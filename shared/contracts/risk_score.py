from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Corridor = Literal["hormuz", "redsea", "cape", "domestic"]
AlertLevel = Literal["low", "elevated", "high", "critical"]


class RiskScoreRequest(BaseModel):
    corridor: Corridor
    as_of: datetime


class RiskSignal(BaseModel):
    type: str
    source: str
    weight: float
    detail: str


class KeyEvent(BaseModel):
    headline: str
    severity: Literal["low", "medium", "high", "critical"]
    date: datetime


class RiskScoreResponse(BaseModel):
    corridor: Corridor
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    alert_level: AlertLevel
    signals: list[RiskSignal] = []
    reasoning_trail: list[str]
    key_events: list[KeyEvent]
    computed_at: datetime
    data_sources: list[str]
    model: str = "Pravah Risk Engine v1"
