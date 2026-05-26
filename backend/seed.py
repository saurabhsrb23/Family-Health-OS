"""
Seed script — populates demo data on first run.
Idempotent: safe to run multiple times (skips if data already exists).

Demo credentials:
  Email:    demo@familyhealthos.com
  Password: Demo@1234
"""

import sys
import logging
from database import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed():
    # Ensure tables exist
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
    """
    Seed placeholder — extended in Module 2 once models exist.

    When models are available this will create:
      - 1 demo user  (demo@praan.health / Demo@1234)
      - 2 family members  (Parent 1, Parent 2)
      - 1 active 90-day care program  (starts today)
      - Program components (nutrition + strength + clinical)
      - Sample meal logs, workout sessions, health measurements
    """
    # ── Guard: check if models exist yet ─────────────────────────────────────
    try:
        from models.user import User  # noqa
    except ImportError:
        logger.info("Models not yet defined (Module 2). Skipping seed data.")
        return

    # ── Guard: skip if already seeded ────────────────────────────────────────
    existing = db.execute(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM users")
    ).scalar()
    if existing > 0:
        logger.info(f"Database already has {existing} user(s). Skipping seed.")
        return

    # ── Seed will be filled in Module 2 ──────────────────────────────────────
    logger.info("Seed data will be populated in Module 2 once models are defined.")


if __name__ == "__main__":
    logger.info("Starting seed...")
    seed()
    logger.info("Seed complete.")
