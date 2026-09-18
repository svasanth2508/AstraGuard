"""Deterministic Phase-8 acceptance test: persistence + incident memory."""
from pathlib import Path

DB = Path(__file__).with_name("astraguard.db")
if DB.exists():
    DB.unlink()

# Import after deleting DB so sequence starts clean.
from database import list_audit_events, list_incidents  # noqa: E402
from simulator import EnterpriseSimulator  # noqa: E402


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def degrade(sim: EnterpriseSimulator) -> dict:
    sim.inject("db-overload")
    assert sim._state.started_monotonic is not None
    sim._state.started_monotonic -= 20
    return sim.snapshot()


def resolve(sim: EnterpriseSimulator, incident_id: str) -> dict:
    sim.approve_remediation(incident_id)
    assert sim._state.remediation_started_monotonic is not None
    sim._state.remediation_started_monotonic -= sim.RECOVERY_DURATION + 1
    sim.snapshot()
    assert sim._state.verification_started_monotonic is not None
    sim._state.verification_started_monotonic -= sim.VERIFICATION_DURATION + 1
    return sim.snapshot()


print("\n=== PHASE 8 PERSISTENCE ===")
first = EnterpriseSimulator()
first_degraded = degrade(first)
first_id = first_degraded["incident"]["id"]
first_resolved = resolve(first, first_id)
check(first_resolved["incident"]["status"] == "RESOLVED", "First incident resolves successfully")

stored = list_incidents(limit=10)
check(any(item["id"] == first_id and item["status"] == "RESOLVED" for item in stored), "Resolved incident persists in SQLite")
check(len(list_audit_events(incident_id=first_id)) >= 5, "Audit events persist in SQLite")

print("\n=== PHASE 8 INCIDENT MEMORY ===")
second = EnterpriseSimulator()
second_degraded = degrade(second)
second_incident = second_degraded["incident"]
check(second_incident is not None, "Second correlated incident is created")
match = second_incident.get("historical_match")
check(match is not None, "Historical match is found")
check(match["incident_id"] == first_id, "Historical match points to prior resolved incident")
check(match["similarity"] == 100.0, "Identical alert fingerprint produces 100% Jaccard similarity")
check(match["previous_root_cause"] == "Database connection exhaustion", "Historical root cause is recalled")
check(bool(match["previous_successful_remediation"]), "Previous successful remediation is recalled")

snapshot = second.snapshot()
check(len(snapshot["historical_incidents"]) >= 2, "Snapshot exposes persistent incident history")
check(len(snapshot["persistent_audit"]) >= 5, "Snapshot exposes persistent audit history")

print("\nPHASE 8 ACCEPTANCE RESULT: PASS")
