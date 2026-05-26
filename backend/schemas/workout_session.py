from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class ExerciseCreate(BaseModel):
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    duration_seconds: Optional[int] = None


class WorkoutCreate(BaseModel):
    program_id: UUID
    session_type: str = "strength"
    energy_level: Optional[int] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    logged_at: datetime
    exercises: List[ExerciseCreate] = []

    @field_validator("energy_level")
    @classmethod
    def validate_energy(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 1 <= v <= 5:
            raise ValueError("Energy level must be between 1 and 5")
        return v


class ExerciseResponse(BaseModel):
    id: UUID
    exercise_name: str
    sets: Optional[int]
    reps: Optional[int]
    weight_kg: Optional[float]
    duration_seconds: Optional[int]

    model_config = {"from_attributes": True}


class WorkoutResponse(BaseModel):
    id: UUID
    member_id: UUID
    program_id: UUID
    session_type: str
    energy_level: Optional[int]
    duration_minutes: Optional[int]
    notes: Optional[str]
    logged_at: datetime
    exercises: List[ExerciseResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
