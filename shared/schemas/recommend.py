"""
shared/schemas/recommend.py  —  Pravah Procurement Agent contract  (v2)

This is the canonical schema. procurement-agent/models.py imports from here
so both ends are always in sync.

v2 changes vs v1:
  - RecommendRequest completely replaced (target_refinery, crude_grade,
    weights instead of blocked_corridors / required_volume_mbpd)
  - SupplierRecommendation: grade→grade_match, cost_index→estimated_cost_usd_per_bbl,
    risk_score→corridor_risk_score, rationale→reasoning; added route, port,
    grade_compatibility_score, composite_score
  - RecommendResponse: added current_supplier_baseline, graph_stats, market_data;
    removed total_suppliers_evaluated / graph_paths_analyzed
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


# ── Request ────────────────────────────────────────────────────────────────────

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
                self.cost_weight          /= w_sum
                self.risk_weight          /= w_sum
                self.transit_time_weight  /= w_sum
            else:
                raise ValueError("Weights cannot sum to zero")
        return self


# ── Response sub-models ────────────────────────────────────────────────────────

class SupplierRecommendation(BaseModel):
    """One ranked alternative supplier route."""
    rank: int
    supplier: str
    route: str
    port: str
    grade_match: str
    grade_compatibility_score: float
    estimated_cost_usd_per_bbl: float
    transit_days: int
    corridor_risk_score: float
    composite_score: float
    reasoning: str

# Backward-compat alias used by procurement-agent/main.py
RecommendationItem = SupplierRecommendation


class Baseline(BaseModel):
    """Current supplier used as the scoring benchmark."""
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


# ── Top-level response ─────────────────────────────────────────────────────────

class RecommendResponse(BaseModel):
    recommendations: list[SupplierRecommendation]
    current_supplier_baseline: Baseline
    graph_stats: GraphStats
    computed_at: str                          # ISO-8601 string from .isoformat()
    market_data: Optional[LiveMarketData] = None
