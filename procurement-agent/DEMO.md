# Procurement Agent Demo

## How to run

1. Backend:
```bash
cd procurement-agent
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

2. Frontend:
```bash
cd procurement-agent-frontend
npm install
npm run dev
```

## Example `curl` request

```bash
curl -X POST "http://localhost:8000/recommend" \
     -H "Content-Type: application/json" \
     -d '{
       "current_supplier": "saudi_arabia",
       "current_corridor_risk_score": 78,
       "target_refinery": "jamnagar",
       "required_crude_grade": "medium_sour",
       "cost_weight": 0.5,
       "risk_weight": 0.3,
       "transit_time_weight": 0.2,
       "max_alternatives": 5
     }'
```

## Scenarios worth showing live

1. **Balanced Profile (Base Case)**
   - Cost: 0.5, Risk: 0.3, Transit: 0.2
   - Shows a blend where cost-efficient but slightly risky routes are balanced against highly secure ones.

2. **Maximum Risk Aversion**
   - Cost: 0.0, Risk: 1.0, Transit: 0.0
   - Pushing the risk weight to max will highlight safe routes like `cape_of_good_hope` even if they are much slower or more expensive. The graph will animate the highlight shifting away from `hormuz_strait`.

3. **Maximum Cost Efficiency**
   - Cost: 1.0, Risk: 0.0, Transit: 0.0
   - The cheapest suppliers (e.g. Russia) and fastest/cheapest routes will rise to Rank 1 regardless of geopolitical risk.
