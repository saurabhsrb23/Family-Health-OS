"""Initial schema — all tables for Family Health OS

Revision ID: 001
Revises: None
Create Date: 2026-05-26

Creates all 11 tables in FK-dependency order:
  1.  users
  2.  family_members
  3.  care_programs
  4.  program_components
  5.  meal_logs
  6.  workout_sessions
  7.  exercise_logs
  8.  health_measurements
  9.  adherence_metrics
  10. program_summaries
  11. audit_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── 1. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── 2. family_members ─────────────────────────────────────────────────────
    op.create_table(
        "family_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("relationship", sa.String(50), nullable=False),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_family_members_user_id", "family_members", ["user_id"])

    # ── 3. care_programs ──────────────────────────────────────────────────────
    op.create_table(
        "care_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("phase", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_care_programs_member_id", "care_programs", ["member_id"])

    # ── 4. program_components ─────────────────────────────────────────────────
    op.create_table(
        "program_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("component_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_program_components_program_id", "program_components", ["program_id"])

    # ── 5. meal_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "meal_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("photo_key", sa.String(500), nullable=True),
        sa.Column("meal_type", sa.String(50), nullable=False),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("food_description", sa.Text(), nullable=True),
        sa.Column("extraction_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("extraction_error", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_meal_logs_program_id", "meal_logs", ["program_id"])
    op.create_index("ix_meal_logs_member_id", "meal_logs", ["member_id"])
    op.create_index("ix_meal_logs_member_date", "meal_logs", ["member_id", "logged_at"])

    # ── 6. workout_sessions ───────────────────────────────────────────────────
    op.create_table(
        "workout_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("session_type", sa.String(100), nullable=False),
        sa.Column("energy_level", sa.Integer(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_workout_sessions_program_id", "workout_sessions", ["program_id"])
    op.create_index("ix_workout_sessions_member_id", "workout_sessions", ["member_id"])
    op.create_index("ix_workout_sessions_member_date", "workout_sessions", ["member_id", "logged_at"])

    # ── 7. exercise_logs ──────────────────────────────────────────────────────
    op.create_table(
        "exercise_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workout_sessions.id"), nullable=False),
        sa.Column("exercise_name", sa.String(255), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_exercise_logs_session_id", "exercise_logs", ["session_id"])

    # ── 8. health_measurements ────────────────────────────────────────────────
    op.create_table(
        "health_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("measurement_type", sa.String(50), nullable=False),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("glucose_mgdl", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_health_measurements_program_id", "health_measurements", ["program_id"])
    op.create_index("ix_health_measurements_member_id", "health_measurements", ["member_id"])
    op.create_index("ix_health_meas_member_date", "health_measurements", ["member_id", "measured_at"])

    # ── 9. adherence_metrics ──────────────────────────────────────────────────
    op.create_table(
        "adherence_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("component_type", sa.String(50), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("adherence_percentage", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_adherence_metrics_program_id", "adherence_metrics", ["program_id"])
    op.create_index("ix_adherence_metrics_member_id", "adherence_metrics", ["member_id"])
    op.create_index("ix_adherence_member_date", "adherence_metrics", ["member_id", "metric_date"])
    op.create_unique_constraint(
        "uq_adherence_member_component_date",
        "adherence_metrics",
        ["member_id", "component_type", "metric_date"],
    )

    # ── 10. program_summaries ─────────────────────────────────────────────────
    op.create_table(
        "program_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_programs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id"), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("week_start_date", sa.Date(), nullable=True),
        sa.Column("week_end_date", sa.Date(), nullable=True),
        sa.Column("generation_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("program_progress_pct", sa.Float(), nullable=True),
        sa.Column("nutrition_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strength_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("clinical_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommended_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_program_summaries_program_id", "program_summaries", ["program_id"])
    op.create_index("ix_program_summaries_member_id", "program_summaries", ["member_id"])
    op.create_unique_constraint(
        "uq_summary_program_week",
        "program_summaries",
        ["program_id", "week_number"],
    )

    # ── 11. audit_logs ────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),      # no FK — intentional
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),    # no FK — intentional
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_path", sa.String(500), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        # Append-only: no updated_at, no deleted_at
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    # Drop in reverse FK-dependency order
    op.drop_table("audit_logs")
    op.drop_table("program_summaries")
    op.drop_table("adherence_metrics")
    op.drop_table("health_measurements")
    op.drop_table("exercise_logs")
    op.drop_table("workout_sessions")
    op.drop_table("meal_logs")
    op.drop_table("program_components")
    op.drop_table("care_programs")
    op.drop_table("family_members")
    op.drop_table("users")
