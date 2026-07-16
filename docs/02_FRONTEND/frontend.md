# Frontend Architecture & Implementation

## Overview
The Pravah frontend is built with **Next.js (App Router)**. It is a highly interactive, client-heavy application designed to consume the centralized backend API and visualize complex data through charts and network graphs.

## Core Files & Directories
*   `frontend/app/`: The root directory for the Next.js App Router.
*   `frontend/app/globals.css`: Contains the Tailwind CSS configuration, custom design tokens, and base styling rules.
*   `frontend/app/layout.tsx`: The root layout wrapping all pages.
*   `frontend/app/lib/`: Contains critical data-fetching and utility modules.
*   `frontend/app/components/`: Reusable React components (e.g., `data-freshness.tsx`, `reasoning-trail.tsx`).

## Page Hierarchy & Routing
The application utilizes Next.js file-based routing. The following primary pages exist:

1.  **`page.tsx` (Root/Login)**: The entry point of the application.
2.  **`dashboard.tsx`**: The main command center view. Aggregates data from multiple endpoints to present a unified view of system health and active risks.
3.  **`risk-intelligence.tsx`**: Specialized view for the Risk Engine. Displays global corridor risks, recent GDELT/fixture events, and signal weightings.
4.  **`simulator.tsx`**: Specialized view for the Scenario Engine. Allows users to tweak parameters (like shock duration) and view Monte Carlo price projections.
5.  **`procurement.tsx`**: Displays the crude oil supply chain. Uses the NetworkX outputs from the backend to visualize alternative routes and calculate replacement barrel costs.
6.  **`spr.tsx`**: Dedicated to the Strategic Petroleum Reserve. Visualizes the daily drawdown schedule and calculates total cost savings against a naive baseline.
7.  **`citizen-view.tsx` & `policy-maker.tsx`**: Persona-specific views that tailor the data presentation (e.g., focusing on pump price impact in INR for citizens).

## Data Fetching & State Management
Pravah does not use heavy state management libraries like Redux. Instead, it relies on React Context/Hooks and direct API polling.

### The `lib/api.ts` Configuration
This file acts as the central registry for all backend endpoints. It reads from environment variables (`NEXT_PUBLIC_*_URL`) to determine the base URL for each logical service. In the current monolithic deployment, all these variables point to the same host.

### The `useLiveData` Hook (`lib/use-live-data.ts`)
This custom React hook is the core of the frontend's data pipeline. 
*   **Polling**: It handles polling the backend at set intervals to ensure the dashboard remains "live".
*   **State Machine**: It manages the transition between `loading`, `error`, and `success` states.
*   **Fallback Logic**: If the backend is unreachable or returns an error, the hook seamlessly falls back to using mock data (from `lib/mock-data.ts`) or previously cached successful responses to prevent UI breakage.

## Styling & Theming
*   **Tailwind CSS**: Utility classes are used extensively for rapid UI development.
*   **Dark Mode**: The design system is aggressively themed for dark mode, using deep slate backgrounds and vibrant accents (blue, amber, red) to indicate varying levels of risk and system status.
*   **Recharts**: Used for rendering complex data visualizations (e.g., the Monte Carlo price paths in the Simulator).

## Developer Workflows
*   **Adding a new API call**: Define the route in `lib/api.ts`, create the TypeScript interface matching the backend's Pydantic model, and use `useLiveData` in the target component to fetch the data.
*   **Handling Vercel Deployments**: The frontend includes configuration (`eslint.config.mjs`) to suppress certain strict React hooks warnings (e.g., exhaustive-deps) to ensure the Vercel build succeeds even if prototype code is committed.

---
*Related Documents:*
*   [Component Reference](../07_COMPONENTS/component_reference.md) (If implemented)
*   [API Contracts](../07_CONTRACTS/contracts.md)
