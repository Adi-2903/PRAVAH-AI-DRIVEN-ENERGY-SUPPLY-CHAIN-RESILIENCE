# Pravah Deployment Guide

This guide provides the exact steps required to deploy the Pravah v1.0.0 Monolith to production. 

## 1. GitHub Repository Setup
1. Push the `main` branch to your GitHub repository.
2. Ensure the repository contains the `frontend/` folder with `api/index.py` and `vercel.json` properly configured.

## 2. Vercel Import
1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New** → **Project**.
3. Import your GitHub repository.

## 3. Build Settings
During the import configuration, set the following:
- **Project Name:** `pravah` (or your preferred name)
- **Framework Preset:** Next.js
- **Root Directory:** `frontend` (⚠️ **CRITICAL:** Vercel must build from the `frontend/` directory to capture both the Next.js app and the Python serverless function).
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm install`

## 4. Environment Variables
In the Vercel project settings, configure the following optional variables:
- `GEMINI_API_KEY`: (Optional) Required for live AI Risk assessments. If omitted, the system falls back to heuristics.
- `EIA_API_KEY`: (Optional) Required for live oil spot prices. If omitted, the system falls back to embedded historical CSVs.
- `MAPBOX_ACCESS_TOKEN`: (Required for Maps) Mapbox token to render the UI map layer.

*Note: No URL routing variables (e.g. `NEXT_PUBLIC_API_URL`) are required, as Vercel automatically routes `/api/*` to the local Python function.*

## 5. Custom Domain (Optional) & HTTPS
1. In your Vercel Project, go to **Settings** → **Domains**.
2. Add your custom domain (e.g., `pravah.yourcompany.com`).
3. Follow the DNS instructions provided by Vercel to configure your CNAME or A records.
4. **HTTPS:** Vercel automatically provisions and renews SSL/TLS certificates for all domains. No manual HTTPS configuration is necessary.

## 6. Production Verification
After deployment completes, visit your production URL and perform the following smoke tests:
1. **Health Check:** Visit `https://your-domain.com/api/health` and expect `{"status": "ok"}`.
2. **Dashboard Load:** Visit the homepage to verify UI renders without blank screens.
3. **API Routing:** Open the **Risk Intelligence** tab and verify the "Live Backend" badge illuminates, confirming the Next.js frontend is successfully communicating with the Python serverless backend.

## 7. Rollback Strategy
Vercel keeps a fully functional, immutable snapshot of every single deployment.
- If a bad deployment reaches production, go to the Vercel **Deployments** tab.
- Find the previous successful deployment.
- Click the three dots (options) and select **Promote to Production** (or **Assign Custom Domains**).
- The rollback takes effect instantaneously, completely bypassing the build process.
