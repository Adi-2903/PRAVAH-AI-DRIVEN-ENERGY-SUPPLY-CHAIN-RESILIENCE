# SPR Optimizer Agent

This microservice computes the optimal Strategic Petroleum Reserve (SPR) drawdown schedule given a risk and price forecast, using linear programming (`scipy.optimize.linprog`).

## Optimization Approach
The goal is to minimize the total effective cost of not using the SPR (which is equivalent to maximizing the value of the drawn oil). The objective function minimizes `sum(-drawdown * price * risk_weight)`, encouraging the solver to release oil on days when the price and risk are highest, without violating constraints.

Constraints:
1. Daily release cannot exceed `max_daily_drawdown_days`.
2. Cumulative reserve cannot drop below `min_safety_floor_days`.

## Running the Service
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
This runs the service on `http://localhost:8000`.

## Testing
Run tests using:
```bash
pytest tests/
```
