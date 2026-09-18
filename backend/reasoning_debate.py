from __future__ import annotations

from typing import Any


def build_reasoning_debate(
    scenario: str | None,
    top_hypothesis: dict[str, Any] | None,
    metrics: dict[str, float],
    historical_match: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return a deterministic, judge-friendly reasoning debate.

    This is intentionally not a free-running multi-agent system. Each role is a
    structured view over the same evidence so the demo remains reproducible.
    """
    if not scenario or not top_hypothesis:
        return None

    cause = top_hypothesis["cause"]
    confidence = top_hypothesis["confidence"]

    skeptic_lines = {
        "db-overload": "Could the small traffic increase be the real cause of the database pressure?",
        "payment-failure": "Could a database problem be making Payment slow instead of Payment being the source?",
        "network-latency": "Could the elevated Payment latency be an isolated service fault rather than a network issue?",
        "traffic-spike": "Could the database itself be failing independently of the incoming request surge?",
    }
    evidence_lines = {
        "db-overload": f"Traffic is only {metrics['traffic_rps']:.0f} RPS, while DB connections reached {metrics['database_connections']:.0f}% and DB CPU reached {metrics['database_cpu']:.0f}%.",
        "payment-failure": f"Payment P95 latency reached {metrics['payment_latency_ms']:.0f} ms while DB CPU remains {metrics['database_cpu']:.0f}%.",
        "network-latency": f"Inter-service latency reached {metrics['network_latency_ms']:.0f} ms and symptoms appear across independent branches.",
        "traffic-spike": f"Inbound traffic reached {metrics['traffic_rps']:.0f} RPS before downstream services became saturated.",
    }
    dependency_lines = {
        "db-overload": "The affected request path converges on Database: Database → Payment → Checkout → API Gateway.",
        "payment-failure": "Checkout and API Gateway are downstream of Payment, while Database remains comparatively stable.",
        "network-latency": "Payment, Authentication and Notification degrade together across separate dependency branches, supporting a shared network-layer cause.",
        "traffic-spike": "The blast radius follows the normal request path from API Gateway through Checkout and Payment toward Database.",
    }

    history = "No strong historical match is required for this decision."
    if historical_match:
        history = (
            f"Incident memory found {historical_match['incident_id']} at "
            f"{historical_match['similarity']:.0f}% similarity with previous root cause "
            f"'{historical_match.get('previous_root_cause') or 'unknown'}'."
        )

    turns = [
        {"role": "RCA Agent", "statement": f"{cause} is the leading hypothesis at {confidence}% confidence."},
        {"role": "Skeptic", "statement": skeptic_lines.get(scenario, "Could another upstream dependency explain the same symptoms?")},
        {"role": "Evidence Analyzer", "statement": evidence_lines.get(scenario, "Observed telemetry supports the leading hypothesis more strongly than alternatives.")},
        {"role": "Dependency Analyzer", "statement": dependency_lines.get(scenario, "The dependency graph supports the observed blast radius.")},
        {"role": "Incident Memory", "statement": history},
        {"role": "Decision", "statement": f"{cause} remains the strongest hypothesis because it best explains timing, dependency structure, telemetry and blast radius."},
    ]

    return {
        "status": "COMPLETED",
        "mode": "Deterministic structured reasoning",
        "disclaimer": "This view summarizes rule-based evidence; it is not an unconstrained autonomous multi-agent system.",
        "turns": turns,
        "decision": turns[-1]["statement"],
    }
