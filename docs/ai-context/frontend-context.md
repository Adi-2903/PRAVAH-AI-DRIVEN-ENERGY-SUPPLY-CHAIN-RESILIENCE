# Frontend Context

**Framework**: Next.js (App Router)
**Styling**: Tailwind CSS (`globals.css`)
**Component Library**: Custom/Radix UI/Lucide React

## Structure
*   The frontend uses the Next.js `app/` directory structure.
*   **Pages**:
    *   `dashboard.tsx`: Main overview, fetching live data layer.
    *   `risk-intelligence.tsx`: Displays corridor risks, events, and signal weightings. Hits `/corridors`.
    *   `simulator.tsx`: Interfaces with the Scenario Engine, passing risk/corridor parameters to `POST /simulate`.
    *   `procurement.tsx`: Displays network supply chain graphs. Hits `POST /recommend`.
    *   `spr.tsx`: Displays daily SPR scheduling and cost savings. Hits `POST /spr-schedule`.
    *   `citizen-view.tsx` & `digital-twin.tsx` & `policy-maker.tsx`: Various dashboard views for specific user personas.
*   **State & Fetching**: 
    *   Managed largely by `lib/live-data.ts` and `lib/use-live-data.ts`.
    *   Data is fetched directly from the backend API, defined in `lib/api.ts` (using `NEXT_PUBLIC_*_URL` env vars).
*   **Mock Fallbacks**: `lib/mock-data.ts` is used heavily when the backend is unavailable or when the `NEXT_PUBLIC_USE_MOCK` flag is active.

## Design
*   **Theme**: Dark mode prioritized. Uses deep backgrounds and vibrant gradients for charts and cards.
*   **Data Visualization**: Uses `recharts` for charting.
*   **Components**: Heavy use of modular components like `<Card>`, `<Badge>`, `<Progress>`, imported directly within files or from generic libraries.

## Important Constraints
*   **Client Components**: Many pages use `"use client"` because they rely on React hooks (`useState`, `useEffect`) and browser APIs (e.g., PDF generation).
*   **Vercel Build**: Suppress ESLint warnings if necessary to pass Vercel builds (e.g. `react-hooks/exhaustive-deps`).
