from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class NutritionConfig(BaseModel):
    daily_calorie_target: int = 2000
    daily_protein_target_g: float = 60.0
    meals_per_day: int = 3


class StrengthConfig(BaseModel):
    sessions_per_week: int = 4
    session_duration_minutes: int = 60


class ClinicalConfig(BaseModel):
    bp_checks_per_week: int = 2
    weight_checks_per_week: int = 3
    checkin_frequency_days: int = 14


class ProgramCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    nutrition_config: NutritionConfig
    strength_config: StrengthConfig
    clinical_config: ClinicalConfig


class ProgramUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # active, completed, paused, cancelled


class ComponentResponse(BaseModel):
    id: UUID
    component_type: str
    is_active: bool
    config: Dict[str, Any]

    model_config = {"from_attributes": True}


class ProgramResponse(BaseModel):
    id: UUID
    member_id: UUID
    title: str
    description: Optional[str]
    start_date: date
    end_date: date
    phase: int
    status: str
    day_number: int
    days_remaining: int
    components: List[ComponentResponse]
    created_at: datetime

    model_config = {"from_attributes": True}
