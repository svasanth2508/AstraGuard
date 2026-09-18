# AstraGuard Phase 7 — Integration & Acceptance

## What Phase 7 adds

- Hardened frontend API requests with a 5-second timeout and readable backend error messages.
- Visible `API CONNECTED` + last-sync indicator in the command center.
- `/api/diagnostics` endpoint for quick integration verification.
- Deterministic backend acceptance test for both successful recovery and forced-failure rollback.
- Phase/version markers updated to Phase 7.

## Automated backend acceptance test

From `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
python acceptance_test.py
```

Expected final line:

```text
PHASE 7 ACCEPTANCE RESULT: PASS
```

## Browser integration test

1. Start backend: `uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Open `http://localhost:5173`
4. Confirm `API CONNECTED` is visible and updates every second.
5. Inject DB Overload and wait for alerts / INC-001.
6. Run Counterfactual Test.
7. Approve remediation and wait for `Recovery Verified`.
8. Reset Demo.
9. Repeat with `FORCE FAILURE: ON` and confirm rollback.

## Diagnostics

Open `http://127.0.0.1:8000/api/diagnostics`.
It should report `status: ready`, `phase: 7`, six services, and four incident scenarios.
