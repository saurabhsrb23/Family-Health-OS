import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.user import User
from models.workout_session import ExerciseLog, WorkoutSession
from schemas.workout_session import WorkoutCreate, WorkoutResponse
from services.adherence_service import invalidate_adherence_cache
from services.member_service import get_member_by_id
from utils.pagination import PaginatedResponse, PaginationParams
from utils.security import get_current_user

router = APIRouter(tags=["Workouts"])
logger = logging.getLogger(__name__)


# ── POST /members/{member_id}/workouts ───────────────────────────────────────

@router.post(
    "/members/{member_id}/workouts",
    response_model=WorkoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_workout(
    member_id: UUID,
    body: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log a workout session with individual exercise sets/reps.
    All exercises are created atomically with the session.
    """
    get_member_by_id(member_id, current_user.id, db)

    session = WorkoutSession(
        program_id=body.program_id,
        member_id=member_id,
        session_type=body.session_type,
        energy_level=body.energy_level,
        duration_minutes=body.duration_minutes,
        notes=body.notes,
        logged_at=body.logged_at,
    )
    db.add(session)
    db.flush()  # get session.id before inserting exercises

    for ex in body.exercises:
        db.add(ExerciseLog(
            session_id=session.id,
            exercise_name=ex.exercise_name,
            sets=ex.sets,
            reps=ex.reps,
            weight_kg=ex.weight_kg,
            duration_seconds=ex.duration_seconds,
        ))

    db.commit()
    db.refresh(session)

    invalidate_adherence_cache(member_id, body.logged_at.date())
    logger.info(f"Workout logged: {session.id} for member {member_id} ({len(body.exercises)} exercises)")
    return session


# ── GET /members/{member_id}/workouts ─────────────────────────────────────────

@router.get("/members/{member_id}/workouts", response_model=PaginatedResponse[WorkoutResponse])
def list_workouts(
    member_id: UUID,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List workout sessions with optional date range filter."""
    get_member_by_id(member_id, current_user.id, db)

    q = (
        db.query(WorkoutSession)
        .options(joinedload(WorkoutSession.exercise_logs))
        .filter(WorkoutSession.member_id == member_id, WorkoutSession.deleted_at.is_(None))
    )
    if start_date:
        q = q.filter(WorkoutSession.logged_at >= start_date)
    if end_date:
        q = q.filter(WorkoutSession.logged_at <= end_date)

    total = q.count()
    sessions = (
        q.order_by(WorkoutSession.logged_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )

    # Build WorkoutResponse — map exercise_logs to exercises field
    data = [_to_response(s) for s in sessions]
    return PaginatedResponse.create(data=data, total=total, page=pagination.page, page_size=pagination.page_size)


# ── GET /members/{member_id}/workouts/{session_id} ────────────────────────────

@router.get("/members/{member_id}/workouts/{session_id}", response_model=WorkoutResponse)
def get_workout(
    member_id: UUID,
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a workout session with all exercises."""
    get_member_by_id(member_id, current_user.id, db)

    session = (
        db.query(WorkoutSession)
        .options(joinedload(WorkoutSession.exercise_logs))
        .filter(
            WorkoutSession.id == session_id,
            WorkoutSession.member_id == member_id,
            WorkoutSession.deleted_at.is_(None),
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "WORKOUT_NOT_FOUND", "detail": "Workout session not found", "status_code": 404},
        )
    return _to_response(session)


# ── helper ────────────────────────────────────────────────────────────────────

def _to_response(session: WorkoutSession) -> WorkoutResponse:
    """Map ORM WorkoutSession (exercise_logs) → WorkoutResponse (exercises)."""
    return WorkoutResponse(
        id=session.id,
        member_id=session.member_id,
        program_id=session.program_id,
        session_type=session.session_type,
        energy_level=session.energy_level,
        duration_minutes=session.duration_minutes,
        notes=session.notes,
        logged_at=session.logged_at,
        exercises=session.exercise_logs or [],
        created_at=session.created_at,
    )
