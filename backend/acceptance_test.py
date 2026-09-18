"""Fast, deterministic Phase-7 acceptance test for AstraGuard.

Run from backend/:  python acceptance_test.py
No server or browser is required. The script fast-forwards simulator timers so the
complete success and rollback paths are tested in seconds.
"""

from simulator import EnterpriseSimulator


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def fast_forward_incident(sim: EnterpriseSimulator) -> dict:
    assert sim._state.started_monotonic is not None
    sim._state.started_monotonic -= 20
    return sim.snapshot()


def success_path() -> None:
    print("\n=== SUCCESS PATH ===")
    sim = EnterpriseSimulator()
    initial = sim.snapshot()
    check(initial["system"]["services_healthy"] == 6, "All 6 services start healthy")
    check(initial["system"]["active_incidents"] == 0, "No incident exists initially")

    sim.inject("db-overload")
    degraded = fast_forward_incident(sim)
    check(len(degraded["alerts"]) >= 6, "DB overload generates at least 6 alerts")
    incident = degraded["incident"]
    check(incident is not None, "Correlated incident is created")
    check(incident["root_cause"] == "Database connection exhaustion", "Database exhaustion is top RCA")
    check(incident["confidence"] >= 90, "RCA confidence is at least 90%")

    incident_id = incident["id"]
    cf = sim.run_counterfactual_test(incident_id)["incident"]["counterfactual"]
    check(cf is not None and cf["causal_support"] == "HIGH", "Counterfactual causal support is HIGH")

    approved = sim.approve_remediation(incident_id)
    check(approved["incident"]["remediation_state"] == "EXECUTING", "Human approval starts remediation")

    assert sim._state.remediation_started_monotonic is not None
    sim._state.remediation_started_monotonic -= sim.RECOVERY_DURATION + 1
    sim.snapshot()  # advance EXECUTING -> VERIFYING
    assert sim._state.verification_started_monotonic is not None
    sim._state.verification_started_monotonic -= sim.VERIFICATION_DURATION + 1
    resolved = sim.snapshot()
    check(resolved["incident"]["status"] == "RESOLVED", "Incident closes after verification")
    check(resolved["incident"]["verification"]["passed"], "Remediation contract verification passes")
    check(resolved["system"]["system_status"] == "Recovery Verified", "System reports Recovery Verified")

    reset = sim.reset_demo()
    check(reset["system"]["services_healthy"] == 6 and not reset["alerts"], "Reset Demo restores healthy state")


def rollback_path() -> None:
    print("\n=== FORCED FAILURE / ROLLBACK PATH ===")
    sim = EnterpriseSimulator()
    degraded = fast_forward_incident_after_inject(sim)
    incident_id = degraded["incident"]["id"]
    sim.set_force_failure(True)
    sim.approve_remediation(incident_id)

    assert sim._state.remediation_started_monotonic is not None
    sim._state.remediation_started_monotonic -= sim.RECOVERY_DURATION + 1
    sim.snapshot()
    assert sim._state.verification_started_monotonic is not None
    sim._state.verification_started_monotonic -= sim.VERIFICATION_DURATION + 1
    rolling = sim.snapshot()
    check(rolling["incident"]["status"] == "ROLLBACK_IN_PROGRESS", "Failed verification triggers rollback")

    assert sim._state.rollback_started_monotonic is not None
    sim._state.rollback_started_monotonic -= sim.ROLLBACK_DURATION + 1
    rolled = sim.snapshot()
    check(rolled["incident"]["status"] == "OPEN_AFTER_ROLLBACK", "Incident stays open after rollback")
    check(any(e["event_type"] == "ROLLBACK_COMPLETED" for e in rolled["audit"]), "Audit trail records rollback completion")


def fast_forward_incident_after_inject(sim: EnterpriseSimulator) -> dict:
    sim.inject("db-overload")
    return fast_forward_incident(sim)


if __name__ == "__main__":
    success_path()
    rollback_path()
    print("\nPHASE 7 ACCEPTANCE RESULT: PASS")
