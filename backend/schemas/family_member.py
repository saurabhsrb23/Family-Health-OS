from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class MemberCreate(BaseModel):
    name: str
    date_of_birth: Optional[date] = None
    relationship: Literal["self", "spouse", "parent", "child", "other"]
    gender: Optional[str] = None
    phone: Optional[str] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None


class ActiveProgramSummary(BaseModel):
    id: UUID
    title: str
    day_number: int
    days_remaining: int
    phase: int
    status: str


class MemberResponse(BaseModel):
    id: UUID
    name: str
    date_of_birth: Optional[date]
    relationship: str
    gender: Optional[str]
    phone: Optional[str]
    is_active: bool
    active_program: Optional[ActiveProgramSummary] = None
    created_at: datetime

    model_config = {"from_attributes": True}
