import logging
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.meal_log import MealLog
from models.user import User
from schemas.meal_log import ExtractionStatusResponse, MealLogResponse
from services import ai_service
from services.adherence_service import invalidate_adherence_cache
from services.member_service import get_member_by_id
from utils.pagination import PaginatedResponse, PaginationParams
from utils.security import get_current_user

router = APIRouter(tags=["Meal Logs"])
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/jpg", "image/png",
    "image/heic", "image/heif",   # iPhone default format
    "image/webp",                  # Android default
    "image/gif",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif"}


# ── POST /members/{member_id}/meals ──────────────────────────────────────────

@router.post(
    "/members/{member_id}/meals",
    response_model=MealLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meal(
    member_id: UUID,
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(..., description="Meal photo (jpg/jpeg/png)"),
    meal_type: str = Form(..., description="breakfast | lunch | dinner | snack"),
    logged_at: str = Form(..., description="ISO datetime e.g. 2026-05-26T08:00:00"),
    program_id: str | None = Form(None, description="UUID of the care program"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a meal photo for AI nutrition extraction.
    Photo is saved locally; in production this goes to Cloud Storage.
    AI extraction runs as a background task — poll /meals/{id}/status for results.
    """
    # Verify member ownership
    member = get_member_by_id(member_id, current_user.id, db)

    # Validate file type
    suffix = Path(photo.filename or "").suffix.lower()
    if photo.content_type not in ALLOWED_IMAGE_TYPES and suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MEAL_INVALID_FILE_TYPE", "detail": "Only jpg/jpeg/png images are allowed", "status_code": 400},
        )

    # Validate file size
    photo.file.seek(0, 2)  # seek to end
    file_size = photo.file.tell()
    photo.file.seek(0)     # reset
    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "MEAL_FILE_TOO_LARGE", "detail": f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit", "status_code": 413},
        )

    # Validate meal_type
    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MEAL_INVALID_TYPE", "detail": "meal_type must be: breakfast, lunch, dinner, snack", "status_code": 400},
        )

    # Parse logged_at
    try:
        logged_at_dt = datetime.fromisoformat(logged_at)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MEAL_INVALID_DATE", "detail": "logged_at must be ISO datetime format", "status_code": 400},
        )

    # Save photo to local storage
    # Production: upload to GCS bucket, store object key instead of local path
    upload_dir = settings.upload_dir_path / str(member_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid4()}{suffix or '.jpg'}"
    file_path = upload_dir / file_name
    with file_path.open("wb") as f:
        shutil.copyfileobj(photo.file, f)

    photo_key = f"{member_id}/{file_name}"
    photo_url = f"/uploads/{photo_key}"  # local dev URL; production: GCS signed URL

    # Create meal log record
    meal_log = MealLog(
        program_id=UUID(program_id) if program_id else None,
        member_id=member_id,
        photo_url=photo_url,
        photo_key=photo_key,
        meal_type=meal_type,
        extraction_status="pending",
        logged_at=logged_at_dt,
    )
    db.add(meal_log)
    db.commit()
    db.refresh(meal_log)

    # Background AI extraction
    background_tasks.add_task(
        ai_service.extract_nutrition_from_image,
        meal_log.id,
        meal_type,
        db,
    )

    # Invalidate adherence cache for this member's date
    invalidate_adherence_cache(member_id, logged_at_dt.date())

    logger.info(f"Meal log created: {meal_log.id} for member {member_id}, AI extraction queued")
    return meal_log


# ── GET /members/{member_id}/meals ────────────────────────────────────────────

@router.get("/members/{member_id}/meals", response_model=PaginatedResponse[MealLogResponse])
def list_meals(
    member_id: UUID,
    start_date: datetime = Query(None, description="Filter from this datetime (inclusive)"),
    end_date: datetime = Query(None, description="Filter to this datetime (inclusive)"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List meal logs for a member with optional date range filter."""
    get_member_by_id(member_id, current_user.id, db)

    q = db.query(MealLog).filter(
        MealLog.member_id == member_id,
        MealLog.deleted_at.is_(None),
    )
    if start_date:
        q = q.filter(MealLog.logged_at >= start_date)
    if end_date:
        q = q.filter(MealLog.logged_at <= end_date)

    total = q.count()
    meals = q.order_by(MealLog.logged_at.desc()).offset(pagination.offset).limit(pagination.page_size).all()

    return PaginatedResponse.create(
        data=meals,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ── GET /members/{member_id}/meals/{meal_id} ──────────────────────────────────

@router.get("/members/{member_id}/meals/{meal_id}", response_model=MealLogResponse)
def get_meal(
    member_id: UUID,
    meal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific meal log entry."""
    get_member_by_id(member_id, current_user.id, db)

    meal = db.query(MealLog).filter(
        MealLog.id == meal_id,
        MealLog.member_id == member_id,
        MealLog.deleted_at.is_(None),
    ).first()

    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "MEAL_NOT_FOUND", "detail": "Meal log not found", "status_code": 404},
        )
    return meal


# ── GET /members/{member_id}/meals/{meal_id}/status ───────────────────────────

@router.get(
    "/members/{member_id}/meals/{meal_id}/status",
    response_model=ExtractionStatusResponse,
)
def get_meal_extraction_status(
    member_id: UUID,
    meal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lightweight polling endpoint for AI extraction status.
    Mobile app polls this every 2 seconds after photo upload.
    Returns immediately — no heavy DB joins.
    """
    get_member_by_id(member_id, current_user.id, db)

    meal = db.query(MealLog).filter(
        MealLog.id == meal_id,
        MealLog.member_id == member_id,
    ).first()

    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "MEAL_NOT_FOUND", "detail": "Meal log not found", "status_code": 404},
        )

    return ExtractionStatusResponse(
        meal_id=meal.id,
        extraction_status=meal.extraction_status,
        calories=meal.calories,
        protein_g=meal.protein_g,
        food_description=meal.food_description,
    )
