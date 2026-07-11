import networkx as nx
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict

from .procurement_models import RecommendRequest, RecommendResponse, RecommendationItem, Baseline, GraphStats
from shared.db.knowledge_graph import build_supply_chain_graph

router = APIRouter(prefix="/api/procurement")

G = build_supply_chain_graph()

# ── Real-world cost & risk data per supplier ──────────────────────────────────
# Costs in USD/bbl (approximate FOB + freight to India).
# Risks are corridor risk scores (0–100) based on geopolitical data.
SUPPLIER_DATA: Dict[str, dict] = {
    "SAU_ARAMCO":  {"cost": 82.4, "risk": 78, "grade": "Arab Light",  "country": "Saudi Arabia", "flag": "🇸🇦"},
    "IRQ_SOMO":    {"cost": 79.1, "risk": 60, "grade": "Basra Light",  "country": "Iraq",          "flag": "🇮🇶"},
    "RUS_ROSNEFT": {"cost": 68.5, "risk": 45, "grade": "Urals",        "country": "Russia",        "flag": "🇷🇺"},
    "NGA_NNPC":    {"cost": 85.2, "risk": 28, "grade": "Bonny Light",  "country": "Nigeria",       "flag": "🇳🇬"},
}

CORRIDOR_RISK: Dict[str, int] = {
    "hormuz": 78,
    "redsea": 52,
    "cape":   18,
}

@router.get("/graph")
def get_graph():
    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)]
    return {"nodes": nodes, "edges": edges}

@router.get("/recommend/mock")
def recommend_mock():
    return {
        "recommendations": [
            {
                "supplier": "IRQ_SOMO", "route": "hormuz", "port": "PORT_VADINAR",
                "grade_match": "FUEL_DIESEL", "grade_compatibility_score": 0.95,
                "estimated_cost_usd_per_bbl": 79.1, "transit_days": 3,
                "corridor_risk_score": 60, "composite_score": 0.55, "rank": 1,
                "reasoning": "Lower corridor risk by 18 pts vs Saudi baseline, cost saving of $3.30/bbl, transit +1d"
            }
        ],
        "current_supplier_baseline": {
            "supplier": "SAU_ARAMCO", "estimated_cost_usd_per_bbl": 82.4,
            "transit_days": 2, "corridor_risk_score": 78, "composite_score": 0.36
        },
        "graph_stats": {"nodes_considered": 18, "edges_traversed": 52},
        "computed_at": datetime.now().isoformat()
    }

@router.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    global G

    if req.target_refinery not in G.nodes or G.nodes[req.target_refinery].get("type") != "refinery":
        raise HTTPException(status_code=400, detail=f"Refinery '{req.target_refinery}' not found in graph")

    if req.required_crude_grade not in G.nodes or G.nodes[req.required_crude_grade].get("type") != "fuel":
        raise HTTPException(status_code=400, detail=f"Fuel grade '{req.required_crude_grade}' not found in graph")

    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]

    # ── Find the BEST path per supplier (dedup by supplier) ───────────────────
    # Key insight: a supplier can reach the target refinery via multiple ports.
    # We only want the single best path per supplier, scored by composite metric.
    edges_traversed = 0
    best_per_supplier: Dict[str, dict] = {}

    for supplier in suppliers:
        sdata = SUPPLIER_DATA.get(supplier, {})
        cost = sdata.get("cost", 80.0)
        grade = sdata.get("grade", "Unknown")
        country = sdata.get("country", supplier)
        flag = sdata.get("flag", "🌍")

        try:
            paths = list(nx.all_simple_paths(G, source=supplier, target=req.required_crude_grade))
        except nx.NetworkXNoPath:
            paths = []

        for path in paths:
            edges_traversed += len(path) - 1
            if req.target_refinery not in path:
                continue

            route = path[1]   # corridor
            port  = path[2]   # port
            transit_days = G[supplier][route].get("transit_days", 10)
            corridor_risk = CORRIDOR_RISK.get(route, 50)

            # For current supplier, override risk with actual provided score
            if supplier == req.current_supplier:
                corridor_risk = req.current_corridor_risk_score

            cand = {
                "supplier": supplier,
                "route": route,
                "port": port,
                "grade_match": req.required_crude_grade,
                "grade_compatibility_score": 0.95,
                "estimated_cost_usd_per_bbl": cost,
                "transit_days": transit_days,
                "corridor_risk_score": corridor_risk,
                "country": country,
                "flag": flag,
                "grade": grade,
            }

            # Composite score (higher = better) — used for deduplication within supplier
            composite = (
                req.cost_weight     * (1 - cost / 100.0) +
                req.risk_weight     * (1 - corridor_risk / 100.0) +
                req.transit_time_weight * (1 - transit_days / 60.0)
            )
            cand["composite_score"] = round(composite, 3)

            # Keep only the best-scoring path per supplier
            if supplier not in best_per_supplier or composite > best_per_supplier[supplier]["composite_score"]:
                best_per_supplier[supplier] = cand

    if not best_per_supplier:
        raise HTTPException(status_code=404, detail="No routes found through target refinery")

    # ── Build baseline from current supplier ────────────────────────────────────
    if req.current_supplier in best_per_supplier:
        bl = best_per_supplier[req.current_supplier]
    else:
        sdata = SUPPLIER_DATA.get(req.current_supplier, {})
        bl = {
            "supplier": req.current_supplier,
            "route": "hormuz",
            "port": "PORT_VADINAR",
            "estimated_cost_usd_per_bbl": sdata.get("cost", 82.0),
            "transit_days": 2,
            "corridor_risk_score": req.current_corridor_risk_score,
        }

    b_composite = (
        req.cost_weight     * (1 - bl["estimated_cost_usd_per_bbl"] / 100.0) +
        req.risk_weight     * (1 - bl["corridor_risk_score"] / 100.0) +
        req.transit_time_weight * (1 - bl["transit_days"] / 60.0)
    )

    baseline_out = Baseline(
        supplier=bl["supplier"],
        estimated_cost_usd_per_bbl=bl["estimated_cost_usd_per_bbl"],
        transit_days=bl["transit_days"],
        corridor_risk_score=bl["corridor_risk_score"],
        composite_score=round(b_composite, 2),
    )

    # ── Score and rank ALTERNATIVES (exclude current supplier) ─────────────────
    alternatives = []
    for supplier, cand in best_per_supplier.items():
        if supplier == req.current_supplier:
            continue

        cost_delta    = cand["estimated_cost_usd_per_bbl"] - bl["estimated_cost_usd_per_bbl"]
        risk_delta    = cand["corridor_risk_score"]          - bl["corridor_risk_score"]
        transit_delta = cand["transit_days"]                 - bl["transit_days"]

        # Build human-readable reasoning
        parts = []
        if risk_delta < 0:
            parts.append(f"Risk ↓ {-risk_delta:.0f} pts vs {bl['supplier']}")
        elif risk_delta > 0:
            parts.append(f"Risk ↑ {risk_delta:.0f} pts vs {bl['supplier']}")
        else:
            parts.append("Same corridor risk")

        if cost_delta < 0:
            parts.append(f"Saves ${-cost_delta:.2f}/bbl")
        elif cost_delta > 0:
            parts.append(f"+${cost_delta:.2f}/bbl cost premium")
        else:
            parts.append("Same price")

        if transit_delta < 0:
            parts.append(f"Faster by {-transit_delta}d")
        elif transit_delta > 0:
            parts.append(f"+{transit_delta}d transit")
        else:
            parts.append("Same transit time")

        grade = cand.get("grade", "")
        if grade:
            parts.append(f"Grade: {grade}")

        cand["reasoning"] = " · ".join(parts)
        alternatives.append(cand)

    # Sort by composite score (best first)
    alternatives.sort(key=lambda x: x["composite_score"], reverse=True)

    top_n = alternatives[:req.max_alternatives]

    if not top_n:
        raise HTTPException(status_code=404, detail="No alternative suppliers found (only current supplier has routes)")

    final_recs = []
    _fields = set(RecommendationItem.model_fields.keys()) if hasattr(RecommendationItem, "model_fields") else set(RecommendationItem.__fields__.keys())
    for idx, c in enumerate(top_n):
        c["rank"] = idx + 1
        final_recs.append(RecommendationItem(**{k: v for k, v in c.items() if k in _fields}))

    return RecommendResponse(
        recommendations=final_recs,
        current_supplier_baseline=baseline_out,
        graph_stats=GraphStats(nodes_considered=len(G.nodes), edges_traversed=edges_traversed),
        computed_at=datetime.now().isoformat(),
    )
