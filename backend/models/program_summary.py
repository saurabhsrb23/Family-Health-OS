import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from database import Base


class ProgramSummary(Base):
    __tablename__ = "program_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False)  # 1-13
    week_start_date = Column(Date, nullable=True)
    week_end_date = Column(Date, nullable=True)
    generation_status = Column(String(50), default="pending", server_default="pending", nullable=False)
    # generation_status: pending, completed, failed
    summary_text = Column(Text, nullable=True)
    program_progress_pct = Column(Float, nullable=True)
    nutrition_summary = Column(JSONB, nullable=True)
    strength_summary = Column(JSONB, nullable=True)
    clinical_summary = Column(JSONB, nullable=True)
    risks = Column(JSONB, nullable=True)               # list of risk strings
    recommended_actions = Column(JSONB, nullable=True)  # list of action strings
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # One summary per program per week
        UniqueConstraint("program_id", "week_number", name="uq_summary_program_week"),
    )

    # Relationships
    program = relationship("CareProgram")
    member = relationship("FamilyMember")
