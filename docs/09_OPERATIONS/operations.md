# Operations & Debugging Guide

## Debugging the Monolith (`api.py`)

### 1. External API Failures
Pravah relies on three external APIs:
*   **EIA** (Brent crude history)
*   **GDELT** (Live geopolitical news)
*   **Exchangerate.host** (USD/INR conversion)

**Symptom**: The frontend `data-status` indicator shows "Fallback Cache" instead of "Live".
**Cause**: The EIA API key is invalid, rate-limited, or the service is down.
**Resolution**: Check the Vercel logs. The backend is designed to gracefully fallback to `_BRENT_CSV` without throwing a 500 error. No immediate action is required for the system to function, but verifying `EIA_API_KEY` in the environment variables is the first step.

### 2. Frontend "Mock Data" Indicator
**Symptom**: The UI explicitly states it is using Mock Data.
**Cause**: The frontend failed to reach the FastAPI backend (e.g., CORS error, 502 Bad Gateway) OR the `.env` variable `NEXT_PUBLIC_USE_MOCK` is set to `true`.
**Resolution**: 
*   Verify the `NEXT_PUBLIC_*` URLs in `.env`.
*   Check the browser console for CORS errors. If CORS is failing, ensure the `ALLOWED_ORIGINS` environment variable in the backend includes the frontend domain.

## Common Operations Workflows

### Adding a New Supply Route
1.  Open `api.py`.
2.  Locate `build_procurement_graph()`.
3.  Add the new node (e.g., `G.add_node("new_route", type="route", risk=50)`).
4.  Add the edges connecting the supplier to the route, and the route to the port.
5.  Deploy. The frontend will dynamically pick up the new network graph via `GET /graph`.

### Modifying the SPR Safety Floor
1.  Open `api.py`.
2.  Locate `_coordinate()`.
3.  Modify the `min_safety_floor_days` argument passed into `SPRScheduleRequest`. Currently, it is hardcoded to `6.0` days.

## Logging
The backend uses standard Python `logging`. 
*   The log level is controlled via the `LOG_LEVEL` environment variable.
*   Every request is intercepted by the `_log_requests` middleware, logging the method, path, status code, and latency in milliseconds. Check Vercel function logs for this output.
