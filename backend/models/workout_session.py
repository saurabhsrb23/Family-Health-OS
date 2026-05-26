import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    session_type = Column(String(100), nullable=False)  # strength, cardio, flexibility, mixed
    energy_level = Column(Integer, nullable=True)  # 1-5
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_workout_sessions_member_date", "member_id", "logged_at"),
    )

    # Relationships
    member = relationship("FamilyMember")
    program = relationship("CareProgram", back_populates="workout_sessions")
    exercise_logs = relationship("ExerciseLog", back_populates="session", cascade="all, delete-orphan")


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("workout_sessions.id"), nullable=False, index=True)
    exercise_name = Column(String(255), nullable=False)
    sets = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("WorkoutSession", back_populates="exercise_logs")
