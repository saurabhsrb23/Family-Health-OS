from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, model_validator


class MeasurementCreate(BaseModel):
    program_id: UUID
    measurement_type: Literal["blood_pressure", "weight", "glucose"]
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    weight_kg: Optional[float] = None
    glucose_mgdl: Optional[float] = None
    notes: Optional[str] = None
    measured_at: datetime

    @model_validator(mode="after")
    def validate_measurement_fields(self) -> "MeasurementCreate":
        if self.measurement_type == "blood_pressure":
            if self.systolic_bp is None or self.diastolic_bp is None:
                raise ValueError("Blood pressure requires both systolic_bp and diastolic_bp")
        elif self.measurement_type == "weight":
            if self.weight_kg is None:
                raise ValueError("Weight measurement requires weight_kg")
        elif self.measurement_type == "glucose":
            if self.glucose_mgdl is None:
                raise ValueError("Glucose measurement requires glucose_mgdl")
        return self


class MeasurementResponse(BaseModel):
    id: UUID
    member_id: UUID
    program_id: UUID
    measurement_type: str
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    weight_kg: Optional[float]
    glucose_mgdl: Optional[float]
    notes: Optional[str]
    measured_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
