# AstraGuard Phase 9 — Final Demo Test

## Flagship 2–3 minute judge flow

1. Start with all six services healthy.
2. Click **Inject DB Overload**.
3. Watch DB CPU/connections rise and failure propagate Database → Payment → Checkout → API Gateway.
4. Show raw alerts becoming one correlated incident.
5. Point out the three competing RCA hypotheses and evidence/counter-evidence.
6. Show **Reasoning Debate**: RCA Agent → Skeptic → Evidence Analyzer → Dependency Analyzer → Incident Memory → Decision.
7. Run **Counterfactual Test** and show HIGH causal support.
8. Show simulator-estimated business impact.
9. Explain **Minimum Safe Remediation** and the remediation contract.
10. Click **Approve**.
11. Watch metrics recover, then show **Recovery Verified**.
12. Point to the audit trail and persistent SQLite history.

## Safety/rollback demo

1. Reset Demo.
2. Inject DB Overload again.
3. Enable **Force Remediation Failure**.
4. Approve remediation.
5. Verification fails → automatic rollback → incident stays open.

## Alternate scenario sanity tests

Test each once: Payment Failure, Network Latency, Traffic Spike. Each must create an incident, produce three RCA hypotheses, generate business impact and a remediation recommendation.

## Automated check

From `backend`:

```powershell
python phase9_acceptance.py
```

Expected final line:

```text
PHASE 9 ACCEPTANCE RESULT: PASS
```
