from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class MealLogCreate(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    logged_at: datetime
    program_id: UUID


class MealLogResponse(BaseModel):
    id: UUID
    member_id: UUID
    program_id: UUID
    meal_type: str
    photo_url: Optional[str]
    calories: Optional[float]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    food_description: Optional[str]
    extraction_status: str
    logged_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractionStatusResponse(BaseModel):
    meal_id: UUID
    extraction_status: str
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    food_description: Optional[str] = None
