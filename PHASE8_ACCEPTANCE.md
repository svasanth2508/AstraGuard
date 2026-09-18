# AstraGuard Phase 8 — Persistence & Incident Memory Test

## What Phase 8 adds

- SQLite-backed incident history (`backend/astraguard.db`, created automatically at runtime)
- SQLite-backed audit trail
- Alert-signature incident fingerprints
- Jaccard similarity against previous **resolved** incidents
- Historical match card showing prior root cause, successful remediation and recovery status
- Persistent incident history on the dashboard
- `/api/history` and `/api/history/{incident_id}/audit`

## Judge-ready memory demo

1. Start backend and frontend.
2. Click **Inject DB Overload** and complete the normal remediation flow until **RECOVERY VERIFIED**.
3. Click **Reset Demo**. Historical data is intentionally retained.
4. Inject **DB Overload** again.
5. Wait for alert correlation/RCA.
6. In **Incident Memory**, verify a previous incident is shown with a high/100% similarity for the identical scenario.
7. Show the previous root cause and successful remediation recalled from SQLite.
8. Refresh the browser. The **SQLite History** list remains available.

## Automated backend test

From `backend/` run:

```powershell
python phase8_acceptance.py
```

**Warning:** this test deletes `backend/astraguard.db` first so it can run deterministically. Do not run it after collecting demo history you want to keep.

Expected final line:

```text
PHASE 8 ACCEPTANCE RESULT: PASS
```
