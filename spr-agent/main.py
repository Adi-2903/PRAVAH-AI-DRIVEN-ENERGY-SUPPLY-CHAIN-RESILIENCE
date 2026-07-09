from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import numpy as np
from scipy.optimize import linprog

from models import SPRScheduleRequest, SPRScheduleResponse, DailySchedule

app = FastAPI(title="SPR Optimizer Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_risk_weight(score: float) -> float:
    # Scale risk score to a weight. Higher risk -> higher weight.
    # Base weight 1.0, scales up to 2.0 at risk 100.
    return 1.0 + (score / 100.0)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/spr-schedule", response_model=SPRScheduleResponse)
def compute_schedule(req: SPRScheduleRequest):
    N = req.planning_horizon_days
    if len(req.daily_risk_scores) != N or len(req.daily_price_forecast_usd_per_bbl) != N:
        raise HTTPException(status_code=422, detail="Array lengths must match planning_horizon_days")

    if req.current_reserve_days < req.min_safety_floor_days:
        raise HTTPException(status_code=400, detail="Current reserve already below safety floor")

    # 1. Objective function: Minimize total effective cost of NOT using SPR.
    # Equivalent to maximizing the value of the SPR drawdown.
    # Maximize sum(x_i * P_i * W_i) => Minimize sum(-x_i * P_i * W_i)
    c = np.zeros(N)
    for i in range(N):
        w = get_risk_weight(req.daily_risk_scores[i])
        # Negative because linprog minimizes
        c[i] = -1.0 * req.daily_price_forecast_usd_per_bbl[i] * w

    # 2. Constraints
    # A_ub * x <= b_ub
    # Constraint 1: Cumulative drawdown <= (current - floor)
    # x_0 <= max_total
    # x_0 + x_1 <= max_total
    # ...
    # sum(x_0..x_N-1) <= max_total
    max_total_draw = req.current_reserve_days - req.min_safety_floor_days
    
    A_ub = np.tril(np.ones((N, N)))
    b_ub = np.full(N, max_total_draw)

    # Bounds: 0 <= x_i <= max_daily_drawdown_days
    bounds = [(0, req.max_daily_drawdown_days) for _ in range(N)]

    # 3. Solve Linear Program
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    if not res.success:
        # If optimization fails, fallback to zero drawdown
        opt_drawdowns = np.zeros(N)
    else:
        opt_drawdowns = res.x

    # 4. Compute naive baseline (flat distribution of total allowed drawdown)
    flat_daily = min(max_total_draw / N, req.max_daily_drawdown_days)
    naive_drawdowns = np.full(N, flat_daily)

    # 5. Calculate Costs and Savings
    # We define cost as the unmitigated cost minus the value of the drawdown.
    # For a fair monetary comparison, we just compare the raw financial value of the drawn oil.
    # Value = sum(drawdown * price)
    opt_value_usd = np.sum(opt_drawdowns * req.daily_price_forecast_usd_per_bbl) * 1_000_000 # Assuming units are M bbl for scale, or just scale arbitrarily for demo
    naive_value_usd = np.sum(naive_drawdowns * req.daily_price_forecast_usd_per_bbl) * 1_000_000

    # Let's say baseline "cost" is some arbitrary large number minus naive value,
    # or just frame it in terms of "savings" directly.
    # The prompt asks for baseline_cost, optimized_cost, savings.
    # Cost = (Total Demand * Average Price) - Value of Drawdown.
    # Let Demand = max_daily_drawdown * N
    total_demand = req.max_daily_drawdown_days * N
    avg_price = np.mean(req.daily_price_forecast_usd_per_bbl)
    unmitigated_cost = total_demand * avg_price * 1_000_000

    baseline_cost = unmitigated_cost - naive_value_usd
    optimized_cost = unmitigated_cost - opt_value_usd
    savings = baseline_cost - optimized_cost
    savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

    # 6. Format Response
    schedule = []
    current_res = req.current_reserve_days
    
    for i in range(N):
        d = float(opt_drawdowns[i])
        current_res -= d
        
        if d > req.max_daily_drawdown_days * 0.9:
            rat = "Maximum capacity release to offset peak risk/price."
        elif d > 0:
            rat = "Partial release balancing safety floor constraints."
        else:
            rat = "Reserve preserved for higher risk days."
            
        schedule.append(DailySchedule(
            day=i+1,
            drawdown_days=round(d, 3),
            reserve_after_days=round(current_res, 3),
            risk_score=req.daily_risk_scores[i],
            price_usd=req.daily_price_forecast_usd_per_bbl[i],
            rationale=rat
        ))

    return SPRScheduleResponse(
        schedule=schedule,
        total_drawdown_days=round(float(np.sum(opt_drawdowns)), 3),
        baseline_cost_usd=round(baseline_cost, 2),
        optimized_cost_usd=round(optimized_cost, 2),
        savings_usd=round(savings, 2),
        savings_pct=round(savings_pct, 2),
        reserve_never_below_floor=bool(current_res >= req.min_safety_floor_days - 1e-5),
        computed_at=datetime.utcnow().isoformat() + "Z"
    )

@app.get("/spr-schedule/mock", response_model=SPRScheduleResponse)
def mock_schedule():
    # Pre-canned response for safety fallback
    return SPRScheduleResponse(
        schedule=[
            DailySchedule(day=1, drawdown_days=1.0, reserve_after_days=8.5, risk_score=85, price_usd=102.5, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=2, drawdown_days=1.0, reserve_after_days=7.5, risk_score=88, price_usd=104.0, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=3, drawdown_days=1.0, reserve_after_days=6.5, risk_score=82, price_usd=101.0, rationale="Maximum capacity release to offset peak risk/price."),
            DailySchedule(day=4, drawdown_days=0.5, reserve_after_days=6.0, risk_score=70, price_usd=95.0, rationale="Partial release balancing safety floor constraints."),
            DailySchedule(day=5, drawdown_days=0.0, reserve_after_days=6.0, risk_score=60, price_usd=90.0, rationale="Reserve preserved for higher risk days."),
            DailySchedule(day=6, drawdown_days=0.0, reserve_after_days=6.0, risk_score=55, price_usd=88.0, rationale="Reserve preserved for higher risk days."),
            DailySchedule(day=7, drawdown_days=0.0, reserve_after_days=6.0, risk_score=50, price_usd=85.0, rationale="Reserve preserved for higher risk days.")
        ],
        total_drawdown_days=3.5,
        baseline_cost_usd=50000000.0,
        optimized_cost_usd=42000000.0,
        savings_usd=8000000.0,
        savings_pct=16.0,
        reserve_never_below_floor=True,
        computed_at=datetime.utcnow().isoformat() + "Z"
    )
