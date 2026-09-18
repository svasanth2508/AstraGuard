from __future__ import annotations

from typing import Any


RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def classify_incident_risk(severity: str | None, impact: dict[str, Any] | None) -> dict[str, Any]:
    """Classify how serious the incident is. This is separate from remediation-action risk."""
    severity_name = (severity or "LOW").upper()
    score = int((impact or {}).get("impact_score", 0) or 0)

    if severity_name == "CRITICAL" or score >= 80:
        level = "CRITICAL"
    elif severity_name == "HIGH" or score >= 60:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "level": level,
        "impact_score": score,
        "reason": "Incident risk reflects business/technical impact, not the danger of the remediation action.",
    }


def classify_action_policy(action: dict[str, Any]) -> dict[str, Any]:
    """Decide whether a proposed operational action may run automatically."""
    risk = str(action.get("risk", "HIGH")).upper()
    name = str(action.get("action", ""))
    destructive_tokens = ("delete", "drop table", "disable authentication", "wipe", "destroy")
    destructive = any(token in name.lower() for token in destructive_tokens)

    if destructive:
        return {
            "action_risk": "HIGH",
            "decision": "BLOCKED",
            "requires_approval": True,
            "auto_execute": False,
            "reason": "Destructive actions are blocked by policy.",
        }

    if risk == "LOW":
        return {
            "action_risk": "LOW",
            "decision": "AUTO_EXECUTION_PERMITTED",
            "requires_approval": False,
            "auto_execute": True,
            "reason": "Low-risk, reversible remediation may execute automatically.",
        }

    return {
        "action_risk": risk,
        "decision": "HUMAN_APPROVAL_REQUIRED",
        "requires_approval": True,
        "auto_execute": False,
        "reason": "Medium/high-risk operational changes require an operator decision.",
    }
