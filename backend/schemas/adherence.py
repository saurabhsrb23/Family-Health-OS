from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DailyAdherence(BaseModel):
    date: date
    adherence_pct: float
    status: str
    target_value: Optional[float]
    actual_value: Optional[float]


class RollingAdherence(BaseModel):
    average_pct: float
    trend: str  # improving | declining | stable
    days: List[DailyAdherence]


class NutritionAdherence(BaseModel):
    today_calories_target: Optional[float]
    today_calories_actual: Optional[float]
    today_protein_target: Optional[float]
    today_protein_actual: Optional[float]
    today_adherence_pct: float
    today_status: str
    rolling_7day: RollingAdherence


class StrengthAdherence(BaseModel):
    sessions_this_week: int
    target_sessions: int
    week_adherence_pct: float
    rolling_7day: RollingAdherence


class ClinicalAdherence(BaseModel):
    measurements_this_week: int
    target_measurements: int
    week_adherence_pct: float


class FullAdherenceReport(BaseModel):
    member_id: UUID
    report_date: date
    nutrition: NutritionAdherence
    strength: StrengthAdherence
    clinical: ClinicalAdherence
    overall_pct: float
