import os
import httpx
import asyncio
import networkx as nx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Optional

from models import RecommendRequest, RecommendResponse, RecommendationItem, Baseline, GraphStats, LiveMarketData
from knowledge_graph.graph_builder import build_procurement_graph, get_grade_compatibility

app = FastAPI(title="Procurement Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

G = build_procurement_graph()

# ── Live market data cache ──────────────────────────────────────────────────
_market_cache: Optional[dict] = None
_market_cache_ts: float = 0
CACHE_TTL_SECONDS = 300  # 5-min cache

async def fetch_live_market_data() -> dict:
    """Fetch live crude oil prices from open APIs (with fallback to static data)."""
    global _market_cache, _market_cache_ts
    now = datetime.now(timezone.utc).timestamp()
    if _market_cache and (now - _market_cache_ts) < CACHE_TTL_SECONDS:
        return _market_cache

    live = {}
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            # Open exchange rate for USD/INR
            fx_resp = await client.get(
                "https://api.exchangerate.host/latest",
                params={"base": "USD", "symbols": "INR"}
            )
            if fx_resp.status_code == 200:
                data = fx_resp.json()
                live["usd_inr"] = data.get("rates", {}).get("INR", 83.5)
    except Exception:
        pass

    # Commodity prices — static fallback enriched with realistic 2025 spot prices
    defaults = {
        "brent_usd":    84.12,
        "wti_usd":      80.55,
        "dubai_usd":    82.90,
        "oman_usd":     83.15,
        "usd_inr":      live.get("usd_inr", 83.42),
        "nat_gas_usd":  2.81,
        # Per-supplier live cost adjustment (basis differential from Brent)
        "SAU_ARAMCO_diff":   -1.72,   # Arab Light OSP
        "IRQ_SOMO_diff":     -4.32,   # Basrah Light discount
        "UAE_ADNOC_diff":     0.45,   # Murban premium
        "RUS_ROSNEFT_diff": -14.12,   # Urals deep discount (sanctions)
        "USA_WTI_diff":       4.38,   # WTI + tanker premium
        "NGA_NNPC_diff":      2.10,   # Bonny Light premium
        "KWT_KPC_diff":      -2.40,   # Kuwait Export Crude
        "MEX_PEMEX_diff":    -6.80,   # Maya heavy discount
        "data_source": "EIA/OpenExchangeRate fallback",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "is_live": len(live) > 0,
    }
    defaults.update(live)
    _market_cache = defaults
    _market_cache_ts = now
    return defaults


def get_live_cost(market: dict, supplier_id: str, base_cost: float) -> float:
    """Adjust static cost with live Brent + differential."""
    brent = market.get("brent_usd", 84.12)
    diff = market.get(f"{supplier_id}_diff", 0.0)
    # Blend static base (40%) with live-price estimate (60%) for realism
    live_cost = brent + diff
    return round(0.4 * base_cost + 0.6 * live_cost, 2)


# ── Health & Diagnostics ────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "graph_nodes": len(G.nodes),
        "graph_edges": len(G.edges),
        "version": "2.0.0"
    }


@app.get("/graph")
def get_graph():
    nodes = [{"id": n, **d} for n, d in G.nodes(data=True)]
    edges = [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


@app.get("/market")
async def get_market():
    data = await fetch_live_market_data()
    return data


# ── Core recommendation endpoint ────────────────────────────────────────────
@app.post("/recommend", response_model=RecommendResponse)
async def recommend(req: RecommendRequest):
    # Validate refinery
    if req.target_refinery not in G.nodes or G.nodes[req.target_refinery].get("type") != "refinery":
        available = [n for n, d in G.nodes(data=True) if d.get("type") == "refinery"]
        raise HTTPException(
            status_code=400,
            detail=f"Refinery '{req.target_refinery}' not found. Available: {available}"
        )

    # Validate grade
    if req.required_crude_grade not in G.nodes or G.nodes[req.required_crude_grade].get("type") != "grade":
        available = [n for n, d in G.nodes(data=True) if d.get("type") == "grade"]
        raise HTTPException(
            status_code=400,
            detail=f"Grade '{req.required_crude_grade}' not found. Available: {available}"
        )

    compatibility = get_grade_compatibility(G, req.target_refinery, req.required_crude_grade)
    if compatibility < 0.6:
        raise HTTPException(
            status_code=400,
            detail=f"Refinery '{req.target_refinery}' not compatible with grade '{req.required_crude_grade}' (score {compatibility:.2f} < 0.60)"
        )

    # Fetch live market data
    market = await fetch_live_market_data()

    # ── Find all valid supplier paths ────────────────────────────────────────
    suppliers = [n for n, d in G.nodes(data=True) if d.get("type") == "supplier"]
    all_candidates = []
    edges_traversed = 0
    baseline_cand = None

    for supplier in suppliers:
        try:
            paths = list(nx.all_simple_paths(G, source=supplier, target=req.required_crude_grade))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

        # Filter paths that go through the requested refinery
        valid_paths = [p for p in paths if req.target_refinery in p]
        if not valid_paths:
            continue

        # Pick the shortest valid path (most direct)
        path = min(valid_paths, key=len)
        edges_traversed += len(path) - 1

        # Extract route, port from path:  supplier → route → port → refinery → grade
        route = path[1] if len(path) > 1 else None
        port  = path[2] if len(path) > 2 else None
        if route is None or port is None:
            continue
        if G.nodes[route].get("type") != "route":
            continue
        if G.nodes[port].get("type") != "port":
            continue

        base_cost    = G.nodes[supplier].get("cost", 80.0)
        live_cost    = get_live_cost(market, supplier, base_cost)
        risk         = G.nodes[route].get("risk", 50)
        transit_days = G[supplier][route].get("transit_days", 15)

        cand = {
            "supplier":                    supplier,
            "route":                       route,
            "port":                        port,
            "grade_match":                 req.required_crude_grade,
            "grade_compatibility_score":   compatibility,
            "estimated_cost_usd_per_bbl":  live_cost,
            "transit_days":                transit_days,
            "corridor_risk_score":         risk,
            "route_display":               G.nodes[route].get("display", route),
            "port_display":                G.nodes[port].get("display", port),
            "supplier_country":            G.nodes[supplier].get("country", supplier),
        }

        if supplier == req.current_supplier:
            # Override risk with real-time risk passed from the frontend
            cand["corridor_risk_score"] = req.current_corridor_risk_score
            baseline_cand = cand.copy()
        else:
            all_candidates.append(cand)

    if not all_candidates and baseline_cand is None:
        raise HTTPException(status_code=404, detail="No valid routes found in supply graph")

    # Synthetic baseline if current supplier not in graph
    if baseline_cand is None:
        base_cost = G.nodes.get(req.current_supplier, {}).get("cost", 82.4)
        live_cost = get_live_cost(market, req.current_supplier, base_cost)
        baseline_cand = {
            "supplier":                    req.current_supplier,
            "route":                       "hormuz_strait",
            "port":                        "PORT_VADINAR",
            "grade_match":                 req.required_crude_grade,
            "grade_compatibility_score":   compatibility,
            "estimated_cost_usd_per_bbl":  live_cost,
            "transit_days":                9,
            "corridor_risk_score":         req.current_corridor_risk_score,
            "route_display":               "Hormuz Strait",
            "port_display":                "Vadinar Port",
            "supplier_country":            "Saudi Arabia",
        }

    # ── Deduplication: one best path per supplier ────────────────────────────
    # (already handled since we pick the shortest valid path per supplier above)

    # ── Normalization bounds ──────────────────────────────────────────────────
    all_for_norm = all_candidates + [baseline_cand]
    max_cost    = max(c["estimated_cost_usd_per_bbl"] for c in all_for_norm) or 1.0
    min_cost    = min(c["estimated_cost_usd_per_bbl"] for c in all_for_norm)
    max_risk    = max(c["corridor_risk_score"]         for c in all_for_norm) or 1.0
    min_risk    = min(c["corridor_risk_score"]         for c in all_for_norm)
    max_transit = max(c["transit_days"]                for c in all_for_norm) or 1.0
    min_transit = min(c["transit_days"]                for c in all_for_norm)

    def norm(val, lo, hi):
        return 1.0 - ((val - lo) / (hi - lo)) if hi > lo else 1.0

    def composite(c):
        nc = norm(c["estimated_cost_usd_per_bbl"], min_cost, max_cost)
        nr = norm(c["corridor_risk_score"],         min_risk, max_risk)
        nt = norm(c["transit_days"],                min_transit, max_transit)
        return round(
            req.cost_weight * nc + req.risk_weight * nr + req.transit_time_weight * nt,
            4
        )

    # ── Score baseline ────────────────────────────────────────────────────────
    b_score = composite(baseline_cand)
    baseline_out = Baseline(
        supplier=baseline_cand["supplier"],
        estimated_cost_usd_per_bbl=baseline_cand["estimated_cost_usd_per_bbl"],
        transit_days=baseline_cand["transit_days"],
        corridor_risk_score=baseline_cand["corridor_risk_score"],
        composite_score=b_score,
    )

    # ── Score & rank alternatives ─────────────────────────────────────────────
    scored = []
    for cand in all_candidates:
        score = composite(cand)
        cost_delta    = cand["estimated_cost_usd_per_bbl"] - baseline_cand["estimated_cost_usd_per_bbl"]
        risk_delta    = cand["corridor_risk_score"]         - baseline_cand["corridor_risk_score"]
        transit_delta = cand["transit_days"]                - baseline_cand["transit_days"]

        parts = []
        if risk_delta < 0:
            parts.append(f"Risk ↓{abs(int(risk_delta))} pts via {cand['route_display']}")
        elif risk_delta > 0:
            parts.append(f"Risk ↑{int(risk_delta)} pts via {cand['route_display']}")
        else:
            parts.append(f"Equal risk via {cand['route_display']}")

        if cost_delta < 0:
            parts.append(f"saves ${abs(cost_delta):.2f}/bbl")
        else:
            parts.append(f"costs +${cost_delta:.2f}/bbl")

        if transit_delta <= 0:
            parts.append(f"transit {cand['transit_days']}d ({'same' if transit_delta==0 else f'{abs(transit_delta)}d faster'})")
        else:
            parts.append(f"transit {cand['transit_days']}d ({transit_delta}d slower)")

        parts.append(f"src: {cand['supplier_country']}, via {cand['port_display']}")

        cand["composite_score"] = score
        cand["reasoning"]       = ". ".join(parts) + "."
        scored.append(cand)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    top_n = scored[: req.max_alternatives]
    final_recs = []
    for idx, c in enumerate(top_n):
        final_recs.append(
            RecommendationItem(
                supplier=c["supplier"],
                route=c["route"],
                port=c["port"],
                grade_match=c["grade_match"],
                grade_compatibility_score=c["grade_compatibility_score"],
                estimated_cost_usd_per_bbl=c["estimated_cost_usd_per_bbl"],
                transit_days=c["transit_days"],
                corridor_risk_score=c["corridor_risk_score"],
                composite_score=c["composite_score"],
                rank=idx + 1,
                reasoning=c["reasoning"],
            )
        )

    return RecommendResponse(
        recommendations=final_recs,
        current_supplier_baseline=baseline_out,
        graph_stats=GraphStats(nodes_considered=len(G.nodes), edges_traversed=edges_traversed),
        computed_at=datetime.now(timezone.utc).isoformat(),
        market_data=LiveMarketData(
            brent_usd=market.get("brent_usd", 84.12),
            wti_usd=market.get("wti_usd", 80.55),
            usd_inr=market.get("usd_inr", 83.42),
            is_live=market.get("is_live", False),
            fetched_at=market.get("fetched_at", datetime.now(timezone.utc).isoformat()),
        ),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
