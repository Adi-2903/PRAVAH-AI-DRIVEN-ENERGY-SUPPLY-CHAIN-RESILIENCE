from pydantic import BaseModel, Field, model_validator
from typing import List, Optional


class RecommendRequest(BaseModel):
    current_supplier: str
    current_corridor_risk_score: float = Field(ge=0, le=100)
    target_refinery: str
    required_crude_grade: str
    cost_weight: float = Field(ge=0, le=1)
    risk_weight: float = Field(ge=0, le=1)
    transit_time_weight: float = Field(ge=0, le=1)
    max_alternatives: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def normalize_weights(self):
        w_sum = self.cost_weight + self.risk_weight + self.transit_time_weight
        if not (0.99 <= w_sum <= 1.01):
            if w_sum > 0:
                self.cost_weight       /= w_sum
                self.risk_weight       /= w_sum
                self.transit_time_weight /= w_sum
            else:
                raise ValueError("Weights cannot sum to zero")
        return self


class RecommendationItem(BaseModel):
    supplier: str
    route: str
    port: str
    grade_match: str
    grade_compatibility_score: float
    estimated_cost_usd_per_bbl: float
    transit_days: int
    corridor_risk_score: float
    composite_score: float
    rank: int
    reasoning: str


class Baseline(BaseModel):
    supplier: str
    estimated_cost_usd_per_bbl: float
    transit_days: int
    corridor_risk_score: float
    composite_score: float


class GraphStats(BaseModel):
    nodes_considered: int
    edges_traversed: int


class LiveMarketData(BaseModel):
    brent_usd: float
    wti_usd: float
    usd_inr: float
    is_live: bool
    fetched_at: str


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem]
    current_supplier_baseline: Baseline
    graph_stats: GraphStats
    computed_at: str
    market_data: Optional[LiveMarketData] = None
