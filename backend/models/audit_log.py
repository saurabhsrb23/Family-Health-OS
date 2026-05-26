import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)      # null for unauthenticated requests
    member_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)              # e.g. CREATE_MEAL_LOG, READ_MEMBER
    resource_type = Column(String(100), nullable=True)        # MealLog, Member, CareProgram
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_path = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Append-only — no updated_at, no deleted_at, no soft delete
    # Audit logs are permanent records for compliance and PHI access tracking
