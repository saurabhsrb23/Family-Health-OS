import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class AdherenceMetric(Base):
    __tablename__ = "adherence_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    component_type = Column(String(50), nullable=False)  # nutrition, strength, clinical
    metric_date = Column(Date, nullable=False)
    target_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    adherence_percentage = Column(Float, nullable=True)  # 0-100
    status = Column(String(50), nullable=True)  # met, partial, missed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # One record per member per component per day — prevents duplicate adherence entries
        UniqueConstraint(
            "member_id", "component_type", "metric_date",
            name="uq_adherence_member_component_date",
        ),
        Index("ix_adherence_member_date", "member_id", "metric_date"),
    )

    # Relationships
    program = relationship("CareProgram")
    member = relationship("FamilyMember")
