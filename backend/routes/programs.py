from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.care_program import ComponentResponse, ProgramCreate, ProgramResponse, ProgramUpdate
from services import program_service
from utils.security import get_current_user

router = APIRouter(prefix="/members/{member_id}/programs", tags=["Care Programs"])


def _to_response(program, db: Session = None) -> ProgramResponse:
    """Build ProgramResponse from ORM object, computing day_number and phase."""
    day_number, days_remaining = program_service._compute_day_number(program)
    phase = program_service._compute_phase(day_number)

    components = [
        ComponentResponse(
            id=c.id,
            component_type=c.component_type,
            is_active=c.is_active,
            config=c.config or {},
        )
        for c in (program.components or [])
    ]

    return ProgramResponse(
        id=program.id,
        member_id=program.member_id,
        title=program.title,
        description=program.description,
        start_date=program.start_date,
        end_date=program.end_date,
        phase=phase,
        status=program.status,
        day_number=day_number,
        days_remaining=days_remaining,
        components=components,
        created_at=program.created_at,
    )


# ── POST /members/{member_id}/programs ───────────────────────────────────────

@router.post("", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
def create_program(
    member_id: UUID,
    body: ProgramCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a 90-day care program for a family member.
    Returns 409 if member already has an active program.
    """
    program = program_service.create_program(member_id, current_user.id, body, db)
    return _to_response(program)


# ── GET /members/{member_id}/programs ─────────────────────────────────────────

@router.get("", response_model=List[ProgramResponse])
def list_programs(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all care programs for a family member (most recent first)."""
    programs = program_service.get_programs_for_member(member_id, current_user.id, db)
    return [_to_response(p) for p in programs]


# ── GET /members/{member_id}/programs/{program_id} ───────────────────────────

@router.get("/{program_id}", response_model=ProgramResponse)
def get_program(
    member_id: UUID,
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific care program with all component configs."""
    program = program_service.get_program_by_id(program_id, member_id, current_user.id, db)
    return _to_response(program)


# ── PUT /members/{member_id}/programs/{program_id} ───────────────────────────

@router.put("/{program_id}", response_model=ProgramResponse)
def update_program(
    member_id: UUID,
    program_id: UUID,
    body: ProgramUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update program title, description, or status.
    Status transitions: active → paused → active → completed / cancelled.
    """
    program = program_service.update_program(program_id, member_id, current_user.id, body, db)
    return _to_response(program)


# ── DELETE /members/{member_id}/programs/{program_id} ────────────────────────

@router.delete("/{program_id}", status_code=status.HTTP_200_OK)
def delete_program(
    member_id: UUID,
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a care program (status set to cancelled, data retained)."""
    program_service.delete_program(program_id, member_id, current_user.id, db)
    return {"message": "Program deleted"}
