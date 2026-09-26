<p align="center">
  <b>Self-Verifying Autonomous Enterprise Incident Resolution Engine</b>
</p>

<p align="center">
  Detect • Diagnose • Decide • Remediate • Verify • Learn
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?logo=react&logoColor=white" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/ML-River-5B5BD6" />
  <img src="https://img.shields.io/badge/Graph-NetworkX-1F6FEB" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Frontend%20Deploy-Vercel-000000?logo=vercel&logoColor=white" />
  <img src="https://img.shields.io/badge/Backend%20Deploy-Render-46E3B7" />
</p>

🚀 Overview

AstraGuard is an autonomous enterprise incident-resolution platform designed to detect abnormal system behaviour, correlate related alerts, identify probable root causes, evaluate remediation risk, recommend the minimum safe remediation, verify recovery, and learn from confirmed incidents.

AstraGuard is built around one key principle:

Automation should not stop at detection — it should verify whether the system actually recovered.

It combines adaptive anomaly detection, online learning, graph-based dependency reasoning, counterfactual validation, risk-aware remediation, human approval, rollback support, incident memory, and administrator notifications in one integrated workflow.

🎯 Problem Statement

Modern enterprise systems generate large volumes of telemetry, alerts, logs, and service-health signals. Traditional monitoring platforms often identify that something is wrong, but engineers still need to manually:

correlate alerts,

identify the root cause,

estimate business impact,

choose a safe remediation,

decide whether automation is appropriate,

verify whether the remediation succeeded,

roll back failed actions,

and learn from previous incidents.

This increases Mean Time To Resolution (MTTR) and can make incident response slower and riskier.

AstraGuard addresses this gap with a self-verifying, explainable, and risk-aware autonomous incident-resolution workflow.

✨ Core Features

🔍 Adaptive Anomaly Detection

Streaming anomaly detection using Half-Space Trees

Learns healthy operational behaviour continuously

Avoids learning active incident behaviour as a healthy baseline

Produces live anomaly scores and operational-pattern states

🧠 Online Incident Classification

Classifies abnormal patterns into known incident types

Supports continuous learning from verified incident outcomes

Designed for adaptive behaviour instead of fixed offline-only prediction

📉 Concept Drift Detection

Uses ADWIN to detect changes in normal operating behaviour

Helps the system adapt when baseline conditions shift over time

🔗 Alert Correlation

Combines related low-level alerts into a single incident

Reduces duplicate noise and improves incident clarity

🕸️ Dependency Reasoning

Uses NetworkX to model service dependencies

Tracks failure propagation across dependent services

Helps separate root causes from downstream symptoms

🎯 Root Cause Analysis

Uses structured weighted evidence scoring

Evaluates temporal, dependency and service-impact evidence

Produces a leading root-cause hypothesis with confidence

🧪 Counterfactual Validation

AstraGuard asks:

“If the suspected cause were removed, would downstream symptoms disappear?”

This provides an additional causal validation step before remediation.

💼 Business Impact Analysis

Identifies affected services

Evaluates operational blast radius

Connects technical failures with business-facing impact

🛠️ Minimum Safe Remediation

Instead of applying the largest possible action, AstraGuard selects the smallest action expected to resolve the incident safely.

⚖️ Risk-Aware Autonomy

AstraGuard separates:

Incident Severity — how serious the incident is

Action Risk — how dangerous the remediation itself is

Action Risk

Decision

Low

Automatic remediation permitted

Medium

Human approval required

High

Strict approval / restricted execution

Destructive

Blocked

📜 Remediation Contract

Each remediation can define:

recommended action,

success conditions,

observation period,

verification criteria,

rollback action.

✅ Self-Verifying Recovery

AstraGuard does not mark an incident as resolved immediately after remediation.

Remediation
    ↓
Observation
    ↓
Verification
    ↓
Success → Resolve Incident
Failure → Rollback

↩️ Automatic Rollback

If recovery verification fails, AstraGuard can trigger rollback and keep the incident open.

🧠 Incident Memory

Stores previous incidents

Uses Jaccard similarity to compare incident fingerprints

Helps identify similar historical failures and prior successful remediation

📧 Administrator Notifications

Lifecycle notifications are generated for:

Incident detected

Human approval required

Recovery verified

Recovery failed / rollback started

In-app notification history remains available even if external email delivery is unavailable.

🗃️ Audit Trail

Important decisions and actions are recorded, including:

incident detection,

alert correlation,

RCA,

remediation selection,

approval,

execution,

verification,

rollback,

notification status.

🔄 Resolution Flow

Enterprise Telemetry
        ↓
Adaptive Anomaly Detection
        ↓
Online Incident Classification
        ↓
Alert Correlation
        ↓
Dependency Analysis
        ↓
Weighted Root Cause Analysis
        ↓
Counterfactual Validation
        ↓
Business Impact Analysis
        ↓
Minimum Safe Remediation
        ↓
Action-Risk Assessment
        ↓
 ┌─────────────────────┐
 │ Low Risk            │ → Auto Execute
 │ Medium / High Risk  │ → Human Approval
 └─────────────────────┘
        ↓
Remediation Execution
        ↓
Recovery Verification
        ↓
 ┌─────────────────────┐
 │ Passed              │ → Resolve
 │ Failed              │ → Rollback
 └─────────────────────┘
        ↓
Verified Outcome
        ↓
Adaptive Learning + Incident Memory

🧪 Demo Scenarios

Scenario

Description

Database Overload

Database saturation and connection exhaustion causing cascading failures

Payment Service Failure

Payment service becomes the primary bottleneck

Network Latency Spike

Inter-service network degradation affects multiple dependency branches

Traffic Spike

Sudden request surge causes service and database saturation

🏗️ Architecture

┌─────────────────────────────┐
│      React Dashboard        │
│ TypeScript + Tailwind CSS   │
│ Recharts + React Flow       │
└──────────────┬──────────────┘
               │ REST API
               ↓
┌─────────────────────────────┐
│       FastAPI Backend       │
├─────────────────────────────┤
│ Incident Simulator          │
│ Alert Correlation           │
│ Adaptive ML Runtime         │
│ NetworkX Dependency Graph   │
│ RCA Engine                  │
│ Counterfactual Engine       │
│ Business Impact Engine      │
│ Risk Engine                 │
│ Remediation Engine          │
│ Verification Engine         │
│ Notification Service        │
└──────────────┬──────────────┘
               │
               ↓
┌─────────────────────────────┐
│ SQLite + Incident Memory    │
│ Audit History               │
│ Adaptive Model State        │
└─────────────────────────────┘

🧰 Tech Stack

Frontend

React 19

TypeScript

Vite

Tailwind CSS

@xyflow/react

Recharts

Lucide React

Backend

Python

FastAPI

Uvicorn

Pydantic

SQLAlchemy

SQLite

Intelligence / Reasoning

River

Half-Space Trees

ADWIN

Online classification

NetworkX

Weighted evidence scoring

Counterfactual reasoning

Jaccard similarity

Deployment

Frontend: Vercel

Backend: Render

🌐 Live Deployment

Frontend

https://astraguard-eight.vercel.app

Backend API

https://astraguard-q4yz.onrender.com

Health Endpoint

https://astraguard-q4yz.onrender.com/api/health

📁 Project Structure

AstraGuard/
├── backend/
│   ├── main.py
│   ├── simulator.py
│   ├── adaptive_runtime.py
│   ├── adaptive_api.py
│   ├── notification_service.py
│   ├── correlation.py
│   ├── rca_engine.py
│   ├── counterfactual.py
│   ├── impact_engine.py
│   ├── risk_engine.py
│   ├── remediation.py
│   ├── verifier.py
│   ├── incident_memory.py
│   ├── database.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.*
└── README.md

⚙️ Local Setup

1. Clone the repository

git clone https://github.com/svasanth2508/AstraGuard.git
cd AstraGuard

2. Backend

cd backend
python -m venv .venv

Windows PowerShell:

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload

Backend:

http://127.0.0.1:8000

3. Frontend

Open another terminal:

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173

🔐 Environment Variables

Frontend

VITE_API_BASE_URL=http://127.0.0.1:8000

Production example:

VITE_API_BASE_URL=https://astraguard-q4yz.onrender.com

Backend Notifications

ASTRA_EMAIL_ENABLED=true
ASTRA_ADMIN_EMAIL=admin@example.com
ASTRA_FROM_EMAIL=sender@example.com

Current email integration also expects:

RESEND_API_KEY=your_secret_api_key

Never commit API keys, passwords or production secrets to GitHub.

🔌 Important API Endpoints

Method

Endpoint

Purpose

GET

/api/health

Backend health check

GET

/api/snapshot

Complete live AstraGuard state

GET

/api/system

Current system status

GET

/api/metrics

Live telemetry

GET

/api/alerts

Active alerts

GET

/api/incidents

Current incidents

POST

/api/incidents/inject/{scenario}

Inject a controlled demo incident

POST

/api/incidents/{id}/counterfactual

Run counterfactual validation

POST

/api/incidents/{id}/approve

Approve remediation

POST

/api/incidents/{id}/reject

Reject remediation

POST

/api/incidents/{id}/verify

Verify recovery

POST

/api/incidents/{id}/rollback

Trigger rollback

GET

/api/history

Historical incidents

GET

/api/notifications

Notification history

GET

/api/notifications/status

Notification configuration

POST

/api/system/reset

Reset the demo environment

🛡️ Safety Model

AstraGuard is designed around bounded autonomy.

Incident Severity ≠ Remediation Action Risk

A critical incident can still have a low-risk remediation, while a moderate incident may require a high-risk action that should be human-approved.

This separation is central to AstraGuard's safety architecture.

🧠 Why AstraGuard Is Different

Traditional monitoring often stops at:

Detect → Alert

AstraGuard demonstrates:

Detect
→ Correlate
→ Diagnose
→ Validate
→ Evaluate Risk
→ Remediate
→ Verify
→ Roll Back if Necessary
→ Learn

Key differentiators:

Counterfactual RCA validation

Minimum Safe Remediation

Remediation Contracts

Risk-aware autonomy

Human-in-the-loop approval

Verified recovery before closure

Automatic rollback

Adaptive online learning

Historical incident memory

🎥 Recommended Demo Flow

Show healthy telemetry and adaptive monitoring.

Inject Database Overload.

Watch alerts and telemetry degrade.

Show incident correlation.

Explain root-cause analysis.

Show counterfactual validation.

Show business impact.

Show action-risk evaluation.

Approve remediation if required.

Observe recovery.

Show Recovery Verified.

Show notifications and audit history.

Reset and demonstrate a low-risk autonomous scenario.

👥 Team

Team DUO

Project: AstraGuard
Tagline: Detect. Diagnose. Decide. Recover. Verify. Learn.

🏷️ Suggested GitHub Topics

astraguard
autonomous-incident-response
anomaly-detection
root-cause-analysis
incident-management
site-reliability-engineering
sre
devops
fastapi
react
typescript
machine-learning
online-learning
river-ml
networkx
counterfactual-reasoning
self-healing-systems
remediation
observability
enterprise-monitoring
hackathon

⚠️ Current Scope

AstraGuard is currently a demonstration and research prototype.

The enterprise telemetry used in the demo is simulated. A production deployment would typically integrate with real infrastructure sources such as:

OpenTelemetry

Prometheus

application logs

distributed tracing

cloud monitoring APIs

Kubernetes

service meshes

incident-management systems.

Production remediation should additionally use strict permissions, sandboxing, staged rollouts, change controls, and organization-specific security policies.

🔒 Security Notes

Never commit .env files containing secrets.

Never commit API keys.

Store production credentials in Render/Vercel environment settings.

Restrict remediation permissions in real infrastructure.

Require approval for sensitive or destructive actions.

Keep audit logs for autonomous actions.

Rotate exposed credentials immediately.

🤝 Contributing

Contributions, suggestions and improvements are welcome.

git checkout -b feature/your-feature
git add .
git commit -m "Add your feature"
git push origin feature/your-feature

Then open a Pull Request.

📌 Repository

https://github.com/svasanth2508/AstraGuard

📄 License

No license file is currently included in the repository.

If AstraGuard will be open sourced, add an appropriate license such as MIT or Apache-2.0.

<p align="center">
  <b>AstraGuard</b><br/>
  Self-Verifying Autonomous Enterprise Incident Resolution Engine
</p>
