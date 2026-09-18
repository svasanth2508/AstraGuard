from __future__ import annotations

from typing import Any, Iterable

from database import list_incidents


def build_fingerprint(alert_types: Iterable[str]) -> list[str]:
    """Create a stable lightweight incident fingerprint from alert signatures."""
    return sorted({str(item).strip().upper() for item in alert_types if str(item).strip()})


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    left = set(a)
    right = set(b)
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def find_historical_match(current_fingerprint: list[str], exclude_incident_id: str | None = None) -> dict[str, Any] | None:
    """Return the most similar previously resolved incident using Jaccard similarity."""
    if not current_fingerprint:
        return None
    candidates = list_incidents(limit=50, completed_only=True)
    best: tuple[float, dict[str, Any]] | None = None
    for incident in candidates:
        if exclude_incident_id and incident["id"] == exclude_incident_id:
            continue
        score = jaccard_similarity(current_fingerprint, incident.get("fingerprint") or [])
        if best is None or score > best[0]:
            best = (score, incident)
    if best is None or best[0] <= 0:
        return None
    score, incident = best
    return {
        "incident_id": incident["id"],
        "similarity": round(score * 100, 1),
        "previous_root_cause": incident.get("root_cause"),
        "previous_successful_remediation": incident.get("remediation_action"),
        "recovery": "Successful" if incident.get("recovery_successful") else "Not verified",
        "matched_alerts": sorted(set(current_fingerprint) & set(incident.get("fingerprint") or [])),
        "method": "Jaccard similarity over normalized alert signatures",
    }
