import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.adherence import FullAdherenceReport
from services import adherence_service
from services.member_service import get_member_by_id
from utils.security import get_current_user

router = APIRouter(tags=["Adherence"])
logger = logging.getLogger(__name__)


# ── GET /members/{member_id}/adherence ────────────────────────────────────────

@router.get("/members/{member_id}/adherence", response_model=FullAdherenceReport)
def get_adherence_report(
    member_id: UUID,
    report_date: Optional[date] = Query(default=None, description="Reference date for the report week (defaults to today). Pass any date in a past week to view historical data."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Full adherence dashboard for a family member.

    Returns:
    - Today's (or report_date's) nutrition adherence (protein + calories vs targets)
    - The week's strength adherence (sessions completed vs target)
    - The week's clinical adherence (measurements vs target)
    - 7-day rolling adherence with trend for nutrition + strength
    - Overall weighted score: nutrition 40% + strength 40% + clinical 20%

    Partially cached (TTL=15min per component). Recalculates on cache miss.
    Pass report_date to view a previous week's data.
    """
    get_member_by_id(member_id, current_user.id, db)
    report = adherence_service.get_full_adherence_report(member_id, db, report_date=report_date)
    return FullAdherenceReport(**report)


# ── POST /members/{member_id}/adherence/recompute ────────────────────────────

@router.post("/members/{member_id}/adherence/recompute")
def recompute_adherence(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Force-invalidate all adherence cache for this member and recompute today's nutrition.
    Useful after bulk data corrections or manual data entry.
    """
    get_member_by_id(member_id, current_user.id, db)

    today = date.today()
    adherence_service.invalidate_adherence_cache(member_id, today)

    # Recompute nutrition for today as a fresh baseline
    nutrition = adherence_service.compute_nutrition_adherence(member_id, today, db)

    logger.info(f"Adherence recomputed for member {member_id}: {nutrition['adherence_percentage']}%")
    return {
        "message": "Recomputed",
        "today_nutrition_pct": nutrition["adherence_percentage"],
        "today_protein_actual": nutrition["actual_value"],
        "today_protein_target": nutrition["target_value"],
        "status": nutrition["status"],
    }


# ── GET /members/{member_id}/adherence/nutrition/daily ────────────────────────

@router.get("/members/{member_id}/adherence/nutrition/daily")
def get_daily_nutrition_adherence(
    member_id: UUID,
    target_date: date = Query(default=None, description="Date to query (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Nutrition adherence for a specific date.
    Useful for historical day-by-day breakdown on the mobile calendar view.
    """
    get_member_by_id(member_id, current_user.id, db)

    query_date = target_date or date.today()
    result = adherence_service.compute_nutrition_adherence(member_id, query_date, db)
    return result
