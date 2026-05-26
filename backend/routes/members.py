from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.family_member import MemberCreate, MemberResponse, MemberUpdate, ActiveProgramSummary
from services import member_service
from utils.pagination import PaginatedResponse, PaginationParams
from utils.security import get_current_user

router = APIRouter(prefix="/members", tags=["Members"])


def _to_response(member_dict: dict) -> MemberResponse:
    """Convert the cached dict or ORM object to MemberResponse."""
    active = member_dict.get("active_program")
    return MemberResponse(
        id=member_dict["id"],
        name=member_dict["name"],
        date_of_birth=member_dict.get("date_of_birth"),
        relationship=member_dict["relationship"],
        gender=member_dict.get("gender"),
        phone=member_dict.get("phone"),
        is_active=member_dict["is_active"],
        active_program=ActiveProgramSummary(**active) if active else None,
        created_at=member_dict["created_at"],
    )


# ── GET /members ──────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[MemberResponse])
def list_members(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all family members for the authenticated user (paginated)."""
    all_members = member_service.get_members_for_user(current_user.id, db)

    # Paginate in-memory (list is typically small — max ~10 members per family)
    total = len(all_members)
    page_slice = all_members[pagination.offset: pagination.offset + pagination.page_size]
    data = [_to_response(m) for m in page_slice]

    return PaginatedResponse.create(
        data=data,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ── POST /members ─────────────────────────────────────────────────────────────

@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    body: MemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new family member to the current user's account."""
    member = member_service.create_member(current_user.id, body, db)
    member_dict = member_service._member_to_dict(member)
    member_dict["active_program"] = member_service._compute_program_summary(member, db)
    return _to_response(member_dict)


# ── GET /members/{member_id} ──────────────────────────────────────────────────

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific family member. Returns 403 if member belongs to another user."""
    member = member_service.get_member_by_id(member_id, current_user.id, db)
    member_dict = member_service._member_to_dict(member)
    member_dict["active_program"] = member_service._compute_program_summary(member, db)
    return _to_response(member_dict)


# ── PUT /members/{member_id} ──────────────────────────────────────────────────

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: UUID,
    body: MemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name, phone, or gender of a family member."""
    member = member_service.update_member(member_id, current_user.id, body, db)
    member_dict = member_service._member_to_dict(member)
    member_dict["active_program"] = member_service._compute_program_summary(member, db)
    return _to_response(member_dict)


# ── DELETE /members/{member_id} ───────────────────────────────────────────────

@router.delete("/{member_id}", status_code=status.HTTP_200_OK)
def delete_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a family member (data retained for compliance)."""
    member_service.delete_member(member_id, current_user.id, db)
    return {"message": "Member deleted successfully"}
