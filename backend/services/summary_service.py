"""
Weekly summary service — aggregates a week of health data and generates an AI summary.

Production path: replace mock_ai_summary() with a real Gemini API call.
The mock returns the same schema so the rest of the system is production-ready.
"""

import logging
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from cache.redis_client import CacheKeys, cache
from models.adherence_metric import AdherenceMetric
from models.care_program import CareProgram
from models.health_measurement import HealthMeasurement
from models.meal_log import MealLog
from models.program_summary import ProgramSummary
from models.workout_session import WorkoutSession

logger = logging.getLogger(__name__)

_SUMMARY_TTL = 604800  # 7 days — summaries don't change after generation

# Required top-level keys in AI output — validated before saving
_REQUIRED_SUMMARY_KEYS = {
    "summary", "programProgress", "nutritionSummary",
    "strengthSummary", "clinicalSummary", "risks", "recommendedActions",
}


# ── Mock AI summary ───────────────────────────────────────────────────────────

def mock_ai_summary(program_data: dict) -> dict:
    """
    Mock Gemini summary generator.

    Production implementation:
      1. Build structured prompt with week data + JSON schema
      2. POST to Gemini 1.5 Pro:
           https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent
         prompt: f"You are a health coach AI. Analyse this week's data and return ONLY valid JSON
                  matching this schema exactly: {_REQUIRED_SUMMARY_KEYS}.
                  Data: {json.dumps(program_data)}"
      3. Extract JSON from response text (strip markdown fences if present)
      4. Validate all required keys present — raise if not
      5. Return validated dict
    """
    nutrition = program_data.get("nutrition", {})
    strength = program_data.get("strength", {})
    clinical = program_data.get("clinical", {})

    avg_protein = nutrition.get("avg_protein_g", 0)
    protein_target = nutrition.get("protein_target", 60)
    avg_calories = nutrition.get("avg_calories", 0)
    calorie_target = nutrition.get("calorie_target", 2000)
    nutrition_pct = min(100.0, (avg_protein / protein_target * 100)) if protein_target > 0 else 0.0

    sessions = strength.get("sessions_completed", 0)
    target_sessions = strength.get("target_sessions", 4)
    strength_pct = min(100.0, (sessions / target_sessions * 100)) if target_sessions > 0 else 0.0

    clinical_count = clinical.get("measurements_done", 0)
    clinical_target = clinical.get("target_measurements", 5)
    clinical_pct = min(100.0, (clinical_count / clinical_target * 100)) if clinical_target > 0 else 0.0

    overall_pct = round(nutrition_pct * 0.4 + strength_pct * 0.4 + clinical_pct * 0.2, 1)
    performance = "strong" if overall_pct >= 75 else "moderate" if overall_pct >= 50 else "low"

    # Risks
    risks = []
    if nutrition_pct < 70:
        risks.append(f"Protein intake avg {round(avg_protein, 1)}g is below target of {protein_target}g")
    if strength_pct < 75:
        risks.append(f"Only {sessions} of {target_sessions} strength sessions completed this week")
    if clinical_pct < 50:
        risks.append(f"Only {clinical_count} of {clinical_target} clinical measurements recorded")
    if not risks:
        risks.append("No significant risks identified this week — great consistency!")

    # Actions
    actions = []
    if nutrition_pct < 90:
        deficit = round(protein_target - avg_protein, 1)
        actions.append(f"Add ~{deficit}g protein daily — try Greek yogurt, eggs, or chicken")
    if strength_pct < 100:
        missed = target_sessions - sessions
        actions.append(f"Schedule {missed} makeup strength session(s) in the coming week")
    if clinical_pct < 80:
        actions.append("Set daily reminders for BP and weight checks at the same time each day")
    if not actions:
        actions.append("Maintain current routine — excellent consistency!")

    return {
        "summary": (
            f"Week {program_data.get('week_number', 1)} showed {performance} progress overall ({overall_pct}%). "
            f"Nutrition adherence at {round(nutrition_pct)}% and strength training at {round(strength_pct)}%."
        ),
        "programProgress": round(program_data.get("program_progress_pct", 0), 1),
        "nutritionSummary": {
            "avgDailyCalories": round(avg_calories),
            "avgDailyProtein": round(avg_protein, 1),
            "targetCalories": calorie_target,
            "targetProtein": protein_target,
            "adherencePct": round(nutrition_pct, 1),
            "highlight": f"Protein was {'on track' if nutrition_pct >= 90 else 'below target'} this week",
        },
        "strengthSummary": {
            "sessionsCompleted": sessions,
            "targetSessions": target_sessions,
            "adherencePct": round(strength_pct, 1),
            "highlight": f"Completed {sessions}/{target_sessions} planned sessions",
        },
        "clinicalSummary": {
            "measurementsDone": clinical_count,
            "targetMeasurements": clinical_target,
            "avgSystolic": clinical.get("avg_systolic", 0),
            "avgDiastolic": clinical.get("avg_diastolic", 0),
            "weightChange": clinical.get("weight_change_kg", 0),
            "highlight": "BP within normal range" if clinical.get("avg_systolic", 0) < 130 else "Monitor blood pressure closely",
        },
        "risks": risks,
        "recommendedActions": actions,
    }


def _validate_summary_schema(summary: dict) -> None:
    """Raise ValueError if any required key is missing from AI output."""
    missing = _REQUIRED_SUMMARY_KEYS - set(summary.keys())
    if missing:
        raise ValueError(f"AI summary missing required keys: {missing}")


# ── Data aggregation for the week ─────────────────────────────────────────────

def _gather_week_data(program: CareProgram, week_start: date, week_end: date, week_number: int, db: Session) -> dict:
    member_id = program.member_id

    # Nutrition — avg calories + protein for the week (completed meals only)
    nutrition_row = (
        db.query(
            func.coalesce(func.avg(MealLog.calories), 0).label("avg_calories"),
            func.coalesce(func.avg(MealLog.protein_g), 0).label("avg_protein"),
        )
        .filter(
            MealLog.member_id == member_id,
            MealLog.deleted_at.is_(None),
            MealLog.extraction_status == "completed",
            func.date(MealLog.logged_at) >= week_start,
            func.date(MealLog.logged_at) <= week_end,
        )
        .first()
    )

    # Strength — session count
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

    # Clinical — measurements + avg BP
    clinical_rows = (
        db.query(HealthMeasurement)
        .filter(
            HealthMeasurement.member_id == member_id,
            HealthMeasurement.deleted_at.is_(None),
            func.date(HealthMeasurement.measured_at) >= week_start,
            func.date(HealthMeasurement.measured_at) <= week_end,
        )
        .all()
    )
    bp_rows = [r for r in clinical_rows if r.measurement_type == "blood_pressure" and r.systolic_bp]
    weight_rows = [r for r in clinical_rows if r.measurement_type == "weight" and r.weight_kg]

    avg_systolic = round(sum(r.systolic_bp for r in bp_rows) / len(bp_rows)) if bp_rows else 0
    avg_diastolic = round(sum(r.diastolic_bp for r in bp_rows) / len(bp_rows)) if bp_rows else 0
    weight_change = round(weight_rows[-1].weight_kg - weight_rows[0].weight_kg, 2) if len(weight_rows) >= 2 else 0.0

    # Program config
    from models.care_program import ProgramComponent
    nutrition_comp = db.query(ProgramComponent).filter(
        ProgramComponent.program_id == program.id,
        ProgramComponent.component_type == "nutrition",
    ).first()
    strength_comp = db.query(ProgramComponent).filter(
        ProgramComponent.program_id == program.id,
        ProgramComponent.component_type == "strength",
    ).first()
    clinical_comp = db.query(ProgramComponent).filter(
        ProgramComponent.program_id == program.id,
        ProgramComponent.component_type == "clinical",
    ).first()

    n_config = nutrition_comp.config or {} if nutrition_comp else {}
    s_config = strength_comp.config or {} if strength_comp else {}
    c_config = clinical_comp.config or {} if clinical_comp else {}

    bp_target = int(c_config.get("bp_checks_per_week", 2))
    weight_target = int(c_config.get("weight_checks_per_week", 3))

    # Program progress %
    total_days = (program.end_date - program.start_date).days + 1
    elapsed = (date.today() - program.start_date).days + 1
    progress_pct = min(100.0, round((elapsed / total_days) * 100, 1))

    return {
        "week_number": week_number,
        "program_progress_pct": progress_pct,
        "nutrition": {
            "avg_calories": float(nutrition_row.avg_calories),
            "avg_protein_g": float(nutrition_row.avg_protein),
            "calorie_target": n_config.get("daily_calorie_target", 2000),
            "protein_target": n_config.get("daily_protein_target_g", 60),
        },
        "strength": {
            "sessions_completed": sessions_count,
            "target_sessions": s_config.get("sessions_per_week", 4),
        },
        "clinical": {
            "measurements_done": len(clinical_rows),
            "target_measurements": bp_target + weight_target,
            "avg_systolic": avg_systolic,
            "avg_diastolic": avg_diastolic,
            "weight_change_kg": weight_change,
        },
    }


# ── Main generation function ──────────────────────────────────────────────────

async def generate_weekly_summary(program_id: UUID, week_number: int, db: Session) -> ProgramSummary:
    """
    Generate (or regenerate) a weekly summary for a program.

    Steps:
      1. Load program
      2. Compute week date range
      3. Get or create ProgramSummary record
      4. Gather aggregated week data
      5. Generate AI summary (mock)
      6. Validate schema
      7. Persist + cache
    """
    program = db.query(CareProgram).filter(
        CareProgram.id == program_id,
        CareProgram.deleted_at.is_(None),
    ).first()
    if not program:
        raise ValueError(f"Program {program_id} not found")

    week_start = program.start_date + timedelta(weeks=week_number - 1)
    week_end = week_start + timedelta(days=6)

    # Get or create summary record
    summary = db.query(ProgramSummary).filter(
        ProgramSummary.program_id == program_id,
        ProgramSummary.week_number == week_number,
    ).first()

    if not summary:
        summary = ProgramSummary(
            program_id=program_id,
            member_id=program.member_id,
            week_number=week_number,
            week_start_date=week_start,
            week_end_date=week_end,
            generation_status="pending",
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)

    # Mark as generating
    summary.generation_status = "pending"
    db.commit()

    try:
        week_data = _gather_week_data(program, week_start, week_end, week_number, db)
        ai_output = mock_ai_summary(week_data)
        _validate_summary_schema(ai_output)

        summary.summary_text = ai_output["summary"]
        summary.program_progress_pct = ai_output["programProgress"]
        summary.nutrition_summary = ai_output["nutritionSummary"]
        summary.strength_summary = ai_output["strengthSummary"]
        summary.clinical_summary = ai_output["clinicalSummary"]
        summary.risks = ai_output["risks"]
        summary.recommended_actions = ai_output["recommendedActions"]
        summary.generation_status = "completed"
        summary.generated_at = datetime.utcnow()

        db.commit()
        db.refresh(summary)

        # Cache for 7 days (summaries don't change)
        cache_key = CacheKeys.format(CacheKeys.SUMMARY, program_id=str(program_id), week_number=week_number)
        cache.set(cache_key, {
            "id": str(summary.id),
            "week_number": summary.week_number,
            "week_start_date": str(summary.week_start_date),
            "week_end_date": str(summary.week_end_date),
            "summary_text": summary.summary_text,
            "program_progress_pct": summary.program_progress_pct,
            "nutrition_summary": summary.nutrition_summary,
            "strength_summary": summary.strength_summary,
            "clinical_summary": summary.clinical_summary,
            "risks": summary.risks,
            "recommended_actions": summary.recommended_actions,
            "generation_status": summary.generation_status,
            "generated_at": str(summary.generated_at),
        }, ttl=_SUMMARY_TTL)

        logger.info(f"Summary generated: program={program_id} week={week_number} progress={summary.program_progress_pct}%")

    except Exception as e:
        logger.error(f"Summary generation failed: program={program_id} week={week_number} error={e}")
        summary.generation_status = "failed"
        db.commit()

    return summary


# ── Read summary ──────────────────────────────────────────────────────────────

def get_summary(program_id: UUID, week_number: int, db: Session) -> ProgramSummary | None:
    """Get summary from cache first, then DB."""
    cache_key = CacheKeys.format(CacheKeys.SUMMARY, program_id=str(program_id), week_number=week_number)
    cached = cache.get(cache_key)
    if cached:
        logger.debug(f"Cache HIT: {cache_key}")
        return cached  # returns dict when from cache; routes handle both

    summary = db.query(ProgramSummary).filter(
        ProgramSummary.program_id == program_id,
        ProgramSummary.week_number == week_number,
    ).first()

    if summary and summary.generation_status == "completed":
        cache.set(cache_key, {
            "id": str(summary.id),
            "week_number": summary.week_number,
            "week_start_date": str(summary.week_start_date) if summary.week_start_date else None,
            "week_end_date": str(summary.week_end_date) if summary.week_end_date else None,
            "summary_text": summary.summary_text,
            "program_progress_pct": summary.program_progress_pct,
            "nutrition_summary": summary.nutrition_summary,
            "strength_summary": summary.strength_summary,
            "clinical_summary": summary.clinical_summary,
            "risks": summary.risks,
            "recommended_actions": summary.recommended_actions,
            "generation_status": summary.generation_status,
            "generated_at": str(summary.generated_at),
        }, ttl=_SUMMARY_TTL)

    return summary
