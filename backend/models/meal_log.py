import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("care_programs.id"), nullable=False, index=True)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=True)
    photo_key = Column(String(500), nullable=True)
    meal_type = Column(String(50), nullable=False)  # breakfast, lunch, dinner, snack
    calories = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    food_description = Column(Text, nullable=True)
    extraction_status = Column(String(50), default="pending", server_default="pending", nullable=False)
    # extraction_status: pending, processing, completed, failed
    extraction_error = Column(Text, nullable=True)
    logged_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_meal_logs_member_date", "member_id", "logged_at"),
    )

    # Relationships
    member = relationship("FamilyMember")
    program = relationship("CareProgram", back_populates="meal_logs")
