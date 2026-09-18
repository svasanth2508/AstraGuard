"""Phase-9 final hardening acceptance test.

Checks every incident scenario reaches correlation/RCA with the expected leading
hypothesis, then checks the flagship DB-overload success + rollback paths and
structured reasoning debate.
"""
from simulator import EnterpriseSimulator, SCENARIOS

EXPECTED = {key: value["expected_root_cause"] for key, value in SCENARIOS.items()}


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def degrade(sim: EnterpriseSimulator, scenario: str) -> dict:
    sim.inject(scenario)
    assert sim._state.started_monotonic is not None
    sim._state.started_monotonic -= 30
    return sim.snapshot()


print("\n=== ALL SCENARIOS ===")
for scenario, expected_root in EXPECTED.items():
    sim = EnterpriseSimulator()
    snap = degrade(sim, scenario)
    check(len(snap["alerts"]) >= 2, f"{scenario}: generates correlated alert set")
    incident = snap["incident"]
    check(incident is not None, f"{scenario}: incident created")
    check(incident["root_cause"] == expected_root, f"{scenario}: expected root cause selected")
    check(len(incident["rca"]["hypotheses"]) >= 3, f"{scenario}: three competing hypotheses available")
    debate = incident.get("reasoning_debate")
    check(debate is not None and len(debate["turns"]) >= 5, f"{scenario}: structured reasoning debate available")
    check(incident["business_impact"] is not None, f"{scenario}: business impact available")
    check(incident["remediation"] is not None, f"{scenario}: remediation recommendation available")

print("\n=== FLAGSHIP DB SUCCESS LOOP ===")
sim = EnterpriseSimulator()
snap = degrade(sim, "db-overload")
incident_id = snap["incident"]["id"]
cf = sim.run_counterfactual_test(incident_id)["incident"]["counterfactual"]
check(cf["causal_support"] == "HIGH", "DB overload counterfactual causal support is HIGH")
sim.approve_remediation(incident_id)
assert sim._state.remediation_started_monotonic is not None
sim._state.remediation_started_monotonic -= sim.RECOVERY_DURATION + 1
sim.snapshot()
assert sim._state.verification_started_monotonic is not None
sim._state.verification_started_monotonic -= sim.VERIFICATION_DURATION + 1
resolved = sim.snapshot()
check(resolved["incident"]["status"] == "RESOLVED", "DB overload closes only after verification")
check(resolved["incident"]["verification"]["passed"], "DB remediation contract passes")

print("\n=== FLAGSHIP DB FAILURE LOOP ===")
sim2 = EnterpriseSimulator()
snap2 = degrade(sim2, "db-overload")
id2 = snap2["incident"]["id"]
sim2.set_force_failure(True)
sim2.approve_remediation(id2)
assert sim2._state.remediation_started_monotonic is not None
sim2._state.remediation_started_monotonic -= sim2.RECOVERY_DURATION + 1
sim2.snapshot()
assert sim2._state.verification_started_monotonic is not None
sim2._state.verification_started_monotonic -= sim2.VERIFICATION_DURATION + 1
rolling = sim2.snapshot()
check(rolling["incident"]["status"] == "ROLLBACK_IN_PROGRESS", "Failed verification starts rollback")
assert sim2._state.rollback_started_monotonic is not None
sim2._state.rollback_started_monotonic -= sim2.ROLLBACK_DURATION + 1
rolled = sim2.snapshot()
check(rolled["incident"]["status"] == "OPEN_AFTER_ROLLBACK", "Rollback keeps incident open")

print("\nPHASE 9 ACCEPTANCE RESULT: PASS")
