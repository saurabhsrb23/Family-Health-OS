import logging
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from cache.redis_client import CacheKeys, cache
from models.care_program import CareProgram
from models.family_member import FamilyMember
from schemas.family_member import MemberCreate, MemberUpdate

logger = logging.getLogger(__name__)

_MEMBER_LIST_TTL = 3600   # 1 hour
_MEMBER_TTL = 3600


def get_members_for_user(user_id: UUID, db: Session) -> List[dict]:
    """
    Return all active members for a user with their active program summary.
    Cache: members:user:{user_id}  TTL=1h
    Invalidated on: create / update / delete member, create program.
    """
    cache_key = CacheKeys.format(CacheKeys.MEMBER_LIST, user_id=str(user_id))
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached

    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == user_id, FamilyMember.deleted_at.is_(None))
        .order_by(FamilyMember.created_at)
        .all()
    )

    result = []
    for m in members:
        member_dict = _member_to_dict(m)
        member_dict["active_program"] = _compute_program_summary(m, db)
        result.append(member_dict)

    cache.set(cache_key, result, ttl=_MEMBER_LIST_TTL)
    logger.debug(f"Cache MISS + SET: {cache_key} ({len(result)} members)")
    return result


def get_member_by_id(member_id: UUID, user_id: UUID, db: Session) -> FamilyMember:
    """
    Fetch a single member and enforce ownership.
    Cache: member:{member_id}  TTL=1h  (stores only the ORM dict; access control checked every time)
    """
    member = (
        db.query(FamilyMember)
        .filter(FamilyMember.id == member_id, FamilyMember.deleted_at.is_(None))
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "MEMBER_NOT_FOUND", "detail": "Member not found", "status_code": 404},
        )

    # Access control — must always be checked, never rely on cache for this
    if member.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "MEMBER_ACCESS_DENIED", "detail": "Access denied", "status_code": 403},
        )

    return member


def create_member(user_id: UUID, data: MemberCreate, db: Session) -> FamilyMember:
    """Create a new family member and invalidate the member list cache."""
    member = FamilyMember(
        user_id=user_id,
        name=data.name,
        date_of_birth=data.date_of_birth,
        relationship=data.relationship,
        gender=data.gender,
        phone=data.phone,
        is_active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    _invalidate_member_list(user_id)
    logger.info(f"Member created: {member.id} for user {user_id}")
    return member


def update_member(member_id: UUID, user_id: UUID, data: MemberUpdate, db: Session) -> FamilyMember:
    """Update allowed fields and invalidate relevant caches."""
    member = get_member_by_id(member_id, user_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)
    member.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(member)

    _invalidate_member(member_id, user_id)
    logger.info(f"Member updated: {member_id}")
    return member


def delete_member(member_id: UUID, user_id: UUID, db: Session) -> bool:
    """
    Soft delete — sets deleted_at and is_active=False.
    PHI data is retained for audit/compliance purposes.
    """
    member = get_member_by_id(member_id, user_id, db)

    member.deleted_at = datetime.utcnow()
    member.is_active = False
    member.updated_at = datetime.utcnow()
    db.commit()

    _invalidate_member(member_id, user_id)
    logger.info(f"Member soft-deleted: {member_id}")
    return True


# ── helpers ───────────────────────────────────────────────────────────────────

def _compute_program_summary(member: FamilyMember, db: Session) -> Optional[dict]:
    """Find active program and compute day_number, days_remaining, phase."""
    active_program = (
        db.query(CareProgram)
        .filter(
            CareProgram.member_id == member.id,
            CareProgram.status == "active",
            CareProgram.deleted_at.is_(None),
        )
        .first()
    )
    if not active_program:
        return None

    today = date.today()
    day_number = max(1, (today - active_program.start_date).days + 1)
    days_remaining = max(0, (active_program.end_date - today).days)

    return {
        "id": str(active_program.id),
        "title": active_program.title,
        "day_number": day_number,
        "days_remaining": days_remaining,
        "phase": active_program.phase,
        "status": active_program.status,
    }


def _member_to_dict(member: FamilyMember) -> dict:
    return {
        "id": str(member.id),
        "name": member.name,
        "date_of_birth": member.date_of_birth.isoformat() if member.date_of_birth else None,
        "relationship": member.relationship,
        "gender": member.gender,
        "phone": member.phone,
        "is_active": member.is_active,
        "created_at": member.created_at.isoformat(),
        "active_program": None,
    }


def _invalidate_member_list(user_id: UUID) -> None:
    cache.delete_pattern(f"members:user:{user_id}*")


def _invalidate_member(member_id: UUID, user_id: UUID) -> None:
    cache.delete(CacheKeys.format(CacheKeys.MEMBER, member_id=str(member_id)))
    _invalidate_member_list(user_id)
