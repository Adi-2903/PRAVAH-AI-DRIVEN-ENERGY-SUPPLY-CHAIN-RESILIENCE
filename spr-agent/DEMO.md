# SPR Optimizer Demo Guide

## 1. Running the Services
Start the backend optimizer:
```bash
cd spr-agent
uvicorn main:app --reload --port 8001
```
*(Note: Use 8001 if scenario-engine is already on 8000, or stop scenario-engine and run on 8000. For this demo, let's assume it runs on 8001).*

Start the frontend:
```bash
npm run dev
```

## 2. Example API Call
You can test the optimizer directly:

```bash
curl -X POST "http://127.0.0.1:8001/spr-schedule" \
-H "Content-Type: application/json" \
-d '{
  "planning_horizon_days": 14,
  "current_reserve_days": 9.5,
  "min_safety_floor_days": 3.0,
  "daily_risk_scores": [70, 75, 80, 85, 90, 95, 100, 95, 90, 85, 80, 75, 70, 65],
  "daily_price_forecast_usd_per_bbl": [90, 92, 95, 98, 105, 110, 115, 108, 102, 98, 95, 92, 90, 88],
  "max_daily_drawdown_days": 1.0
}'
```

## 3. Demo Scenarios (Frontend)
Once in the SPR Optimizer tab, try these scenarios:

1. **The Peak Shaver**: 
   - Set horizon to 14 days, max drawdown to 1.0. 
   - Observe how the optimization completely front-loads the release on days 5-8 when prices peak at $115 and risk hits 100, saving maximum cost while hitting the floor exactly.
2. **Constrained Floor**: 
   - Raise the safety floor to `8.0` days. 
   - Watch the chart dynamically update. The drawdown bars will shrink dramatically, and the optimizer will only release 1.5 days total, specifically targeting *only* the absolute worst day, preserving the rest to maintain the high floor.
3. **Emergency Release**:
   - Drop the safety floor to `2.0` days.
   - The system will aggressively release oil, demonstrating a much higher savings % compared to the naive flat baseline.
