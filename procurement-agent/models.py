# procurement-agent/models.py
#
# Single source of truth: re-export everything from shared/schemas/recommend.py.
# main.py imports: RecommendRequest, RecommendResponse, RecommendationItem,
#                  Baseline, GraphStats, LiveMarketData
# All of those are now defined (or aliased) in the shared schema.
from shared.schemas.recommend import (
    RecommendRequest,
    SupplierRecommendation,
    SupplierRecommendation as RecommendationItem,   # alias used by main.py
    Baseline,
    GraphStats,
    LiveMarketData,
    RecommendResponse,
)

__all__ = [
    "RecommendRequest",
    "SupplierRecommendation",
    "RecommendationItem",
    "Baseline",
    "GraphStats",
    "LiveMarketData",
    "RecommendResponse",
]
