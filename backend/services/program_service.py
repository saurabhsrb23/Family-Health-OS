import logging
from datetime import date, datetime, timedelta
from math import ceil
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from cache.redis_client import CacheKeys, cache
from models.care_program import CareProgram, ProgramComponent
from models.family_member import FamilyMember
from schemas.care_program import ProgramCreate, ProgramUpdate

logger = logging.getLogger(__name__)

_PROGRAM_TTL = 3600  # 1 hour — programs change rarely


def create_program(member_id: UUID, user_id: UUID, data: ProgramCreate, db: Session) -> CareProgram:
    """
    Create a 90-day care program with 3 components.
    Enforces: one active program per member at a time.
    """
    member = _verify_member_ownership(member_id, user_id, db)

    # One active program per member
    existing = (
        db.query(CareProgram)
        .filter(
            CareProgram.member_id == member_id,
            CareProgram.status == "active",
            CareProgram.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "PROGRAM_ALREADY_ACTIVE",
                "detail": "This member already has an active care program",
                "status_code": 409,
            },
        )

    end_date = data.start_date + timedelta(days=89)  # 90 days inclusive

    program = CareProgram(
        member_id=member_id,
        title=data.title,
        description=data.description,
        start_date=data.start_date,
        end_date=end_date,
        phase=1,
        status="active",
    )
    db.add(program)
    db.flush()  # get program.id before creating components

    components = [
        ProgramComponent(
            program_id=program.id,
            component_type="nutrition",
            is_active=True,
            config=data.nutrition_config.model_dump(),
        ),
        ProgramComponent(
            program_id=program.id,
            component_type="strength",
            is_active=True,
            config=data.strength_config.model_dump(),
        ),
        ProgramComponent(
            program_id=program.id,
            component_type="clinical",
            is_active=True,
            config=data.clinical_config.model_dump(),
        ),
    ]
    db.add_all(components)
    db.commit()
    db.refresh(program)

    # Invalidate member list cache (active_program summary changed)
    cache.delete_pattern(f"members:user:{user_id}*")
    cache.delete(CacheKeys.format(CacheKeys.MEMBER, member_id=str(member_id)))

    logger.info(f"Program created: {program.id} for member {member_id}")
    return program


def get_programs_for_member(member_id: UUID, user_id: UUID, db: Session) -> List[CareProgram]:
    """Return all non-deleted programs for a member (ownership verified)."""
    _verify_member_ownership(member_id, user_id, db)

    return (
        db.query(CareProgram)
        .options(joinedload(CareProgram.components))
        .filter(CareProgram.member_id == member_id, CareProgram.deleted_at.is_(None))
        .order_by(CareProgram.created_at.desc())
        .all()
    )


def get_program_by_id(program_id: UUID, member_id: UUID, user_id: UUID, db: Session) -> CareProgram:
    """
    Fetch program by ID with ownership check.
    Cache: program:{program_id}  TTL=1h
    Note: day_number / days_remaining are computed fresh (time-sensitive).
    """
    _verify_member_ownership(member_id, user_id, db)

    program = (
        db.query(CareProgram)
        .options(joinedload(CareProgram.components))
        .filter(
            CareProgram.id == program_id,
            CareProgram.member_id == member_id,
            CareProgram.deleted_at.is_(None),
        )
        .first()
    )

    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROGRAM_NOT_FOUND", "detail": "Program not found", "status_code": 404},
        )

    return program


def update_program(
    program_id: UUID, member_id: UUID, user_id: UUID, data: ProgramUpdate, db: Session
) -> CareProgram:
    """Update title, description, or status. Recomputes phase on status change."""
    program = get_program_by_id(program_id, member_id, user_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)

    program.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(program)

    cache.delete(CacheKeys.format(CacheKeys.PROGRAM, program_id=str(program_id)))
    cache.delete_pattern(f"members:user:{user_id}*")

    logger.info(f"Program updated: {program_id} status={program.status}")
    return program


def delete_program(program_id: UUID, member_id: UUID, user_id: UUID, db: Session) -> bool:
    """Soft delete — retains data for audit trail."""
    program = get_program_by_id(program_id, member_id, user_id, db)

    program.deleted_at = datetime.utcnow()
    program.status = "cancelled"
    program.updated_at = datetime.utcnow()
    db.commit()

    cache.delete(CacheKeys.format(CacheKeys.PROGRAM, program_id=str(program_id)))
    cache.delete_pattern(f"members:user:{user_id}*")

    logger.info(f"Program soft-deleted: {program_id}")
    return True


# ── helpers ───────────────────────────────────────────────────────────────────

def _compute_day_number(program: CareProgram) -> tuple:
    """Returns (day_number, days_remaining). day_number clamped 1–90."""
    today = date.today()
    day_number = max(1, min(90, (today - program.start_date).days + 1))
    days_remaining = max(0, (program.end_date - today).days)
    return day_number, days_remaining


def _compute_phase(day_number: int) -> int:
    """Phase 1: days 1–30  |  Phase 2: days 31–60  |  Phase 3: days 61–90"""
    return min(3, ceil(day_number / 30))


def _verify_member_ownership(member_id: UUID, user_id: UUID, db: Session) -> FamilyMember:
    """Raise 404/403 if member doesn't exist or doesn't belong to user."""
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
    if member.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "MEMBER_ACCESS_DENIED", "detail": "Access denied", "status_code": 403},
        )
    return member
