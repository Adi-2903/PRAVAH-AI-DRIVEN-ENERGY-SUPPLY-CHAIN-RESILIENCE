# Scenario Engine Backend

This is the backend for the "Pravah: AI-Driven Energy Supply Chain Resilience" scenario engine. It is a FastAPI microservice that simulates how a supply-shock risk score for a corridor (e.g. Strait of Hormuz) propagates into Brent/WTI price movement, India's fuel prices at the pump, and GDP impact.

## Simulation Methodology

The engine runs a genuine Monte Carlo simulation. Based on the risk score (0-100), it parameterizes a geometric random walk with mean reversion (Ornstein-Uhlenbeck process). Higher risk scores increase both the expected price (drift) and the volatility of the simulation. For each day in the simulation, a random shock is drawn and added to the price, which then informs the distribution (P10, P50, P90 bands) for each day.

The elasticities and pass-through rates convert the Brent crude price movement into Indian pump prices and GDP impact percentages. 
The calibration source is historical EIA daily spot price data, specifically validated against the 2022 Ukraine invasion price spike to ensure realistic volatility parameterization.

## Running Locally

1. Create a virtual environment and install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the FastAPI application standalone:
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## Testing

Run tests with `pytest`:
```bash
pytest tests/
```
