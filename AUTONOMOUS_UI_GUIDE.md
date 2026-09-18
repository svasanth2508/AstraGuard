# AstraGuard Autonomous UI Upgrade

This build keeps the autonomous-learning backend unchanged and focuses on the judge-facing command center.

## What changed

- Adaptive Monitoring is presented as operational intelligence rather than an "AI/ML" demo panel.
- Added a live anomaly score bar.
- Added Operational Pattern, Learning State, Healthy Samples, Verified Incidents Learned, and Baseline Drift.
- Added a seven-stage Autonomous Resolution Loop: Observe → Detect → Correlate → Diagnose → Decide → Verify → Learn.
- The UI explicitly shows when learning is paused during an active incident, preventing failure telemetry from becoming the healthy baseline.
- Visual polish: grid background, stronger command-center cards, clearer state hierarchy.

## Run

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Main demo

1. Show `NORMAL`, baseline stable, learning active.
2. Inject DB Overload.
3. Watch anomaly score rise and learning move to `PAUSED`.
4. Show alert correlation and RCA.
5. Run counterfactual validation.
6. Approve remediation.
7. Show verification.
8. After recovery, show the loop reaching `Learn` and the verified incident-learning count increasing.
