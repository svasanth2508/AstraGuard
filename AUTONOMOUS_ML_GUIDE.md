# AstraGuard Autonomous Learning Layer

This build replaces the fixed ML-demo layer with a streaming learning loop.

## Algorithms

- **Half-Space Trees** — online anomaly detection on telemetry.
- **Adaptive Random Forest** — online incident-pattern classification. If the installed River version does not expose ARFClassifier, AstraGuard falls back to River's Hoeffding Adaptive Tree rather than failing to start.
- **ADWIN** — concept-drift detection on telemetry that AstraGuard has already verified as healthy.
- **NetworkX + weighted RCA + counterfactual reasoning + Jaccard similarity** remain the explainable validation and safety layers.

## Important safety rule

AstraGuard does **not** train the classifier on its own predictions. While an incident is active, anomaly-model learning is paused. Only after remediation succeeds and recovery is verified does the confirmed incident label feed back into the online classifier.

## Start backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python autonomous_ml_acceptance.py
uvicorn main:app --reload
```

## Start frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## What to watch

The **Adaptive Monitoring** panel shows:

- operational pattern: NORMAL / SUSPICIOUS / ANOMALOUS
- normalized anomaly score
- predicted incident pattern and model confidence
- baseline status: STABLE / ADAPTING
- healthy observations learned
- verified incidents learned
- concept-drift count
- whether online learning is enabled or paused

## DB overload demo

1. Start healthy. Adaptive Monitoring should be NORMAL and predict HEALTHY.
2. Click **Inject DB Overload**.
3. Learning pauses while the incident is active.
4. The anomaly score rises and the classifier should move toward DB_OVERLOAD.
5. Complete RCA, remediation, and recovery verification.
6. After RECOVERY VERIFIED, `Verified Incidents Learned` increases by one.
7. Restart the backend. The model state is restored from `backend/model_store/adaptive_runtime.pkl`.

## Drift behavior

ADWIN is updated only from telemetry AstraGuard considers healthy. A short critical spike is treated as an anomaly, not immediately accepted as a new baseline. Persistent changes observed during verified healthy operation can trigger baseline status `ADAPTING`, while the online anomaly model continues learning the new healthy pattern.

## Production note

The prototype learns from simulator telemetry. In production, the same layer should be driven by a telemetry ingestion pipeline (for example OpenTelemetry/Prometheus) rather than frontend polling.
