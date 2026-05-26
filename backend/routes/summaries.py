import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.program_summary import ProgramSummary
from models.user import User
from services import summary_service
from services.member_service import get_member_by_id
from services.program_service import get_program_by_id
from utils.security import get_current_user

router = APIRouter(tags=["Weekly Summaries"])
logger = logging.getLogger(__name__)


def _summary_to_dict(s: ProgramSummary) -> dict:
    return {
        "id": str(s.id),
        "program_id": str(s.program_id),
        "member_id": str(s.member_id),
        "week_number": s.week_number,
        "week_start_date": str(s.week_start_date) if s.week_start_date else None,
        "week_end_date": str(s.week_end_date) if s.week_end_date else None,
        "generation_status": s.generation_status,
        "summary_text": s.summary_text,
        "program_progress_pct": s.program_progress_pct,
        "nutrition_summary": s.nutrition_summary,
        "strength_summary": s.strength_summary,
        "clinical_summary": s.clinical_summary,
        "risks": s.risks,
        "recommended_actions": s.recommended_actions,
        "generated_at": str(s.generated_at) if s.generated_at else None,
    }


# ── GET /members/{member_id}/programs/{program_id}/summaries ─────────────────

@router.get("/members/{member_id}/programs/{program_id}/summaries")
def list_summaries(
    member_id: UUID,
    program_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all weekly summaries for a program (metadata only — no heavy AI content).
    Returns week number, status, progress %, and generation date for each week.
    """
    get_member_by_id(member_id, current_user.id, db)
    get_program_by_id(program_id, member_id, current_user.id, db)

    summaries = (
        db.query(ProgramSummary)
        .filter(ProgramSummary.program_id == program_id)
        .order_by(ProgramSummary.week_number)
        .all()
    )

    # Return lightweight metadata list
    return [
        {
            "id": str(s.id),
            "week_number": s.week_number,
            "week_start_date": str(s.week_start_date) if s.week_start_date else None,
            "week_end_date": str(s.week_end_date) if s.week_end_date else None,
            "generation_status": s.generation_status,
            "program_progress_pct": s.program_progress_pct,
            "generated_at": str(s.generated_at) if s.generated_at else None,
        }
        for s in summaries
    ]


# ── GET /members/{member_id}/programs/{program_id}/summaries/{week_number} ───

@router.get("/members/{member_id}/programs/{program_id}/summaries/{week_number}")
def get_summary(
    member_id: UUID,
    program_id: UUID,
    week_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the full AI-generated summary for a specific week.
    Returns 404 if the summary has not been generated yet — use the generate endpoint first.
    """
    get_member_by_id(member_id, current_user.id, db)
    get_program_by_id(program_id, member_id, current_user.id, db)

    result = summary_service.get_summary(program_id, week_number, db)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "SUMMARY_NOT_FOUND",
                "detail": f"No summary found for week {week_number}. Use POST /summaries/generate to create one.",
                "status_code": 404,
            },
        )

    # result is either a ProgramSummary ORM object or a cached dict
    if isinstance(result, dict):
        return result
    return _summary_to_dict(result)


# ── POST /members/{member_id}/programs/{program_id}/summaries/generate ────────

@router.post(
    "/members/{member_id}/programs/{program_id}/summaries/generate",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_summary(
    member_id: UUID,
    program_id: UUID,
    background_tasks: BackgroundTasks,
    week_number: int = Body(..., embed=True, ge=1, le=13, description="Week number 1–13"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI weekly summary generation for a specific week.
    Generation runs as a background task — poll GET /summaries/{week_number} for the result.

    Week 1 = days 1–7, Week 2 = days 8–14, ... Week 13 = days 85–91.
    """
    get_member_by_id(member_id, current_user.id, db)
    get_program_by_id(program_id, member_id, current_user.id, db)

    # Get or create the summary record so we can return its ID immediately
    existing = db.query(ProgramSummary).filter(
        ProgramSummary.program_id == program_id,
        ProgramSummary.week_number == week_number,
    ).first()

    summary_id = str(existing.id) if existing else str(UUID(int=0))  # placeholder until created

    background_tasks.add_task(
        summary_service.generate_weekly_summary,
        program_id,
        week_number,
        db,
    )

    logger.info(f"Summary generation queued: program={program_id} week={week_number}")
    return {
        "status": "generating",
        "summary_id": summary_id,
        "week_number": week_number,
        "message": f"Summary generation started for week {week_number}. Poll GET /summaries/{week_number} for results.",
    }
