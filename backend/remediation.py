from __future__ import annotations

from typing import Any

from risk_engine import classify_action_policy, classify_incident_risk


REMEDIATION_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "db-overload": [
        {
            "id": "REM-DB-01",
            "action": "Restart Database",
            "risk": "HIGH",
            "cost": "MEDIUM",
            "disruption": "HIGH",
            "effectiveness": "HIGH",
            "directness": 5,
            "selection_score": 46,
            "requires_approval": True,
            "autonomy_level": 3,
        },
        {
            "id": "REM-DB-02",
            "action": "Scale Database Capacity",
            "risk": "MEDIUM",
            "cost": "HIGH",
            "disruption": "LOW",
            "effectiveness": "HIGH",
            "directness": 5,
            "selection_score": 76,
            "requires_approval": True,
            "autonomy_level": 2,
        },
        {
            "id": "REM-DB-03",
            "action": "Increase Database Connection Pool 100 → 140",
            "risk": "MEDIUM",
            "cost": "LOW",
            "disruption": "LOW",
            "effectiveness": "HIGH",
            "directness": 5,
            "selection_score": 96,
            "requires_approval": True,
            "autonomy_level": 2,
        },
        {
            "id": "REM-DB-04",
            "action": "Restart Payment Service",
            "risk": "MEDIUM",
            "cost": "LOW",
            "disruption": "MEDIUM",
            "effectiveness": "LOW",
            "directness": 2,
            "selection_score": 48,
            "requires_approval": True,
            "autonomy_level": 2,
        },
    ],
    "payment-failure": [
        {
            "id": "REM-PAY-01", "action": "Restart Payment Worker Pool", "risk": "MEDIUM", "cost": "LOW",
            "disruption": "MEDIUM", "effectiveness": "HIGH", "directness": 5, "selection_score": 88,
            "requires_approval": True, "autonomy_level": 2,
        },
        {
            "id": "REM-PAY-02", "action": "Scale Payment Service +1 Instance", "risk": "MEDIUM", "cost": "MEDIUM",
            "disruption": "LOW", "effectiveness": "MEDIUM", "directness": 4, "selection_score": 77,
            "requires_approval": True, "autonomy_level": 2,
        },
        {
            "id": "REM-PAY-03", "action": "Restart Database", "risk": "HIGH", "cost": "MEDIUM",
            "disruption": "HIGH", "effectiveness": "LOW", "directness": 1, "selection_score": 25,
            "requires_approval": True, "autonomy_level": 3,
        },
    ],
    "network-latency": [
        {
            "id": "REM-NET-01", "action": "Reroute Inter-Service Traffic to Healthy Path", "risk": "LOW", "cost": "LOW",
            "disruption": "LOW", "effectiveness": "HIGH", "directness": 5, "selection_score": 94,
            "requires_approval": False, "autonomy_level": 1,
        },
        {
            "id": "REM-NET-02", "action": "Restart API Gateway", "risk": "MEDIUM", "cost": "LOW",
            "disruption": "MEDIUM", "effectiveness": "MEDIUM", "directness": 3, "selection_score": 64,
            "requires_approval": True, "autonomy_level": 2,
        },
    ],
    "traffic-spike": [
        {
            "id": "REM-TRF-01", "action": "Enable Temporary Request Throttling", "risk": "LOW", "cost": "LOW",
            "disruption": "LOW", "effectiveness": "HIGH", "directness": 5, "selection_score": 93,
            "requires_approval": False, "autonomy_level": 1,
        },
        {
            "id": "REM-TRF-02", "action": "Scale API Gateway +2 Instances", "risk": "MEDIUM", "cost": "MEDIUM",
            "disruption": "LOW", "effectiveness": "HIGH", "directness": 5, "selection_score": 84,
            "requires_approval": True, "autonomy_level": 2,
        },
    ],
}


def _contract_for(scenario: str, action: str) -> dict[str, Any]:
    common_success = [
        {"metric": "checkout_error_rate", "operator": "<", "threshold": 5, "label": "Checkout error rate < 5%"},
        {"metric": "payment_latency_ms", "operator": "<", "threshold": 800, "label": "Payment P95 latency < 800 ms"},
        {"metric": "api_5xx_rate", "operator": "<", "threshold": 5, "label": "API 5xx rate < 5%"},
    ]
    if scenario == "db-overload":
        success = common_success + [
            {"metric": "database_cpu", "operator": "<", "threshold": 85, "label": "Database CPU < 85%"},
            {"metric": "database_connections", "operator": "<", "threshold": 75, "label": "DB connections < 75%"},
        ]
        rollback = "Restore database connection pool from 140 to 100"
    elif scenario == "network-latency":
        success = common_success + [
            {"metric": "network_latency_ms", "operator": "<", "threshold": 180, "label": "Network latency < 180 ms"},
        ]
        rollback = "Restore previous traffic route"
    elif scenario == "traffic-spike":
        success = common_success + [
            {"metric": "traffic_rps", "operator": "<", "threshold": 1800, "label": "Traffic load < 1800 RPS"},
        ]
        rollback = "Restore previous throttling/scaling configuration"
    else:
        success = common_success
        rollback = "Restore previous payment-service configuration"

    return {
        "action": action,
        "success_conditions": success,
        "failure_conditions": [
            "Checkout error rate remains > 20%",
            "Payment latency fails to improve",
            "A new critical alert appears",
        ],
        "observation_period_seconds": 15,
        "rollback_action": rollback,
        "status": "AWAITING_EXECUTION",
    }


def select_minimum_safe_remediation(
    scenario: str | None,
    root_cause: str | None,
    confidence: int | float,
) -> dict[str, Any] | None:
    if not scenario or not root_cause:
        return None
    candidates = [dict(item) for item in REMEDIATION_LIBRARY.get(scenario, [])]
    if not candidates:
        return None

    candidates.sort(key=lambda item: item["selection_score"], reverse=True)
    recommended = candidates[0]
    policy = classify_action_policy(recommended)
    recommended["requires_approval"] = policy["requires_approval"]
    recommended["autonomy_level"] = 1 if policy["auto_execute"] else (3 if policy["decision"] == "BLOCKED" else 2)
    approval_state = policy["decision"].replace("_", " ")

    result = {
        "engine": "Minimum Safe Remediation (MSR)",
        "status": "RECOMMENDED",
        "root_cause": root_cause,
        "root_cause_confidence": confidence,
        "recommended_action": recommended,
        "candidates": candidates,
        "why_selected": [
            "Directly addresses the leading root-cause hypothesis",
            "Lowest practical operational risk among effective actions",
            "Minimal service disruption",
            "Lower implementation cost than broader infrastructure changes",
            "Expected to restore the defined SLA conditions",
        ],
        "autonomy": {
            "level": recommended["autonomy_level"],
            "state": approval_state,
            "requires_approval": recommended["requires_approval"],
            "auto_execute": policy["auto_execute"],
            "action_risk": policy["action_risk"],
            "policy_reason": policy["reason"],
        },
        "contract": _contract_for(scenario, recommended["action"]),
    }
    return result
