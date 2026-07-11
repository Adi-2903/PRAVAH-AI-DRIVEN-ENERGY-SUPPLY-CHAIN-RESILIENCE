from datetime import date, datetime
from pydantic import BaseModel


class SprScheduleRequest(BaseModel):
    shock_duration_days: int
    supply_gap_mbpd: float
    current_cover_days: float = 9.5


class SprScheduleResponse(BaseModel):
    recommended_release_mbpd: float
    release_duration_days: int
    start_date: date
    cover_days_before: float
    cover_days_after: float
    optimization_objective: str
    constraint_notes: list[str]
    computed_at: datetime
