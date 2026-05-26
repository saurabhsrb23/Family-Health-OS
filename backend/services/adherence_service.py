"""
Adherence Engine — computes daily/weekly adherence metrics for all 3 program components.

Design notes:
- Nutrition adherence: computed per-day (protein intake vs target)
- Strength adherence: computed per-week (sessions completed vs target)
- Clinical adherence: computed per-week (measurements done vs target)
- All results are upserted into adherence_metrics and cached (TTL=15min)
- Cache invalidated on every new health data write
"""

import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from cache.redis_client import CacheKeys, cache
from models.adherence_metric import AdherenceMetric
from models.care_program import CareProgram, ProgramComponent
from models.health_measurement import HealthMeasurement
from models.meal_log import MealLog
from models.workout_session import WorkoutSession

logger = logging.getLogger(__name__)

_DAILY_TTL = 900    # 15 min — stale for at most 15 min after new data logged
_ROLLING_TTL = 900


# ── Cache invalidation ────────────────────────────────────────────────────────

def invalidate_adherence_cache(member_id: UUID, target_date: date) -> None:
    """Invalidate all adherence cache keys for a member on a date. Call on every health data write."""
    date_str = str(target_date)
    for component in ("nutrition", "strength", "clinical"):
        cache.delete(CacheKeys.format(CacheKeys.ADHERENCE_DAILY, member_id=str(member_id), component=component, date=date_str))
        cache.delete(CacheKeys.format(CacheKeys.ADHERENCE_ROLLING, member_id=str(member_id), component=component))
    logger.debug(f"Adherence cache invalidated for member {member_id} on {date_str}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_active_program(member_id: UUID, db: Session) -> CareProgram | None:
    return (
        db.query(CareProgram)
        .filter(
            CareProgram.member_id == member_id,
            CareProgram.status == "active",
            CareProgram.deleted_at.is_(None),
        )
        .first()
    )


def _get_component_config(program_id: UUID, component_type: str, db: Session) -> dict:
    comp = (
        db.query(ProgramComponent)
        .filter(
            ProgramComponent.program_id == program_id,
            ProgramComponent.component_type == component_type,
            ProgramComponent.is_active.is_(True),
        )
        .first()
    )
    return comp.config or {} if comp else {}


def _adherence_status(pct: float) -> str:
    if pct >= 90:
        return "met"
    elif pct >= 50:
        return "partial"
    return "missed"


def _upsert_metric(
    db: Session,
    program_id: UUID,
    member_id: UUID,
    component_type: str,
    metric_date: date,
    target_value: float,
    actual_value: float,
    adherence_pct: float,
) -> None:
    """
    Upsert adherence_metrics — ON CONFLICT update.
    Unique constraint: (member_id, component_type, metric_date)
    """
    stmt = pg_insert(AdherenceMetric).values(
        program_id=program_id,
        member_id=member_id,
        component_type=component_type,
        metric_date=metric_date,
        target_value=target_value,
        actual_value=actual_value,
        adherence_percentage=adherence_pct,
        status=_adherence_status(adherence_pct),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_adherence_member_component_date",
        set_={
            "target_value": stmt.excluded.target_value,
            "actual_value": stmt.excluded.actual_value,
            "adherence_percentage": stmt.excluded.adherence_percentage,
            "status": stmt.excluded.status,
        },
    )
    db.execute(stmt)
    db.commit()


# ── Nutrition adherence ───────────────────────────────────────────────────────

def compute_nutrition_adherence(member_id: UUID, target_date: date, db: Session) -> dict:
    """
    Compute protein adherence for a member on a specific date.
    Uses completed meal logs only — pending/failed extractions are excluded.

    Cache key: adherence:{member_id}:nutrition:{date}  TTL=15min
    """
    cache_key = CacheKeys.format(CacheKeys.ADHERENCE_DAILY, member_id=str(member_id), component="nutrition", date=str(target_date))
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached

    program = _get_active_program(member_id, db)
    if not program:
        return _empty_nutrition(target_date)

    config = _get_component_config(program.id, "nutrition", db)
    protein_target = float(config.get("daily_protein_target_g", 60.0))
    calorie_target = float(config.get("daily_calorie_target", 2000.0))

    # Aggregate completed meal logs for the day
    result = (
        db.query(
            func.coalesce(func.sum(MealLog.protein_g), 0.0).label("total_protein"),
            func.coalesce(func.sum(MealLog.calories), 0.0).label("total_calories"),
        )
        .filter(
            MealLog.member_id == member_id,
            MealLog.deleted_at.is_(None),
            MealLog.extraction_status == "completed",
            func.date(MealLog.logged_at) == target_date,
        )
        .first()
    )

    total_protein = float(result.total_protein)
    total_calories = float(result.total_calories)

    adherence_pct = min(100.0, (total_protein / protein_target * 100)) if protein_target > 0 else 0.0

    # Upsert into DB
    _upsert_metric(db, program.id, member_id, "nutrition", target_date, protein_target, total_protein, adherence_pct)

    output = {
        "component_type": "nutrition",
        "date": str(target_date),
        "target_value": protein_target,
        "actual_value": round(total_protein, 1),
        "calorie_target": calorie_target,
        "actual_calories": round(total_calories, 1),
        "adherence_percentage": round(adherence_pct, 1),
        "status": _adherence_status(adherence_pct),
    }
    cache.set(cache_key, output, ttl=_DAILY_TTL)
    return output


def _empty_nutrition(target_date: date) -> dict:
    return {
        "component_type": "nutrition",
        "date": str(target_date),
        "target_value": 0.0,
        "actual_value": 0.0,
        "calorie_target": 0.0,
        "actual_calories": 0.0,
        "adherence_percentage": 0.0,
        "status": "missed",
    }


# ── Strength adherence ────────────────────────────────────────────────────────

def compute_strength_adherence(member_id: UUID, week_start: date, db: Session) -> dict:
    """
    Compute strength adherence for a given week (week_start to week_start+6).
    Counts distinct workout sessions (any session_type counts).

    Cache key: adherence:{member_id}:strength:{week_start}  TTL=15min
    """
    cache_key = CacheKeys.format(CacheKeys.ADHERENCE_DAILY, member_id=str(member_id), component="strength", date=str(week_start))
    cached = cache.get(cache_key)
    if cached:
        return cached

    program = _get_active_program(member_id, db)
    if not program:
        return {"component_type": "strength", "week_start": str(week_start), "target_value": 0, "actual_value": 0, "adherence_percentage": 0.0, "status": "missed"}

    config = _get_component_config(program.id, "strength", db)
    target_sessions = int(config.get("sessions_per_week", 4))

    week_end = week_start + timedelta(days=6)
    sessions_count = (
        db.query(func.count(WorkoutSession.id))
        .filter(
            WorkoutSession.member_id == member_id,
            WorkoutSession.deleted_at.is_(None),
            func.date(WorkoutSession.logged_at) >= week_start,
            func.date(WorkoutSession.logged_at) <= week_end,
        )
        .scalar()
    ) or 0

    adherence_pct = min(100.0, (sessions_count / target_sessions * 100)) if target_sessions > 0 else 0.0

    _upsert_metric(db, program.id, member_id, "strength", week_start, float(target_sessions), float(sessions_count), adherence_pct)

    output = {
        "component_type": "strength",
        "week_start": str(week_start),
        "target_value": target_sessions,
        "actual_value": sessions_count,
        "adherence_percentage": round(adherence_pct, 1),
        "status": _adherence_status(adherence_pct),
    }
    cache.set(cache_key, output, ttl=_DAILY_TTL)
    return output


# ── Clinical adherence ────────────────────────────────────────────────────────

def compute_clinical_adherence(member_id: UUID, week_start: date, db: Session) -> dict:
    """
    Compute clinical adherence for a given week.
    Counts BP + weight measurements vs weekly targets.

    Cache key: adherence:{member_id}:clinical:{week_start}  TTL=15min
    """
    cache_key = CacheKeys.format(CacheKeys.ADHERENCE_DAILY, member_id=str(member_id), component="clinical", date=str(week_start))
    cached = cache.get(cache_key)
    if cached:
        return cached

    program = _get_active_program(member_id, db)
    if not program:
        return {"component_type": "clinical", "week_start": str(week_start), "target_value": 0, "actual_value": 0, "adherence_percentage": 0.0, "status": "missed"}

    config = _get_component_config(program.id, "clinical", db)
    bp_target = int(config.get("bp_checks_per_week", 2))
    weight_target = int(config.get("weight_checks_per_week", 3))
    total_target = bp_target + weight_target

    week_end = week_start + timedelta(days=6)
    measurements_count = (
        db.query(func.count(HealthMeasurement.id))
        .filter(
            HealthMeasurement.member_id == member_id,
            HealthMeasurement.deleted_at.is_(None),
            HealthMeasurement.measurement_type.in_(["blood_pressure", "weight"]),
            func.date(HealthMeasurement.measured_at) >= week_start,
            func.date(HealthMeasurement.measured_at) <= week_end,
        )
        .scalar()
    ) or 0

    adherence_pct = min(100.0, (measurements_count / total_target * 100)) if total_target > 0 else 0.0

    _upsert_metric(db, program.id, member_id, "clinical", week_start, float(total_target), float(measurements_count), adherence_pct)

    output = {
        "component_type": "clinical",
        "week_start": str(week_start),
        "target_value": total_target,
        "actual_value": measurements_count,
        "adherence_percentage": round(adherence_pct, 1),
        "status": _adherence_status(adherence_pct),
    }
    cache.set(cache_key, output, ttl=_DAILY_TTL)
    return output


# ── 7-day rolling adherence ───────────────────────────────────────────────────

def get_rolling_adherence(member_id: UUID, component_type: str, db: Session) -> dict:
    """
    7-day rolling adherence for any component.
    Trend = compare last 3 days vs previous 4 days.

    Cache key: adherence:rolling:{member_id}:{component_type}  TTL=15min
    """
    cache_key = CacheKeys.format(CacheKeys.ADHERENCE_ROLLING, member_id=str(member_id), component=component_type)
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached

    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]  # oldest to newest

    # Query stored adherence_metrics for this member/component over last 7 days
    records = (
        db.query(AdherenceMetric)
        .filter(
            AdherenceMetric.member_id == member_id,
            AdherenceMetric.component_type == component_type,
            AdherenceMetric.metric_date >= days[0],
            AdherenceMetric.metric_date <= today,
        )
        .all()
    )
    record_map = {r.metric_date: r for r in records}

    day_entries = []
    for d in days:
        rec = record_map.get(d)
        day_entries.append({
            "date": str(d),
            "adherence_pct": round(rec.adherence_percentage, 1) if rec else 0.0,
            "status": rec.status if rec else "missed",
            "target_value": rec.target_value if rec else None,
            "actual_value": rec.actual_value if rec else None,
        })

    all_pcts = [e["adherence_pct"] for e in day_entries]
    avg_pct = round(sum(all_pcts) / len(all_pcts), 1) if all_pcts else 0.0

    # Trend: last 3 days vs first 4 days
    recent = sum(all_pcts[-3:]) / 3 if len(all_pcts) >= 3 else avg_pct
    older = sum(all_pcts[:4]) / 4 if len(all_pcts) >= 4 else avg_pct
    if recent - older >= 5:
        trend = "improving"
    elif older - recent >= 5:
        trend = "declining"
    else:
        trend = "stable"

    result = {
        "average_pct": avg_pct,
        "trend": trend,
        "days": day_entries,
    }
    cache.set(cache_key, result, ttl=_ROLLING_TTL)
    return result


# ── Full adherence report ─────────────────────────────────────────────────────

def _latest_clinical_readings(member_id: UUID, db: Session) -> dict:
    """Return latest BP string and latest weight_kg for the dashboard snapshot."""
    latest_bp = (
        db.query(HealthMeasurement)
        .filter(
            HealthMeasurement.member_id == member_id,
            HealthMeasurement.measurement_type == "blood_pressure",
            HealthMeasurement.deleted_at.is_(None),
        )
        .order_by(HealthMeasurement.measured_at.desc())
        .first()
    )
    latest_weight = (
        db.query(HealthMeasurement)
        .filter(
            HealthMeasurement.member_id == member_id,
            HealthMeasurement.measurement_type == "weight",
            HealthMeasurement.deleted_at.is_(None),
        )
        .order_by(HealthMeasurement.measured_at.desc())
        .first()
    )
    bp_str = (
        f"{latest_bp.systolic_bp}/{latest_bp.diastolic_bp} mmHg"
        if latest_bp and latest_bp.systolic_bp and latest_bp.diastolic_bp
        else None
    )
    return {
        "latest_bp": bp_str,
        "latest_weight_kg": latest_weight.weight_kg if latest_weight else None,
    }


def get_full_adherence_report(member_id: UUID, db: Session, report_date: date | None = None) -> dict:
    """
    Full adherence dashboard report.
    Computes today's nutrition + current week's strength/clinical + 7-day rolling for all.
    Weighted overall: nutrition 40%, strength 40%, clinical 20%.

    Pass report_date to view a historical week (e.g. last week's data).
    """
    today = report_date or date.today()
    # Week starts on Monday
    week_start = today - timedelta(days=today.weekday())

    nutrition_today = compute_nutrition_adherence(member_id, today, db)
    nutrition_rolling = get_rolling_adherence(member_id, "nutrition", db)

    strength_week = compute_strength_adherence(member_id, week_start, db)
    strength_rolling = get_rolling_adherence(member_id, "strength", db)

    clinical_week = compute_clinical_adherence(member_id, week_start, db)

    program = _get_active_program(member_id, db)
    nutrition_config = _get_component_config(program.id, "nutrition", db) if program else {}

    nutrition_pct = nutrition_today["adherence_percentage"]
    strength_pct = strength_week["adherence_percentage"]
    clinical_pct = clinical_week["adherence_percentage"]
    overall_pct = round(nutrition_pct * 0.4 + strength_pct * 0.4 + clinical_pct * 0.2, 1)

    week_end = week_start + timedelta(days=6)
    return {
        "member_id": str(member_id),
        "report_date": str(today),
        "week_start": str(week_start),
        "week_end": str(week_end),
        "nutrition": {
            "today_calories_target": nutrition_config.get("daily_calorie_target"),
            "today_calories_actual": nutrition_today.get("actual_calories"),
            "today_protein_target": nutrition_today.get("target_value"),
            "today_protein_actual": nutrition_today.get("actual_value"),
            "today_adherence_pct": nutrition_pct,
            "today_status": nutrition_today["status"],
            "rolling_7day": nutrition_rolling,
        },
        "strength": {
            "sessions_this_week": strength_week["actual_value"],
            "target_sessions": strength_week["target_value"],
            "week_adherence_pct": strength_pct,
            "rolling_7day": strength_rolling,
        },
        "clinical": {
            "measurements_this_week": clinical_week["actual_value"],
            "target_measurements": clinical_week["target_value"],
            "week_adherence_pct": clinical_pct,
            **_latest_clinical_readings(member_id, db),
        },
        "overall_pct": overall_pct,
    }
