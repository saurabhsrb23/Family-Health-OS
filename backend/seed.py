"""
Seed script — populates demo data on first run.
Idempotent: safe to run multiple times (skips if data already exists).

Demo credentials:
  Email:    demo@familyhealthos.com
  Password: Demo@1234
"""

import uuid
import logging
from datetime import date, datetime, timedelta

from passlib.context import CryptContext

from database import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed():
    init_db()
    db = SessionLocal()
    try:
        _seed_data(db)
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _seed_data(db):
    from models.user import User
    from models.family_member import FamilyMember
    from models.care_program import CareProgram, ProgramComponent
    from models.meal_log import MealLog
    from models.workout_session import WorkoutSession, ExerciseLog
    from models.health_measurement import HealthMeasurement
    from models.adherence_metric import AdherenceMetric

    # ── Guard: skip if already seeded ────────────────────────────────────────
    existing = db.query(User).filter(User.email == "demo@familyhealthos.com").first()
    if existing:
        logger.info("Demo data already exists. Skipping seed.")
        return

    logger.info("Seeding demo data for Family Health OS...")

    # ── 1. Demo User ──────────────────────────────────────────────────────────
    user = User(
        id=uuid.uuid4(),
        email="demo@familyhealthos.com",
        hashed_password=pwd_context.hash("Demo@1234"),
        full_name="Demo User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    # ── 2. Two Family Members ─────────────────────────────────────────────────
    parent1 = FamilyMember(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Alex Johnson",
        date_of_birth=date(1985, 3, 15),
        relationship="self",
        gender="male",
        phone="+1-555-0101",
    )
    parent2 = FamilyMember(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Sarah Johnson",
        date_of_birth=date(1987, 7, 22),
        relationship="spouse",
        gender="female",
        phone="+1-555-0102",
    )
    db.add_all([parent1, parent2])
    db.flush()

    # ── 3. Care Program for Parent 1 ─────────────────────────────────────────
    program_start = date.today() - timedelta(days=10)
    program_end = program_start + timedelta(days=90)

    program = CareProgram(
        id=uuid.uuid4(),
        member_id=parent1.id,
        title="90-Day Wellness Reset",
        description="A comprehensive 90-day program focusing on nutrition, strength, and clinical health.",
        start_date=program_start,
        end_date=program_end,
        phase=1,
        status="active",
    )
    db.add(program)
    db.flush()

    # ── 4. Program Components ─────────────────────────────────────────────────
    nutrition_component = ProgramComponent(
        id=uuid.uuid4(),
        program_id=program.id,
        component_type="nutrition",
        is_active=True,
        config={
            "daily_calorie_target": 2000,
            "daily_protein_target_g": 60,
            "meals_per_day": 3,
        },
    )
    strength_component = ProgramComponent(
        id=uuid.uuid4(),
        program_id=program.id,
        component_type="strength",
        is_active=True,
        config={
            "sessions_per_week": 4,
            "session_duration_minutes": 60,
        },
    )
    clinical_component = ProgramComponent(
        id=uuid.uuid4(),
        program_id=program.id,
        component_type="clinical",
        is_active=True,
        config={
            "bp_checks_per_week": 2,
            "weight_checks_per_week": 3,
            "checkin_frequency_days": 14,
        },
    )
    db.add_all([nutrition_component, strength_component, clinical_component])
    db.flush()

    # ── 5. Sample Meal Logs (last 7 days) ─────────────────────────────────────
    meal_data = [
        ("breakfast", 450, 28, 55, 12, "Oatmeal with banana and protein shake"),
        ("lunch",     620, 42, 70, 15, "Grilled chicken salad with quinoa"),
        ("dinner",    580, 38, 60, 18, "Salmon with steamed broccoli and rice"),
        ("snack",     180, 10, 20,  6, "Greek yogurt with almonds"),
    ]
    for day_offset in range(7):
        log_date = datetime.utcnow() - timedelta(days=day_offset)
        for meal_type, cal, prot, carbs, fat, desc in meal_data[:3]:
            db.add(MealLog(
                id=uuid.uuid4(),
                program_id=program.id,
                member_id=parent1.id,
                meal_type=meal_type,
                calories=cal,
                protein_g=prot,
                carbs_g=carbs,
                fat_g=fat,
                food_description=desc,
                extraction_status="completed",
                logged_at=log_date.replace(
                    hour={"breakfast": 8, "lunch": 13, "dinner": 19}[meal_type]
                ),
            ))

    # ── 6. Sample Workout Sessions (last 7 days) ──────────────────────────────
    for day_offset in [1, 3, 5]:
        session = WorkoutSession(
            id=uuid.uuid4(),
            program_id=program.id,
            member_id=parent1.id,
            session_type="strength",
            energy_level=4,
            duration_minutes=55,
            notes="Felt strong today",
            logged_at=datetime.utcnow() - timedelta(days=day_offset),
        )
        db.add(session)
        db.flush()

        for exercise_name, sets, reps, weight in [
            ("Bench Press", 4, 10, 80.0),
            ("Squat",       4, 8,  100.0),
            ("Deadlift",    3, 6,  120.0),
        ]:
            db.add(ExerciseLog(
                id=uuid.uuid4(),
                session_id=session.id,
                exercise_name=exercise_name,
                sets=sets,
                reps=reps,
                weight_kg=weight,
            ))

    # ── 7. Sample Health Measurements ─────────────────────────────────────────
    for day_offset in range(7):
        measured = datetime.utcnow() - timedelta(days=day_offset)
        db.add(HealthMeasurement(
            id=uuid.uuid4(),
            program_id=program.id,
            member_id=parent1.id,
            measurement_type="blood_pressure",
            systolic_bp=118 + day_offset,
            diastolic_bp=76 + day_offset,
            measured_at=measured,
        ))
        db.add(HealthMeasurement(
            id=uuid.uuid4(),
            program_id=program.id,
            member_id=parent1.id,
            measurement_type="weight",
            weight_kg=82.5 - (day_offset * 0.1),
            measured_at=measured,
        ))

    # ── 8. Sample Adherence Metrics (last 7 days) ─────────────────────────────
    for day_offset in range(7):
        metric_date = date.today() - timedelta(days=day_offset)
        actual_protein = 55 + (day_offset % 3) * 5  # varies between 55-65g
        pct = round((actual_protein / 60) * 100, 1)
        db.add(AdherenceMetric(
            id=uuid.uuid4(),
            program_id=program.id,
            member_id=parent1.id,
            component_type="nutrition",
            metric_date=metric_date,
            target_value=60.0,
            actual_value=float(actual_protein),
            adherence_percentage=min(pct, 100.0),
            status="met" if pct >= 90 else "partial" if pct >= 70 else "missed",
        ))

    db.commit()
    logger.info("✓ Demo user created: demo@familyhealthos.com / Demo@1234")
    logger.info(f"✓ 2 family members: {parent1.name}, {parent2.name}")
    logger.info(f"✓ 1 care program: {program.title}")
    logger.info("✓ Sample meal logs, workouts, measurements, adherence metrics seeded")


if __name__ == "__main__":
    logger.info("Starting seed...")
    seed()
    logger.info("Seed complete.")
