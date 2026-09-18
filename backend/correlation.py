from __future__ import annotations

from datetime import datetime
from typing import Any


CORRELATION_WINDOW_SECONDS = 120


SIGNATURE_FAMILIES = {
    "db-overload": {
        "DB_CONNECTION_HIGH",
        "DB_CPU_HIGH",
        "PAYMENT_LATENCY_HIGH",
        "CHECKOUT_FAILURE_RATE_HIGH",
        "API_5XX_HIGH",
        "TRANSACTION_FAILURE_HIGH",
    },
    "payment-failure": {
        "PAYMENT_LATENCY_HIGH",
        "CHECKOUT_FAILURE_RATE_HIGH",
        "API_5XX_HIGH",
        "TRANSACTION_FAILURE_HIGH",
    },
    "network-latency": {
        "NETWORK_LATENCY_HIGH",
        "PAYMENT_LATENCY_HIGH",
        "CHECKOUT_FAILURE_RATE_HIGH",
        "API_5XX_HIGH",
        "TRANSACTION_FAILURE_HIGH",
    },
    "traffic-spike": {
        "TRAFFIC_SURGE",
        "PAYMENT_LATENCY_HIGH",
        "CHECKOUT_FAILURE_RATE_HIGH",
        "API_5XX_HIGH",
        "TRANSACTION_FAILURE_HIGH",
    },
}


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def correlate_alerts(
    alerts: list[dict[str, Any]],
    services: list[dict[str, Any]],
    scenario: str | None,
) -> dict[str, Any] | None:
    """Group related active alerts into one deterministic incident.

    Correlation evidence uses timestamp proximity, known topology, shared scenario
    signatures and overlapping affected services. A minimum of two alerts is
    required so a single threshold crossing is not immediately promoted to an
    incident.
    """
    if len(alerts) < 2:
        return None

    timestamps = [_parse_timestamp(alert["timestamp"]) for alert in alerts]
    span_seconds = max(0.0, (max(timestamps) - min(timestamps)).total_seconds())
    timestamp_close = span_seconds <= CORRELATION_WINDOW_SECONDS

    alert_types = {alert["type"] for alert in alerts}
    family = SIGNATURE_FAMILIES.get(scenario or "", set())
    signature_matches = len(alert_types & family)

    affected_services = sorted({alert["service"] for alert in alerts})
    service_index = {service["id"]: service for service in services}

    topology_links: list[str] = []
    for service_id in affected_services:
        service = service_index.get(service_id)
        if not service:
            continue
        for dependency in service.get("dependencies", []):
            if dependency in affected_services:
                topology_links.append(f"{service_id} → {dependency}")

    reasons: list[str] = []
    if timestamp_close:
        reasons.append(f"Alerts occurred within {round(span_seconds, 1)} seconds")
    if signature_matches:
        reasons.append(f"{signature_matches} alerts match the {scenario or 'active'} incident signature")
    if topology_links:
        reasons.append("Affected services are connected in the dependency graph")
    if len(affected_services) >= 2:
        reasons.append(f"Blast radius spans {len(affected_services)} related services")

    # Transparent correlation strength; this is not a probability.
    strength = 0
    strength += 30 if timestamp_close else 0
    strength += min(30, signature_matches * 6)
    strength += 25 if topology_links else 0
    strength += min(15, len(affected_services) * 4)

    return {
        "correlated": True,
        "alert_count": len(alerts),
        "affected_services": affected_services,
        "timestamp_span_seconds": round(span_seconds, 1),
        "signature_matches": signature_matches,
        "topology_links": topology_links,
        "correlation_strength": min(100, strength),
        "reasons": reasons,
    }
