from __future__ import annotations

from time import monotonic

from adaptive_runtime import runtime
from simulator import simulator


def force_scenario_peak() -> dict:
    if simulator._state.started_monotonic is not None:
        simulator._state.started_monotonic = monotonic() - 30
    return simulator.snapshot()


def resolve_current_incident() -> dict:
    snap = simulator.snapshot()
    incident = snap.get("incident")
    if not incident:
        raise AssertionError("Expected incident before remediation")
    if incident["remediation_state"] == "AWAITING_APPROVAL":
        simulator.approve_remediation(incident["id"])
    if simulator._state.remediation_started_monotonic is not None:
        simulator._state.remediation_started_monotonic = monotonic() - simulator.RECOVERY_DURATION - 1
    snap = simulator.snapshot()
    if simulator._state.verification_started_monotonic is not None:
        simulator._state.verification_started_monotonic = monotonic() - simulator.VERIFICATION_DURATION - 1
    return simulator.snapshot()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main() -> None:
    print("AstraGuard autonomous ML acceptance test\n")

    simulator.reset_demo()
    healthy = simulator.snapshot()["adaptive_monitoring"]
    check(healthy["pattern"] in {"NORMAL", "SUSPICIOUS"}, "Healthy baseline is not marked as critical anomaly")
    check(healthy["predicted_incident"] == "HEALTHY", "Healthy baseline classified as HEALTHY")
    check(healthy["observations_learned"] >= 300, "Healthy streaming baseline has been learned")

    expected = {
        "db-overload": "DB_OVERLOAD",
        "payment-failure": "PAYMENT_FAILURE",
        "network-latency": "NETWORK_LATENCY",
        "traffic-spike": "TRAFFIC_SPIKE",
    }

    for scenario, label in expected.items():
        simulator.reset_demo()
        simulator.inject(scenario)
        snap = force_scenario_peak()
        adaptive = snap["adaptive_monitoring"]
        check(adaptive["pattern"] in {"SUSPICIOUS", "ANOMALOUS"}, f"{scenario} produces an unusual telemetry pattern")
        check(adaptive["predicted_incident"] == label, f"{scenario} classified as {label}")
        check(adaptive["learning_enabled"] is False, f"Learning pauses while {scenario} is an active incident")

    simulator.reset_demo()
    before = runtime.status()["confirmed_incidents_learned"]
    simulator.inject("db-overload")
    force_scenario_peak()
    resolved = resolve_current_incident()
    check(resolved["incident"]["status"] == "RESOLVED", "DB overload reaches verified recovery")
    after = runtime.status()["confirmed_incidents_learned"]
    check(after == before + 1, "Verified incident automatically feeds the online classifier")
    check(runtime.status()["last_confirmed_label"] == "DB_OVERLOAD", "Confirmed DB overload label is stored")

    saved = runtime.save()
    check(saved, "Adaptive model state persists to backend/model_store")

    print("\nAUTONOMOUS ML ACCEPTANCE RESULT: PASS")


if __name__ == "__main__":
    main()
