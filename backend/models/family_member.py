import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey

from database import Base


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    relationship = Column(String(50), nullable=False)  # self, spouse, parent, child, other
    gender = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="family_members")
    care_programs = relationship(
        "CareProgram",
        back_populates="member",
        primaryjoin="and_(FamilyMember.id == CareProgram.member_id, CareProgram.deleted_at == None)",
    )
