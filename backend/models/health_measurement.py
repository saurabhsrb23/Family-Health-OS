import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class HealthMeasurement(Base):
    __tablename__ = "health_measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    measurement_type = Column(String(50), nullable=False)  # blood_pressure, weight, glucose
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    glucose_mgdl = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    measured_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_health_meas_member_date", "member_id", "measured_at"),
    )

    # Relationships
    member = relationship("FamilyMember")
    program = relationship("CareProgram", back_populates="health_measurements")
