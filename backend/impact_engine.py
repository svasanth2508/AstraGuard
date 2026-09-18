from __future__ import annotations

from typing import Any


SERVICE_IMPORTANCE = {
    "api-gateway": 3,
    "checkout": 5,
    "payment": 5,
    "auth": 4,
    "notification": 2,
    "database": 5,
}


def calculate_business_impact(
    scenario: str | None,
    metrics: dict[str, float],
    affected_services: list[str],
) -> dict[str, Any] | None:
    if not scenario or not affected_services:
        return None

    failed_transactions = int(round(float(metrics.get("failed_transactions", 0))))
    affected_users = max(len(affected_services) * 35, int(round(failed_transactions * 4.22)))
    revenue_risk = int(round(failed_transactions * 816 / 1000.0) * 1000)
    service_weight = sum(SERVICE_IMPORTANCE.get(service, 2) for service in affected_services)

    sla_violation = (
        float(metrics.get("payment_latency_ms", 0)) >= 800
        or float(metrics.get("checkout_error_rate", 0)) >= 5
        or float(metrics.get("api_5xx_rate", 0)) >= 5
    )

    technical_score = min(
        100,
        int(
            min(float(metrics.get("database_cpu", 0)), 100) * 0.18
            + min(float(metrics.get("database_connections", 0)), 100) * 0.18
            + min(float(metrics.get("payment_latency_ms", 0)) / 50, 100) * 0.24
            + min(float(metrics.get("checkout_error_rate", 0)) * 3, 100) * 0.20
            + min(float(metrics.get("api_5xx_rate", 0)) * 5, 100) * 0.20
        ),
    )
    impact_score = min(100, technical_score + min(20, service_weight) + (10 if sla_violation else 0))
    severity = "CRITICAL" if impact_score >= 75 else "HIGH" if impact_score >= 55 else "MEDIUM"
    criticality = "HIGH" if service_weight >= 12 else "MEDIUM"

    return {
        "severity": severity,
        "impact_score": impact_score,
        "affected_services": len(affected_services),
        "affected_service_names": affected_services,
        "users_affected": affected_users,
        "failed_transactions": failed_transactions,
        "estimated_revenue_risk_inr_per_hour": revenue_risk,
        "sla_violation": sla_violation,
        "business_criticality": criticality,
        "technical_severity_score": technical_score,
        "source": "SIMULATOR_ESTIMATE",
        "disclaimer": "Business-impact values are configurable simulator estimates, not production company data.",
    }
