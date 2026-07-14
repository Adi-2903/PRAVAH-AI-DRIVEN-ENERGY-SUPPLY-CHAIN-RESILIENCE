from datetime import datetime
from pydantic import BaseModel
from .risk_score import RiskScoreResponse
from .simulate import SimulateResponse
from .recommend import RecommendResponse
from .spr_schedule import SPRScheduleResponse

class CoordinatorRequest(BaseModel):
    corridor: str
    target_refinery: str = "REF_JAMNAGAR"

class CoordinatorResponse(BaseModel):
    summary: str
    risk: RiskScoreResponse
    scenario: SimulateResponse
    procurement: RecommendResponse
    spr: SPRScheduleResponse
    as_of: datetime
