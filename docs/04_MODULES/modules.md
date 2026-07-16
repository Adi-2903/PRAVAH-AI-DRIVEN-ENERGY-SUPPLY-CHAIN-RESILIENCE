# Module Deep Dives

Pravah consists of five core intelligence modules. While they operate as discrete conceptual engines, they are all physically implemented within `api.py`.

## 1. Risk Intelligence Engine (`risk-agent`)
**Purpose**: Quantify geopolitical threat levels across critical global shipping corridors.
**Core Logic**:
1.  **Ingestion**: Fetches global news events impacting maritime choke points (Hormuz, Red Sea, Cape of Good Hope, Domestic). Primarily relies on hardcoded `_RISK_FIXTURES` but supports live querying via the GDELT API (`_gdelt_events`).
2.  **Classification**: Uses regex patterns (`_RISK_RELEVANT`) to ensure the event pertains to oil, shipping, blockades, etc.
3.  **Severity Mapping**: Assigns a severity (low, medium, high, critical) based on keywords (e.g., "attack", "missile") or the GDELT Goldstein scale.
4.  **Scoring**: Applies a recency decay factor (`_recency_factor`). Older events carry less weight. The engine aggregates these weighted events and applies them as "pressure" on top of a baseline risk score for the corridor, capped at a maximum of 40 additional points.

## 2. Scenario Modeller (`scenario-engine`)
**Purpose**: Forecast the financial and macroeconomic impact of a supply chain disruption.
**Core Logic**:
1.  **Calibration**: On backend startup, `calibrate_volatility()` calculates the standard deviation of daily log returns of Brent crude over the last 2 years to establish baseline market volatility.
2.  **Simulation**: Executes a Monte Carlo simulation (`_simulate()`) using an Ornstein-Uhlenbeck geometric random walk. 
3.  **Risk Integration**: The Risk Engine's output modifies the random walk. Higher risk scores increase both the volatility (`sigma`) and the mean reversion target (`theta`), skewing the price paths aggressively upward.
4.  **Impact Translation**: Extracts P10, P50 (median), and P90 price distributions and calculates the ripple effect on domestic pump prices (applying a `pass_through_rate`) and national GDP (`gdp_sensitivity_per_10pct_oil_shock`).

## 3. Procurement Agent
**Purpose**: Dynamically reroute crude oil supply chains to avoid compromised corridors.
**Core Logic**:
1.  **Graph Construction**: Builds a `NetworkX.DiGraph` containing Suppliers (e.g., Saudi Aramco, US WTI), Routes (Hormuz, Cape, Red Sea), Ports (Vadinar, Mumbai), and Refineries (Jamnagar). Edges represent transit times and grade compatibilities.
2.  **Traversal**: When a primary route (e.g., Hormuz) is deemed too risky, the agent uses `nx.all_simple_paths` to find every possible alternative route from global suppliers to the target domestic refinery.
3.  **Optimization**: Calculates live estimated costs (Base Cost + Live Brent Premium/Discount). Evaluates all valid routes using a normalized composite score based on:
    *   Cost Weight
    *   Risk Weight (driven by the Risk Engine)
    *   Transit Time Weight

## 4. Strategic Petroleum Reserve (SPR) Optimizer
**Purpose**: Calculate the optimal release schedule of national oil reserves to combat price shocks.
**Core Logic**:
1.  **Constraints**: Operates under strict rules—it cannot draw down reserves below a `min_safety_floor_days` and cannot exceed a `max_daily_drawdown_days` limit.
2.  **Optimization Strategy**: Implements a Single-Budget Knapsack Linear Programming algorithm.
3.  **Execution**: Evaluates the forecasted daily price curve (from the Scenario Engine) and the daily risk curve. It greedily allocates the available SPR drawdown budget to the days with the highest mathematical product of `Price * Risk Weight`. This maximizes the financial relief to the domestic market.

## 5. The Coordinator
**Purpose**: Orchestrate the independent modules into a cohesive policy recommendation.
**Core Logic**:
The Coordinator runs the pipeline in a strict dependency sequence:
`Risk -> Scenario -> Procurement -> SPR`
It evaluates the Procurement Agent's best alternative against the baseline scenario (doing nothing). It generates a `Resolution` containing a deterministic reasoning trail (e.g., *Why did we accept a higher barrel cost? Because the corridor risk reduction offset the financial penalty.*)
