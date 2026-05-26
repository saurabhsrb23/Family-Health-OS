import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.health_measurement import HealthMeasurement
from models.user import User
from schemas.health_measurement import MeasurementCreate, MeasurementResponse
from services.adherence_service import invalidate_adherence_cache
from services.member_service import get_member_by_id
from utils.pagination import PaginatedResponse, PaginationParams
from utils.security import get_current_user

router = APIRouter(tags=["Health Measurements"])
logger = logging.getLogger(__name__)


# ── POST /members/{member_id}/measurements ────────────────────────────────────

@router.post(
    "/members/{member_id}/measurements",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def log_measurement(
    member_id: UUID,
    body: MeasurementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log a health measurement (blood pressure, weight, or glucose).
    Field validation is handled by the MeasurementCreate model_validator.
    """
    get_member_by_id(member_id, current_user.id, db)

    measurement = HealthMeasurement(
        program_id=body.program_id,
        member_id=member_id,
        measurement_type=body.measurement_type,
        systolic_bp=body.systolic_bp,
        diastolic_bp=body.diastolic_bp,
        weight_kg=body.weight_kg,
        glucose_mgdl=body.glucose_mgdl,
        notes=body.notes,
        measured_at=body.measured_at,
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    invalidate_adherence_cache(member_id, body.measured_at.date())
    logger.info(f"Measurement logged: {measurement.id} ({body.measurement_type}) for member {member_id}")
    return measurement


# ── GET /members/{member_id}/measurements ─────────────────────────────────────

@router.get(
    "/members/{member_id}/measurements",
    response_model=PaginatedResponse[MeasurementResponse],
)
def list_measurements(
    member_id: UUID,
    measurement_type: Optional[str] = Query(None, description="blood_pressure | weight | glucose"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List health measurements with optional type and date filters."""
    get_member_by_id(member_id, current_user.id, db)

    q = db.query(HealthMeasurement).filter(
        HealthMeasurement.member_id == member_id,
        HealthMeasurement.deleted_at.is_(None),
    )
    if measurement_type:
        q = q.filter(HealthMeasurement.measurement_type == measurement_type)
    if start_date:
        q = q.filter(HealthMeasurement.measured_at >= start_date)
    if end_date:
        q = q.filter(HealthMeasurement.measured_at <= end_date)

    total = q.count()
    measurements = (
        q.order_by(HealthMeasurement.measured_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )

    return PaginatedResponse.create(
        data=measurements,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ── GET /members/{member_id}/measurements/latest ──────────────────────────────

@router.get(
    "/members/{member_id}/measurements/latest",
    response_model=dict,
)
def get_latest_measurements(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the latest reading of each measurement type.
    Used by mobile dashboard for quick health snapshot.
    """
    get_member_by_id(member_id, current_user.id, db)

    result = {}
    for m_type in ("blood_pressure", "weight", "glucose"):
        latest = (
            db.query(HealthMeasurement)
            .filter(
                HealthMeasurement.member_id == member_id,
                HealthMeasurement.measurement_type == m_type,
                HealthMeasurement.deleted_at.is_(None),
            )
            .order_by(HealthMeasurement.measured_at.desc())
            .first()
        )
        result[m_type] = MeasurementResponse.model_validate(latest) if latest else None

    return result


# ── GET /members/{member_id}/measurements/{measurement_id} ────────────────────

@router.get(
    "/members/{member_id}/measurements/{measurement_id}",
    response_model=MeasurementResponse,
)
def get_measurement(
    member_id: UUID,
    measurement_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific health measurement."""
    get_member_by_id(member_id, current_user.id, db)

    measurement = db.query(HealthMeasurement).filter(
        HealthMeasurement.id == measurement_id,
        HealthMeasurement.member_id == member_id,
        HealthMeasurement.deleted_at.is_(None),
    ).first()

    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "MEASUREMENT_NOT_FOUND", "detail": "Measurement not found", "status_code": 404},
        )
    return measurement
