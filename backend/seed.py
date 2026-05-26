"""
Seed script — populates realistic demo data for Family Health OS.
Idempotent: skips if demo user already exists.

Demo credentials:
  Email:    demo@familyhealthos.com
  Password: Demo@1234

Data created:
  - 1 demo user
  - Rahul Sharma (self) — 30-day active program, rich historical data
  - Priya Sharma (spouse) — 15-day active program, lighter data set
"""

import random
import uuid
import logging
from datetime import date, datetime, timedelta

from passlib.context import CryptContext

from database import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
random.seed(42)  # reproducible data across rebuilds


# ── helpers ───────────────────────────────────────────────────────────────────

def _vary(base: float, pct: float = 0.15) -> float:
    """Return base ± pct variation."""
    return round(base * (1 + random.uniform(-pct, pct)), 1)


def _days_ago(n: int) -> datetime:
    return datetime.utcnow() - timedelta(days=n)


def _adherence_status(pct: float) -> str:
    return "met" if pct >= 90 else "partial" if pct >= 50 else "missed"


# ── main ──────────────────────────────────────────────────────────────────────

def seed(db):
    from models.user import User
    from models.family_member import FamilyMember
    from models.care_program import CareProgram, ProgramComponent
    from models.meal_log import MealLog
    from models.workout_session import WorkoutSession, ExerciseLog
    from models.health_measurement import HealthMeasurement
    from models.adherence_metric import AdherenceMetric
    from models.program_summary import ProgramSummary

    # ── 1. User ───────────────────────────────────────────────────────────────
    print("  Creating demo user...")
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

    # ── 2. Members ────────────────────────────────────────────────────────────
    print("  Creating member 1/2 — Rahul Sharma...")
    rahul = FamilyMember(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Rahul Sharma",
        date_of_birth=date(1985, 3, 15),
        relationship="self",
        gender="male",
        phone="+91-9876543210",
        is_active=True,
    )
    db.add(rahul)
    db.flush()

    print("  Creating member 2/2 — Priya Sharma...")
    priya = FamilyMember(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Priya Sharma",
        date_of_birth=date(1988, 7, 22),
        relationship="spouse",
        gender="female",
        phone="+91-9876543211",
        is_active=True,
    )
    db.add(priya)
    db.flush()

    # ── 3. Programs ───────────────────────────────────────────────────────────
    print("  Creating care programs...")
    rahul_start = date.today() - timedelta(days=30)
    rahul_program = CareProgram(
        id=uuid.uuid4(),
        member_id=rahul.id,
        title="Rahul's 90-Day Transformation",
        description="Comprehensive program focusing on strength, nutrition, and clinical monitoring.",
        start_date=rahul_start,
        end_date=rahul_start + timedelta(days=89),
        phase=2,
        status="active",
    )
    db.add(rahul_program)
    db.flush()

    priya_start = date.today() - timedelta(days=15)
    priya_program = CareProgram(
        id=uuid.uuid4(),
        member_id=priya.id,
        title="Priya's Wellness Journey",
        description="Balanced program for nutrition, strength and clinical health.",
        start_date=priya_start,
        end_date=priya_start + timedelta(days=89),
        phase=1,
        status="active",
    )
    db.add(priya_program)
    db.flush()

    # ── 4. Components ─────────────────────────────────────────────────────────
    print("  Creating program components...")
    r_components = [
        ProgramComponent(id=uuid.uuid4(), program_id=rahul_program.id, component_type="nutrition", is_active=True,
                         config={"daily_calorie_target": 2000, "daily_protein_target_g": 60, "meals_per_day": 3}),
        ProgramComponent(id=uuid.uuid4(), program_id=rahul_program.id, component_type="strength", is_active=True,
                         config={"sessions_per_week": 4, "session_duration_minutes": 60}),
        ProgramComponent(id=uuid.uuid4(), program_id=rahul_program.id, component_type="clinical", is_active=True,
                         config={"bp_checks_per_week": 2, "weight_checks_per_week": 3, "checkin_frequency_days": 14}),
    ]
    p_components = [
        ProgramComponent(id=uuid.uuid4(), program_id=priya_program.id, component_type="nutrition", is_active=True,
                         config={"daily_calorie_target": 1600, "daily_protein_target_g": 50, "meals_per_day": 3}),
        ProgramComponent(id=uuid.uuid4(), program_id=priya_program.id, component_type="strength", is_active=True,
                         config={"sessions_per_week": 3, "session_duration_minutes": 45}),
        ProgramComponent(id=uuid.uuid4(), program_id=priya_program.id, component_type="clinical", is_active=True,
                         config={"bp_checks_per_week": 1, "weight_checks_per_week": 2, "checkin_frequency_days": 14}),
    ]
    db.add_all(r_components + p_components)
    db.flush()

    # ── 5. Rahul's meal logs (30 days × 3 meals = 90 logs) ───────────────────
    print("  Creating meal logs for Rahul (90 logs)...")
    meal_templates = {
        "breakfast": [
            (380, 22, 45, 12, "Oatmeal with banana, eggs and almonds"),
            (420, 28, 38, 15, "Greek yogurt parfait with granola and berries"),
            (350, 18, 42, 11, "Whole wheat toast with avocado and poached eggs"),
            (400, 25, 40, 13, "Protein smoothie with milk, banana and peanut butter"),
        ],
        "lunch": [
            (650, 38, 72, 18, "Grilled chicken rice bowl with roasted vegetables"),
            (580, 32, 65, 16, "Quinoa salad with chickpeas, cucumber and feta"),
            (720, 42, 68, 22, "Dal makhani with brown rice and cucumber raita"),
            (600, 35, 70, 17, "Paneer bhurji with multigrain roti and salad"),
        ],
        "dinner": [
            (720, 45, 68, 22, "Baked salmon with quinoa and roasted broccoli"),
            (680, 40, 62, 20, "Chicken tikka with roti and mixed vegetable curry"),
            (550, 35, 58, 15, "Grilled fish with sweet potato and steamed beans"),
            (600, 38, 60, 18, "Egg curry with brown rice and raita"),
        ],
    }

    for day_offset in range(30):
        log_date = datetime.utcnow() - timedelta(days=day_offset)
        for meal_type in ["breakfast", "lunch", "dinner"]:
            tmpl = random.choice(meal_templates[meal_type])
            db.add(MealLog(
                id=uuid.uuid4(),
                program_id=rahul_program.id,
                member_id=rahul.id,
                meal_type=meal_type,
                calories=_vary(tmpl[0]),
                protein_g=_vary(tmpl[1]),
                carbs_g=_vary(tmpl[2]),
                fat_g=_vary(tmpl[3]),
                food_description=tmpl[4],
                extraction_status="completed",
                logged_at=log_date.replace(hour={"breakfast": 8, "lunch": 13, "dinner": 20}[meal_type]),
            ))

    # ── 6. Priya's meal logs (15 days × 3 meals = 45 logs) ───────────────────
    print("  Creating meal logs for Priya (45 logs)...")
    priya_meals = {
        "breakfast": [(320, 18, 38, 10, "Upma with vegetables and boiled egg"),
                      (280, 15, 35, 9,  "Poha with peanuts and green peas")],
        "lunch":     [(500, 28, 58, 14, "Rajma chawal with salad"),
                      (480, 25, 55, 13, "Curd rice with pickle and papad")],
        "dinner":    [(450, 30, 52, 12, "Palak paneer with roti and salad"),
                      (420, 27, 48, 11, "Grilled chicken with steamed rice and dal")],
    }
    for day_offset in range(15):
        log_date = datetime.utcnow() - timedelta(days=day_offset)
        for meal_type in ["breakfast", "lunch", "dinner"]:
            tmpl = random.choice(priya_meals[meal_type])
            db.add(MealLog(
                id=uuid.uuid4(),
                program_id=priya_program.id,
                member_id=priya.id,
                meal_type=meal_type,
                calories=_vary(tmpl[0]),
                protein_g=_vary(tmpl[1]),
                carbs_g=_vary(tmpl[2]),
                fat_g=_vary(tmpl[3]),
                food_description=tmpl[4],
                extraction_status="completed",
                logged_at=log_date.replace(hour={"breakfast": 7, "lunch": 13, "dinner": 20}[meal_type]),
            ))

    db.flush()

    # ── 7. Rahul's workouts (15 sessions over 4 weeks, Mon/Wed/Fri/Sat) ──────
    print("  Creating workout sessions for Rahul (15 sessions)...")
    exercise_pool = [
        ("Bench Press", 4, 10, 80.0),
        ("Squat", 4, 8, 100.0),
        ("Deadlift", 3, 6, 120.0),
        ("Pull-Up", 3, 10, None),
        ("Shoulder Press", 3, 12, 50.0),
        ("Barbell Row", 3, 10, 70.0),
        ("Leg Press", 4, 12, 140.0),
        ("Dumbbell Curl", 3, 15, 15.0),
    ]

    workout_day_offsets = [1, 3, 5, 6, 8, 10, 12, 13, 15, 17, 19, 20, 22, 24, 27]
    for offset in workout_day_offsets:
        session = WorkoutSession(
            id=uuid.uuid4(),
            program_id=rahul_program.id,
            member_id=rahul.id,
            session_type="strength",
            energy_level=random.choice([3, 4, 4, 5]),
            duration_minutes=random.choice([50, 55, 60, 65]),
            notes=random.choice(["Great session!", "Felt strong today", "Tough but completed", "PB on squats"]),
            logged_at=_days_ago(offset).replace(hour=18, minute=0),
        )
        db.add(session)
        db.flush()

        chosen = random.sample(exercise_pool, k=random.randint(4, 6))
        for ex in chosen:
            db.add(ExerciseLog(
                id=uuid.uuid4(),
                session_id=session.id,
                exercise_name=ex[0],
                sets=ex[1],
                reps=ex[2],
                weight_kg=ex[3],
            ))

    # ── 8. Priya's workouts (8 sessions over 2 weeks) ────────────────────────
    print("  Creating workout sessions for Priya (8 sessions)...")
    priya_exercises = [("Dumbbell Press", 3, 12, 12.0), ("Lunges", 3, 15, None),
                       ("Plank", 3, 60, None), ("Goblet Squat", 3, 12, 16.0)]

    for offset in [1, 3, 5, 7, 9, 11, 13, 14]:
        session = WorkoutSession(
            id=uuid.uuid4(),
            program_id=priya_program.id,
            member_id=priya.id,
            session_type="strength",
            energy_level=random.choice([3, 4, 4]),
            duration_minutes=random.choice([40, 45, 50]),
            notes="Good workout!",
            logged_at=_days_ago(offset).replace(hour=7, minute=0),
        )
        db.add(session)
        db.flush()
        for ex in priya_exercises:
            db.add(ExerciseLog(id=uuid.uuid4(), session_id=session.id,
                               exercise_name=ex[0], sets=ex[1], reps=ex[2], weight_kg=ex[3]))

    # ── 9. Rahul's health measurements (20 records — BP + weight) ────────────
    print("  Creating health measurements for Rahul (20 records)...")
    rahul_weight = 78.0
    for i in range(20):
        day_off = i + 1
        if i % 2 == 0:  # BP
            db.add(HealthMeasurement(
                id=uuid.uuid4(), program_id=rahul_program.id, member_id=rahul.id,
                measurement_type="blood_pressure",
                systolic_bp=random.randint(112, 128),
                diastolic_bp=random.randint(72, 84),
                measured_at=_days_ago(day_off).replace(hour=8),
            ))
        else:           # Weight (trending down)
            rahul_weight = round(rahul_weight - random.uniform(0.05, 0.15), 1)
            db.add(HealthMeasurement(
                id=uuid.uuid4(), program_id=rahul_program.id, member_id=rahul.id,
                measurement_type="weight", weight_kg=rahul_weight,
                measured_at=_days_ago(day_off).replace(hour=7),
            ))

    # ── 10. Priya's health measurements (10 records) ─────────────────────────
    print("  Creating health measurements for Priya (10 records)...")
    priya_weight = 62.0
    for i in range(10):
        day_off = i + 1
        if i % 3 == 0:
            db.add(HealthMeasurement(
                id=uuid.uuid4(), program_id=priya_program.id, member_id=priya.id,
                measurement_type="blood_pressure",
                systolic_bp=random.randint(108, 122),
                diastolic_bp=random.randint(68, 80),
                measured_at=_days_ago(day_off).replace(hour=8),
            ))
        else:
            priya_weight = round(priya_weight - random.uniform(0.03, 0.10), 1)
            db.add(HealthMeasurement(
                id=uuid.uuid4(), program_id=priya_program.id, member_id=priya.id,
                measurement_type="weight", weight_kg=priya_weight,
                measured_at=_days_ago(day_off).replace(hour=7),
            ))

    db.flush()

    # ── 11. Rahul's adherence metrics (30 days, nutrition component) ──────────
    print("  Creating adherence metrics for Rahul (30 days)...")
    protein_target = 60.0
    for day_offset in range(30):
        metric_date = date.today() - timedelta(days=day_offset)
        # Vary adherence: mostly good, some partial, occasional missed
        adherence_roll = random.random()
        if adherence_roll > 0.6:
            actual = _vary(protein_target, 0.05)   # met
        elif adherence_roll > 0.2:
            actual = _vary(protein_target * 0.75, 0.1)  # partial
        else:
            actual = _vary(protein_target * 0.45, 0.1)  # missed
        pct = min(100.0, round((actual / protein_target) * 100, 1))

        db.add(AdherenceMetric(
            id=uuid.uuid4(),
            program_id=rahul_program.id,
            member_id=rahul.id,
            component_type="nutrition",
            metric_date=metric_date,
            target_value=protein_target,
            actual_value=round(actual, 1),
            adherence_percentage=pct,
            status=_adherence_status(pct),
        ))

    # ── 12. Priya's adherence metrics (15 days) ───────────────────────────────
    print("  Creating adherence metrics for Priya (15 days)...")
    priya_protein_target = 50.0
    for day_offset in range(15):
        metric_date = date.today() - timedelta(days=day_offset)
        adherence_roll = random.random()
        if adherence_roll > 0.5:
            actual = _vary(priya_protein_target, 0.08)
        elif adherence_roll > 0.2:
            actual = _vary(priya_protein_target * 0.72, 0.1)
        else:
            actual = _vary(priya_protein_target * 0.42, 0.1)
        pct = min(100.0, round((actual / priya_protein_target) * 100, 1))

        db.add(AdherenceMetric(
            id=uuid.uuid4(),
            program_id=priya_program.id,
            member_id=priya.id,
            component_type="nutrition",
            metric_date=metric_date,
            target_value=priya_protein_target,
            actual_value=round(actual, 1),
            adherence_percentage=pct,
            status=_adherence_status(pct),
        ))

    db.flush()

    # ── 13. Weekly summaries ──────────────────────────────────────────────────
    print("  Creating weekly summaries for Rahul (weeks 1-4)...")
    for week in range(1, 5):
        week_start = rahul_start + timedelta(weeks=week - 1)
        elapsed = (date.today() - rahul_start).days + 1
        progress_pct = round(min(100.0, (elapsed / 90) * 100), 1)

        sessions_done = random.randint(3, 4)
        avg_protein = round(_vary(protein_target, 0.12), 1)
        nutrition_pct = round(min(100, (avg_protein / protein_target) * 100), 1)
        strength_pct = round(min(100, (sessions_done / 4) * 100), 1)

        db.add(ProgramSummary(
            id=uuid.uuid4(),
            program_id=rahul_program.id,
            member_id=rahul.id,
            week_number=week,
            week_start_date=week_start,
            week_end_date=week_start + timedelta(days=6),
            generation_status="completed",
            summary_text=(
                f"Week {week} showed {'strong' if nutrition_pct >= 75 else 'moderate'} progress. "
                f"Nutrition adherence at {round(nutrition_pct)}% and strength at {round(strength_pct)}%."
            ),
            program_progress_pct=progress_pct,
            nutrition_summary={
                "avgDailyCalories": round(_vary(2000, 0.1)),
                "avgDailyProtein": avg_protein,
                "targetCalories": 2000,
                "targetProtein": protein_target,
                "adherencePct": nutrition_pct,
                "highlight": "Protein on track" if nutrition_pct >= 80 else "Increase protein intake",
            },
            strength_summary={
                "sessionsCompleted": sessions_done,
                "targetSessions": 4,
                "adherencePct": strength_pct,
                "highlight": f"Completed {sessions_done}/4 sessions",
            },
            clinical_summary={
                "measurementsDone": random.randint(4, 5),
                "targetMeasurements": 5,
                "avgSystolic": random.randint(115, 125),
                "avgDiastolic": random.randint(74, 82),
                "weightChange": round(random.uniform(-0.5, -0.1), 1),
                "highlight": "BP within normal range",
            },
            risks=[
                "Protein intake slightly below target on 3 days" if nutrition_pct < 80
                else "No significant risks this week"
            ],
            recommended_actions=[
                "Add a protein-rich snack between meals" if nutrition_pct < 80
                else "Maintain current nutrition routine"
            ],
            generated_at=datetime.utcnow() - timedelta(days=30 - week * 7),
        ))

    print("  Creating weekly summaries for Priya (weeks 1-2)...")
    for week in range(1, 3):
        week_start = priya_start + timedelta(weeks=week - 1)
        elapsed = (date.today() - priya_start).days + 1
        progress_pct = round(min(100.0, (elapsed / 90) * 100), 1)

        sessions_done = random.randint(2, 3)
        avg_protein = round(_vary(priya_protein_target, 0.12), 1)
        nutrition_pct = round(min(100, (avg_protein / priya_protein_target) * 100), 1)
        strength_pct = round(min(100, (sessions_done / 3) * 100), 1)

        db.add(ProgramSummary(
            id=uuid.uuid4(),
            program_id=priya_program.id,
            member_id=priya.id,
            week_number=week,
            week_start_date=week_start,
            week_end_date=week_start + timedelta(days=6),
            generation_status="completed",
            summary_text=f"Week {week}: Nutrition {round(nutrition_pct)}%, Strength {round(strength_pct)}%.",
            program_progress_pct=progress_pct,
            nutrition_summary={"avgDailyProtein": avg_protein, "targetProtein": priya_protein_target,
                                "adherencePct": nutrition_pct, "highlight": "Good progress"},
            strength_summary={"sessionsCompleted": sessions_done, "targetSessions": 3,
                              "adherencePct": strength_pct, "highlight": f"{sessions_done}/3 sessions done"},
            clinical_summary={"measurementsDone": random.randint(2, 3), "targetMeasurements": 3,
                              "avgSystolic": random.randint(110, 120), "avgDiastolic": random.randint(70, 78),
                              "weightChange": round(random.uniform(-0.3, -0.05), 1), "highlight": "Healthy range"},
            risks=["Stay consistent with meal logging"],
            recommended_actions=["Set meal logging reminders for consistency"],
            generated_at=datetime.utcnow() - timedelta(days=15 - week * 7),
        ))

    db.commit()
    print()
    print("  Users:    1 (demo@familyhealthos.com)")
    print("  Members:  Rahul Sharma, Priya Sharma")
    print("  Programs: 2 active (Rahul=Day 30, Priya=Day 15)")
    print("  Meals:    135 logs (all AI-extracted)")
    print("  Workouts: 23 sessions")
    print("  Measurements: 30 records")
    print("  Adherence: 45 daily metrics")
    print("  Summaries: 6 weekly summaries")


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Seeding Family Health OS database...")
    init_db()
    db = SessionLocal()

    from models.user import User
    existing = db.query(User).filter(User.email == "demo@familyhealthos.com").first()
    if existing:
        print("Database already seeded. Skipping.")
        db.close()
    else:
        try:
            seed(db)
            print()
            print("Seed complete!")
            print("Login: demo@familyhealthos.com / Demo@1234")
        except Exception as e:
            db.rollback()
            logger.error(f"Seed failed: {e}", exc_info=True)
            raise
        finally:
            db.close()
