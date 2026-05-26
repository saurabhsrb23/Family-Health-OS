import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from database import Base


class CareProgram(Base):
    __tablename__ = "care_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    phase = Column(Integer, default=1, server_default="1", nullable=False)  # 1, 2, or 3
    status = Column(String(50), default="active", server_default="active", nullable=False)
    # status: active, completed, paused, cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    member = relationship("FamilyMember", back_populates="care_programs")
    components = relationship(
        "ProgramComponent",
        back_populates="program",
        primaryjoin="CareProgram.id == ProgramComponent.program_id",
    )
    meal_logs = relationship(
        "MealLog",
        back_populates="program",
        primaryjoin="and_(CareProgram.id == MealLog.program_id, MealLog.deleted_at == None)",
    )
    workout_sessions = relationship(
        "WorkoutSession",
        back_populates="program",
        primaryjoin="and_(CareProgram.id == WorkoutSession.program_id, WorkoutSession.deleted_at == None)",
    )
    health_measurements = relationship(
        "HealthMeasurement",
        back_populates="program",
        primaryjoin="and_(CareProgram.id == HealthMeasurement.program_id, HealthMeasurement.deleted_at == None)",
    )


class ProgramComponent(Base):
    __tablename__ = "program_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    component_type = Column(String(50), nullable=False)  # nutrition, strength, clinical
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    # config examples:
    # nutrition:  {"daily_calorie_target": 2000, "daily_protein_target_g": 60, "meals_per_day": 3}
    # strength:   {"sessions_per_week": 4, "session_duration_minutes": 60}
    # clinical:   {"bp_checks_per_week": 2, "weight_checks_per_week": 3, "checkin_frequency_days": 14}
    config = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    program = relationship("CareProgram", back_populates="components")
