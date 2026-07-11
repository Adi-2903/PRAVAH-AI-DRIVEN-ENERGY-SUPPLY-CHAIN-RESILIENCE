from datetime import datetime
from pydantic import BaseModel


class RecommendRequest(BaseModel):
    blocked_corridors: list[str]
    required_volume_mbpd: float
    max_transit_days: int
    scenario_id: str | None = None


class SupplierRecommendation(BaseModel):
    rank: int
    supplier: str
    country: str
    corridor: str
    grade: str
    cost_index: float
    transit_days: int
    risk_score: float
    rationale: str


class RecommendResponse(BaseModel):
    recommendations: list[SupplierRecommendation]
    total_suppliers_evaluated: int
    graph_paths_analyzed: int
    computed_at: datetime
