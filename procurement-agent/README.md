# Procurement Agent

The Procurement Agent ranks alternative crude oil suppliers and routes for India based on cost and security sensitivity using a knowledge graph.

## Graph Structure

The knowledge graph is a directed network (`nx.DiGraph`) consisting of:
- **Suppliers**: Nodes representing oil producers (e.g., Saudi Arabia, Iraq) with `cost` and `grade` attributes.
- **Routes**: Nodes representing transit paths (e.g., Hormuz Strait, Cape of Good Hope) with a `risk` attribute.
- **Ports**: Nodes representing destination ports in India.
- **Refineries**: Nodes representing refineries (e.g., Jamnagar) where the oil is processed.
- **Grades**: Nodes representing the fuel type (e.g., light_sweet).

Edges define the flow: `Supplier -> Route -> Port -> Refinery -> Grade`. They can also contain properties like `transit_days`.

## Scoring Formula

For each valid path from a supplier to the target grade through the target refinery, we calculate a normalized composite score based on the user's weights:

`composite_score = cost_weight * normalized_cost + risk_weight * normalized_risk + transit_time_weight * normalized_transit`

Because lower cost, risk, and transit times are preferred, the scores are inverted during normalization (`1 - (val / max)`).

## Running Standalone

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

3. Run Tests:
```bash
pytest tests/
```
