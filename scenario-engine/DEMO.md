# Scenario Engine Demo Guide

This document explains how to run the Scenario Engine microservice and frontend panel, along with scenarios to showcase its capabilities.

## 1. Running the System

### Backend (FastAPI)
The backend requires Python 3.11+.
```bash
cd scenario-engine
pip install -r requirements.txt
uvicorn main:app --reload
```
The API will run at `http://127.0.0.1:8000`.

### Frontend (Next.js)
In a separate terminal, start the Next.js app.
```bash
cd ..
npm install
npm run dev
```
Navigate to `http://localhost:3000/scenario` to view the standalone control room panel.

## 2. Example cURL Request

If you want to ping the API directly, run:

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/simulate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "risk_score": 78,
  "corridor": "hormuz",
  "shock_duration_days": 14,
  "num_simulations": 5000,
  "elasticity_assumptions": {
    "price_elasticity_of_demand": -0.05,
    "pass_through_rate_to_pump": 0.7,
    "gdp_sensitivity_per_10pct_oil_shock": -0.15
  },
  "current_brent_usd": 82.0
}'
```

You can also test the mock safety endpoint:
```bash
curl http://127.0.0.1:8000/simulate/mock
```

## 3. Live Demo Scenarios

Here are 3 scenarios worth showing live on the frontend panel:

### Scenario A: The Baseline (Low Risk)
- **Risk Score:** `20`
- **Shock Duration:** `30 days`
- **Narrative:** With a low risk score, the fan chart remains extremely tight around the current spot price. The price of Brent oil barely drifts, and the India Pump Price and GDP impacts are negligible.
- **Visual:** The blue/red fan band is very narrow. 

### Scenario B: The Short-Term Shock
- **Risk Score:** `85`
- **Shock Duration:** `14 days`
- **Narrative:** Watch the fan chart widen dramatically as you push the risk score up. High risk introduces massive volatility (uncertainty). The P90 (worst-case) trajectory will skyrocket quickly. 
- **Visual:** Notice how the worst-case pump price jumps above ₹110/L and the GDP impact shifts leftward into deeper negative territory.

### Scenario C: The Long-Term Grind
- **Risk Score:** `60`
- **Shock Duration:** `90 days`
- **Narrative:** Increase the duration to 90 days. You will see the cone of uncertainty expand significantly over time. While the daily volatility might not be extreme on day 1, the compounded uncertainty by day 90 results in a very wide distribution in the histogram below the chart.
- **Visual:** The histogram distribution flattens and widens, truly demonstrating the Monte Carlo simulation engine at work.
