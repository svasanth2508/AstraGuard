# AstraGuard — Pre-Deployment UI/UX Upgrade

This build focuses on presentation quality while preserving the existing FastAPI contracts, autonomous monitoring flow, risk-aware remediation, notifications, persistence, and simulator behavior.

## What changed

- Premium dark command-center shell with layered depth and restrained ambient motion.
- Sticky command navigation for Overview, Adaptive Monitoring, Incidents, Topology, and Audit.
- Stronger visual hierarchy for system state, incident KPIs, adaptive monitoring, service topology, alerts, and audit history.
- Improved responsive behavior for desktop, laptop, tablet, and mobile.
- Refined buttons, status pills, cards, error states, loading state, scrollbars, React Flow controls, and chart surfaces.
- Subtle entrance animation and reduced-motion accessibility support.
- Mobile navigation toggle and keyboard-visible focus states.
- Retry action for backend connection errors.

## Preserved behavior

No backend routes, database behavior, simulator logic, remediation logic, notification logic, or API calls were removed or replaced. The frontend continues to use the existing `services/api.ts` contract.

## Run locally

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Pre-deployment checks

1. Verify `/api/health` and `/api/snapshot` respond.
2. Test all four incident injection scenarios.
3. Complete DB overload through RCA, counterfactual, approval, remediation, verification, and notification.
4. Test low-risk automatic remediation.
5. Test force-failure rollback.
6. Refresh and confirm persistent history remains.
7. Resize through desktop/tablet/mobile widths.
8. Check browser console for errors.
9. Run `npm run build` locally after `npm install`.
