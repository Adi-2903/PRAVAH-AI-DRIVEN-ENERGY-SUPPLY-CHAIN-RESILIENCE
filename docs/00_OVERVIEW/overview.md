# Pravah Project Overview

## Purpose & Business Objective
Pravah is an AI-Driven Energy Supply Chain Resilience platform. The primary business objective is to maintain national energy security (specifically for India, judging by the default `domestic` parameters, `INR` currency, and Indian refineries like Jamnagar and Vadinar). 

The platform continuously monitors geopolitical risk, forecasts crude oil prices under shock scenarios, recommends alternative procurement routes if primary shipping corridors (like the Strait of Hormuz or Red Sea) are compromised, and optimizes the drawdown of the Strategic Petroleum Reserve (SPR) to minimize economic impact.

## Target Users
*   **Command Center Operators**: Need a high-level, unified view of all active risks and actionable, consolidated recommendations.
*   **Policy Makers**: Need to understand the macroeconomic impact of oil shocks (GDP impact, pump price impact) to make informed policy decisions.
*   **Procurement Officers**: Need specific alternative crude grades, ports, and transit routes when a primary supplier is compromised.
*   **Citizens (Citizen View)**: Need transparent, simplified data regarding energy security and localized pump price impacts.

## Core Capabilities
1.  **Risk Intelligence**: Real-time tracking of geopolitical events (via GDELT or deterministic fixtures) to assign a 0-100 risk score to critical maritime choke points.
2.  **Scenario Modelling**: Monte Carlo simulations to forecast Brent crude trajectories over a given disruption duration, translating barrel prices into localized pump prices and GDP impact percentages.
3.  **Dynamic Procurement**: Network graph traversal of global crude suppliers, routes, and domestic refineries to find the optimal replacement barrel based on weighted cost, risk, and transit time preferences.
4.  **Strategic Reserves Optimization**: Algorithmic scheduling of SPR drawdowns to offset price spikes while adhering to strict safety-floor constraints.

## Interconnected System
Unlike siloed dashboards, Pravah is highly interconnected. An event in the **Risk Engine** directly drives the volatility in the **Scenario Engine**, which in turn defines the price parameters for the **SPR Optimizer**, while the risk score simultaneously reroutes the **Procurement Agent's** supply chain graph. The **Coordinator** is responsible for orchestrating this chain reaction into a single, cohesive policy recommendation.

---
*Related Documents:*
*   [Architecture](../01_ARCHITECTURE/architecture.md)
*   [Data Flow](../05_DATA_FLOW/data_flow.md)
