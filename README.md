# AstraGuard — Phase 9

**Self-Verifying Autonomous Enterprise Incident Resolution Engine**

> AstraGuard is a self-verifying autonomous incident commander that correlates fragmented enterprise alerts, challenges probable root causes through counterfactual reasoning, selects the minimum safe remediation, executes actions under bounded human-controlled autonomy, and verifies recovery before closing an incident.

## Problem

Enterprise systems generate many alerts from applications, services, infrastructure and databases. Several alerts can be symptoms of one underlying incident. Manual investigation is slow, noisy and difficult to audit.

AstraGuard demonstrates an end-to-end incident loop:

**Detect → Correlate → Investigate → Challenge Root Cause → Measure Business Impact → Select Minimum Safe Remediation → Human/Autonomous Execution → Verify Recovery → Rollback if Necessary → Audit**

## What is working

- Six-service enterprise simulator: API Gateway, Checkout, Payment, Authentication, Notification and Database
- Four controlled incident scenarios
- Live metrics and raw alerts
- React Flow dependency graph and failure propagation
- Alert correlation into one incident
- Explainable weighted RCA with three competing hypotheses
- Deterministic structured **Reasoning Debate**
- Counterfactual RCA
- Business-impact estimation
- Minimum Safe Remediation (MSR)
- Remediation Contract
- Human approval / rejection
- Simulated execution and gradual recovery
- Contract-based verified recovery
- Forced remediation failure and automatic rollback
- SQLite incident/audit persistence
- Incident fingerprinting and Jaccard historical similarity
- Persistent audit trail and incident memory
- Automated acceptance tests

## Why it is different

### 1. Counterfactual RCA
AstraGuard does not only rank a root cause. It asks: **If this suspected cause were removed, how many downstream symptoms would disappear?**

### 2. Minimum Safe Remediation
It selects the smallest effective action with the lowest practical risk and disruption instead of immediately choosing a broad restart or destructive intervention.

### 3. Remediation Contract
Before action, AstraGuard defines success thresholds, failure conditions, observation time and rollback behavior.

### 4. Verified Recovery
An incident is not closed merely because a remediation command ran. Telemetry must satisfy the contract first. Failed verification triggers rollback.

### 5. Incident Memory
Completed incidents are fingerprinted and compared using Jaccard similarity so AstraGuard can recall previous root causes and successful remediations.

### 6. Structured Reasoning Debate
A deterministic debate view exposes the decision from multiple roles: RCA Agent, Skeptic, Evidence Analyzer, Dependency Analyzer, Incident Memory and Decision. It is intentionally reproducible rather than an unconstrained multi-agent system.

## Architecture

```text
Users
  ↓
API Gateway
  ↓
Checkout Service ─────→ Authentication Service
  ↓
Payment Service ──────→ Notification Service
  ↓
Database
```

### Technology

**Frontend:** React, TypeScript, Vite, Tailwind CSS, React Flow, Recharts, Lucide React  
**Backend:** Python, FastAPI, NetworkX  
**Persistence:** SQLite  
**Realtime:** frontend polling every second  
**Core intelligence:** deterministic weighted scoring, graph reasoning, counterfactual rules, policy-based remediation and Jaccard similarity

The core demo does not require an LLM API, Kubernetes, cloud infrastructure or internet access.

## Incident scenarios

| Scenario | Expected leading root cause | Main signal |
|---|---|---|
| Database Overload | Database connection exhaustion | DB connections + CPU saturation |
| Payment Failure | Payment service failure | Extreme Payment P95 latency |
| Network Latency | Inter-service network degradation | Shared latency across branches |
| Traffic Spike | Traffic surge causing cascading saturation | Large inbound RPS surge |

The **Database Overload** scenario is the flagship judge demo.

## Flagship DB-overload demo

1. Show all six services healthy.
2. Click **Inject DB Overload**.
3. Watch Database metrics degrade and symptoms propagate to Payment → Checkout → API Gateway.
4. Show multiple alerts becoming one incident.
5. Show the three RCA hypotheses and why Database Connection Exhaustion ranks first.
6. Show the **Reasoning Debate**.
7. Run **Counterfactual Test** and show HIGH causal support.
8. Show simulator-estimated business impact.
9. Show **Minimum Safe Remediation** and the Remediation Contract.
10. Click **Approve**.
11. Watch telemetry recover.
12. Show **VERIFYING RECOVERY** and then **RECOVERY VERIFIED**.
13. Point to the audit trail and SQLite history.

A complete demonstration is designed to fit in roughly 2–3 minutes.

## Rollback demo

1. Reset Demo.
2. Inject DB Overload.
3. Enable **Force Remediation Failure**.
4. Approve the remediation.
5. Verification fails.
6. AstraGuard automatically rolls back and keeps the incident open.

## Installation

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`  
Diagnostics: `http://127.0.0.1:8000/api/diagnostics`

### Frontend

In a second PowerShell:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

After dependencies are installed once, `start-all.bat` can launch both processes.

## Important APIs

- `GET /api/snapshot`
- `GET /api/services`
- `GET /api/alerts`
- `GET /api/incidents`
- `POST /api/incidents/inject/{scenario}`
- `POST /api/incidents/{id}/counterfactual`
- `GET /api/incidents/{id}/debate`
- `GET /api/incidents/{id}/impact`
- `GET /api/incidents/{id}/remediation`
- `POST /api/incidents/{id}/approve`
- `POST /api/incidents/{id}/reject`
- `POST /api/incidents/{id}/verify`
- `POST /api/incidents/{id}/rollback`
- `POST /api/system/force-remediation-failure/{enabled}`
- `POST /api/system/reset`
- `GET /api/history`
- `GET /api/history/{id}/audit`

## Persistence

SQLite is created automatically as:

```text
backend/astraguard.db
```

**Reset Demo** clears current simulator state but intentionally keeps historical incidents so incident memory can be demonstrated.

## Automated tests

Core success + rollback test:

```powershell
cd backend
python acceptance_test.py
```

Persistence and memory test:

```powershell
python phase8_acceptance.py
```

Final Phase 9 multi-scenario hardening test:

```powershell
python phase9_acceptance.py
```

Expected final line:

```text
PHASE 9 ACCEPTANCE RESULT: PASS
```

## Explainable-AI positioning

AstraGuard uses deterministic **AI-driven decision intelligence**: evidence scoring, dependency-graph reasoning, anomaly patterns, counterfactual evaluation, historical similarity and structured autonomous decision policies. An optional LLM could later rewrite reasoning into natural language, but it is not trusted to independently execute remediation.

## Feasibility

The prototype is intentionally controlled and local. It does not require production infrastructure, AWS/Azure, Kubernetes, Kafka, Elasticsearch, a cloud database or a paid AI API. This makes it practical for a 24-hour hackathon and reliable in poor-connectivity demo environments.

## Limitations

- Metrics, users affected and revenue risk are simulator estimates, not production-company data.
- Remediation actions modify simulator state rather than real infrastructure.
- RCA rules are deterministic and cover the four included scenarios; production use would require integration with real telemetry, logs and change-management systems.
- The dependency topology is intentionally small for explainability and demo speed.

## Future work

- Connect Prometheus/OpenTelemetry telemetry
- Integrate real runbooks and safe infrastructure adapters
- Add policy/RBAC approval workflows
- Optional LLM-generated human-readable summaries only
- Expand incident fingerprints and topology discovery
- Evaluate RCA accuracy against real incident datasets

## Hackathon pitch

**AstraGuard moves AIOps from “detect and recommend” to “reason, act safely, verify and learn.”** It correlates noisy alerts into one incident, challenges the root cause counterfactually, chooses the minimum safe remediation, requires human approval where appropriate, verifies recovery against a pre-declared contract, rolls back on failure and remembers successful incidents for the future.
