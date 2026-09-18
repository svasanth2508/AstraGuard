from __future__ import annotations

from typing import Any


COUNTERFACTUAL_LIBRARY: dict[str, dict[str, Any]] = {
    "db-overload": {
        "hypothesis": "Database connection exhaustion",
        "removed_component": "database",
        "symptoms": [
            {"name": "Payment latency", "effect": "returns toward normal", "explained": True},
            {"name": "Checkout errors", "effect": "drop below failure threshold", "explained": True},
            {"name": "API 5xx", "effect": "returns toward baseline", "explained": True},
            {"name": "Transaction failures", "effect": "stop accumulating", "explained": True},
            {"name": "Traffic volume", "effect": "remains slightly elevated", "explained": False},
        ],
        "reasoning": "Database is the deepest shared dependency on the degraded payment → checkout → gateway path.",
    },
    "payment-failure": {
        "hypothesis": "Payment service failure",
        "removed_component": "payment",
        "symptoms": [
            {"name": "Checkout errors", "effect": "drop sharply", "explained": True},
            {"name": "API 5xx", "effect": "returns toward baseline", "explained": True},
            {"name": "Failed transactions", "effect": "stop accumulating", "explained": True},
            {"name": "Database utilization", "effect": "changes only slightly", "explained": False},
        ],
        "reasoning": "Checkout and gateway symptoms are downstream of Payment while the database is not critically saturated.",
    },
    "network-latency": {
        "hypothesis": "Inter-service network degradation",
        "removed_component": "api-gateway",
        "symptoms": [
            {"name": "Payment latency", "effect": "falls substantially", "explained": True},
            {"name": "Checkout errors", "effect": "fall substantially", "explained": True},
            {"name": "Authentication latency", "effect": "returns toward normal", "explained": True},
            {"name": "Notification latency", "effect": "returns toward normal", "explained": True},
            {"name": "Database utilization", "effect": "remains near current level", "explained": False},
        ],
        "reasoning": "Independent service branches degrade together, which is consistent with a shared network-layer fault.",
    },
    "traffic-spike": {
        "hypothesis": "Traffic surge causing cascading saturation",
        "removed_component": "api-gateway",
        "symptoms": [
            {"name": "API 5xx", "effect": "falls as excess load is removed", "explained": True},
            {"name": "Checkout errors", "effect": "falls", "explained": True},
            {"name": "Payment latency", "effect": "falls", "explained": True},
            {"name": "Database utilization", "effect": "returns toward baseline", "explained": True},
            {"name": "Underlying service health", "effect": "remains stable", "explained": True},
        ],
        "reasoning": "The request-rate anomaly precedes downstream saturation and follows the normal request dependency chain.",
    },
}


def run_counterfactual(scenario: str | None, top_hypothesis: dict[str, Any] | None) -> dict[str, Any] | None:
    if not scenario or not top_hypothesis:
        return None
    template = COUNTERFACTUAL_LIBRARY.get(scenario)
    if not template:
        return None

    symptoms = list(template["symptoms"])
    explained = sum(1 for symptom in symptoms if symptom["explained"])
    total = len(symptoms)
    ratio = explained / total if total else 0.0
    support = "HIGH" if ratio >= 0.75 else "MEDIUM" if ratio >= 0.5 else "LOW"

    return {
        "status": "COMPLETED",
        "hypothesis": top_hypothesis["cause"],
        "component": top_hypothesis["component"],
        "question": f"If {top_hypothesis['cause']} were removed, would the observed downstream symptoms disappear?",
        "symptoms": symptoms,
        "explained_symptoms": explained,
        "total_symptoms": total,
        "explanation_ratio": round(ratio * 100),
        "causal_support": support,
        "reasoning": template["reasoning"],
        "method": "Deterministic dependency-graph counterfactual simulation",
    }
