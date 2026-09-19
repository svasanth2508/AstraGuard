from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from simulator import SCENARIOS, simulator
from database import list_audit_events, list_incidents
from adaptive_api import router as adaptive_router
from adaptive_runtime import runtime
from notification_service import notifier


app = FastAPI(
    title="AstraGuard API",
    description=(
        "Backend API for the AstraGuard autonomous "
        "incident resolution simulator."
    ),
    version="1.0.0-autonomous-ml",
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(adaptive_router)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Main production Vercel domain
        "https://astraguard-eight.vercel.app",
    ],

    # Allow AstraGuard preview / branch Vercel deployments
    allow_origin_regex=r"https://astraguard(?:-[a-zA-Z0-9-]+)*\.vercel\.app",

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root() -> dict:
    return {
        "name": "AstraGuard API",
        "status": "online",
        "phase": "autonomous-ml",
        "production_frontend": (
            "https://astraguard-eight.vercel.app"
        ),
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "astraguard-backend",
        "phase": "autonomous-ml",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# DIAGNOSTICS
# =========================================================

@app.get("/api/diagnostics")
def diagnostics() -> dict:
    snapshot = simulator.snapshot()

    runtime_status = runtime.status()

    return {
        "status": "ready",

        "phase": "autonomous-ml",

        "frontend_expected_origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://astraguard-eight.vercel.app",
        ],

        "backend": "FastAPI",

        "polling_interval_seconds": 1,

        "services":
            snapshot["system"]["services_total"],

        "scenario_count":
            len(SCENARIOS),

        "core_flow_ready":
            True,

        "persistence":
            "SQLite",

        "incident_memory":
            "Jaccard similarity",

        "reasoning_debate":
            "Deterministic structured evidence debate",

        "adaptive_learning":
            runtime_status,

        "streaming_ml": {
            "anomaly_detector":
                "Half-Space Trees",

            "incident_classifier":
                runtime_status["model"][
                    "incident_classifier"
                ],

            "drift_detector":
                "ADWIN",

            "verified_feedback_learning":
                True,

            "model_persistence":
                True,
        },

        "demo_hardening":
            True,

        "risk_aware_autonomy": {
            "low_risk":
                "AUTO_EXECUTION_PERMITTED",

            "medium_high_risk":
                "HUMAN_APPROVAL_REQUIRED",

            "destructive":
                "BLOCKED",
        },

        "admin_notifications":
            notifier.config(),

        "persistent_incidents":
            len(
                list_incidents(
                    limit=100
                )
            ),

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# =========================================================
# SNAPSHOT
# =========================================================

@app.get("/api/snapshot")
def get_snapshot() -> dict:
    return simulator.snapshot()


# =========================================================
# SYSTEM
# =========================================================

@app.get("/api/system")
def system_status() -> dict:
    return simulator.snapshot()["system"]


# =========================================================
# SERVICES
# =========================================================

@app.get("/api/services")
def services() -> list[dict]:
    return simulator.snapshot()["services"]


# =========================================================
# METRICS
# =========================================================

@app.get("/api/metrics")
def metrics() -> dict:
    return simulator.snapshot()["metrics"]


# =========================================================
# ALERTS
# =========================================================

@app.get("/api/alerts")
def alerts() -> list[dict]:
    return simulator.snapshot()["alerts"]


# =========================================================
# INCIDENT LIST
# =========================================================

@app.get("/api/incidents")
def incidents() -> list[dict]:
    incident = simulator.snapshot().get(
        "incident"
    )

    return (
        [incident]
        if incident
        else []
    )


# =========================================================
# INCIDENT DETAIL
# =========================================================

@app.get("/api/incidents/{incident_id}")
def incident_detail(
    incident_id: str,
) -> dict:

    incident = simulator.snapshot().get(
        "incident"
    )

    if (
        not incident
        or incident["id"] != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident


# =========================================================
# RCA
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/analyze"
)
def analyze_incident(
    incident_id: str,
) -> dict:

    incident = simulator.snapshot().get(
        "incident"
    )

    if (
        not incident
        or incident["id"] != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident["rca"]


# =========================================================
# COUNTERFACTUAL ANALYSIS
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/counterfactual"
)
def counterfactual_test(
    incident_id: str,
) -> dict:

    try:
        snapshot = (
            simulator.run_counterfactual_test(
                incident_id
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    incident = snapshot.get(
        "incident"
    )

    if (
        not incident
        or not incident.get(
            "counterfactual"
        )
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Counterfactual analysis "
                "is not ready"
            ),
        )

    return incident["counterfactual"]


# =========================================================
# REASONING DEBATE
# =========================================================

@app.get(
    "/api/incidents/{incident_id}/debate"
)
def incident_debate(
    incident_id: str,
) -> dict:

    incident = simulator.snapshot().get(
        "incident"
    )

    if (
        not incident
        or incident["id"] != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    debate = incident.get(
        "reasoning_debate"
    )

    if not debate:
        raise HTTPException(
            status_code=409,
            detail=(
                "Reasoning debate "
                "is not ready"
            ),
        )

    return debate


# =========================================================
# BUSINESS IMPACT
# =========================================================

@app.get(
    "/api/incidents/{incident_id}/impact"
)
def incident_impact(
    incident_id: str,
) -> dict:

    incident = simulator.snapshot().get(
        "incident"
    )

    if (
        not incident
        or incident["id"] != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    impact = incident.get(
        "business_impact"
    )

    if not impact:
        raise HTTPException(
            status_code=409,
            detail=(
                "Business impact "
                "is not ready"
            ),
        )

    return impact


# =========================================================
# REMEDIATION
# =========================================================

@app.get(
    "/api/incidents/{incident_id}/remediation"
)
def incident_remediation(
    incident_id: str,
) -> dict:

    incident = simulator.snapshot().get(
        "incident"
    )

    if (
        not incident
        or incident["id"] != incident_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    remediation = incident.get(
        "remediation"
    )

    if not remediation:
        raise HTTPException(
            status_code=409,
            detail=(
                "Remediation recommendation "
                "is not ready"
            ),
        )

    return remediation


# =========================================================
# APPROVE REMEDIATION
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/approve"
)
def approve_remediation(
    incident_id: str,
) -> dict:

    try:
        return (
            simulator.approve_remediation(
                incident_id
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# =========================================================
# REJECT REMEDIATION
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/reject"
)
def reject_remediation(
    incident_id: str,
) -> dict:

    try:
        return (
            simulator.reject_remediation(
                incident_id
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# =========================================================
# VERIFY RECOVERY
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/verify"
)
def verify_recovery(
    incident_id: str,
) -> dict:

    try:
        return simulator.verify_now(
            incident_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# =========================================================
# ROLLBACK
# =========================================================

@app.post(
    "/api/incidents/{incident_id}/rollback"
)
def rollback_incident(
    incident_id: str,
) -> dict:

    try:
        return simulator.rollback(
            incident_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# =========================================================
# FORCE REMEDIATION FAILURE
# =========================================================

@app.post(
    "/api/system/force-remediation-failure/{enabled}"
)
def force_remediation_failure(
    enabled: bool,
) -> dict:

    return (
        simulator.set_force_failure(
            enabled
        )
    )


# =========================================================
# SCENARIOS
# =========================================================

@app.get("/api/scenarios")
def scenarios() -> list[dict]:

    return [
        {
            "id":
                key,

            "label":
                value["label"],

            "summary":
                value.get(
                    "summary"
                ),

            "expected_root_cause":
                value.get(
                    "expected_root_cause"
                ),
        }

        for key, value
        in SCENARIOS.items()
    ]


# =========================================================
# INCIDENT INJECTION
# =========================================================

@app.post(
    "/api/incidents/inject/{scenario}"
)
def inject_incident(
    scenario: str,
) -> dict:

    try:
        return simulator.inject(
            scenario
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# INCIDENT HISTORY
# =========================================================

@app.get("/api/history")
def incident_history() -> list[dict]:

    return list_incidents(
        limit=50
    )


# =========================================================
# AUDIT HISTORY
# =========================================================

@app.get(
    "/api/history/{incident_id}/audit"
)
def historical_audit(
    incident_id: str,
) -> list[dict]:

    return list_audit_events(
        incident_id=incident_id,
        limit=250,
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.get("/api/notifications")
def notifications() -> dict:

    return {
        "config":
            notifier.config(),

        "events":
            notifier.history(
                limit=50
            ),
    }


# =========================================================
# NOTIFICATION STATUS
# =========================================================

@app.get(
    "/api/notifications/status"
)
def notification_status() -> dict:

    return notifier.config()


# =========================================================
# RESET
# =========================================================

@app.post("/api/system/reset")
def reset_system() -> dict:

    return simulator.reset_demo()
