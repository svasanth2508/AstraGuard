from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Any

from correlation import correlate_alerts
from counterfactual import run_counterfactual
from impact_engine import calculate_business_impact
from rca_engine import analyze_root_cause
from remediation import select_minimum_safe_remediation
from database import max_incident_sequence, save_audit_event, upsert_incident, list_incidents, list_audit_events
from incident_memory import build_fingerprint, find_historical_match
from reasoning_debate import build_reasoning_debate
from adaptive_runtime import runtime
from risk_engine import classify_incident_risk
from notification_service import notifier


BASELINE_METRICS = {
    "database_cpu": 42.0,
    "database_connections": 45.0,
    "payment_latency_ms": 240.0,
    "checkout_error_rate": 1.0,
    "api_5xx_rate": 1.0,
    "failed_transactions": 0.0,
    "traffic_rps": 820.0,
    "network_latency_ms": 38.0,
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "db-overload": {
        "label": "Database Overload",
        "summary": "Connection exhaustion creates a cascading dependency failure.",
        "expected_root_cause": "Database connection exhaustion",
        "duration": 10.0,
        "targets": {
            "database_cpu": 94.0,
            "database_connections": 98.0,
            "payment_latency_ms": 4100.0,
            "checkout_error_rate": 31.0,
            "api_5xx_rate": 18.0,
            "failed_transactions": 147.0,
            "traffic_rps": 870.0,
            "network_latency_ms": 62.0,
        },
    },
    "payment-failure": {
        "label": "Payment Service Failure",
        "summary": "Payment becomes the primary bottleneck while database health stays comparatively normal.",
        "expected_root_cause": "Payment service failure",
        "duration": 8.0,
        "targets": {
            "database_cpu": 51.0,
            "database_connections": 53.0,
            "payment_latency_ms": 5200.0,
            "checkout_error_rate": 38.0,
            "api_5xx_rate": 21.0,
            "failed_transactions": 181.0,
            "traffic_rps": 825.0,
            "network_latency_ms": 45.0,
        },
    },
    "network-latency": {
        "label": "Network Latency Spike",
        "summary": "Shared inter-service latency degrades several independent dependency branches.",
        "expected_root_cause": "Inter-service network degradation",
        "duration": 9.0,
        "targets": {
            "database_cpu": 49.0,
            "database_connections": 57.0,
            "payment_latency_ms": 2300.0,
            "checkout_error_rate": 13.0,
            "api_5xx_rate": 9.0,
            "failed_transactions": 76.0,
            "traffic_rps": 815.0,
            "network_latency_ms": 880.0,
        },
    },
    "traffic-spike": {
        "label": "Traffic Spike",
        "summary": "A sharp request surge cascades into service and database saturation.",
        "expected_root_cause": "Traffic surge causing cascading saturation",
        "duration": 9.0,
        "targets": {
            "database_cpu": 78.0,
            "database_connections": 82.0,
            "payment_latency_ms": 1450.0,
            "checkout_error_rate": 11.0,
            "api_5xx_rate": 7.0,
            "failed_transactions": 63.0,
            "traffic_rps": 2950.0,
            "network_latency_ms": 130.0,
        },
    },
}

SERVICES = [
    {"id": "api-gateway", "name": "API Gateway", "criticality": "HIGH", "dependencies": ["checkout"]},
    {"id": "checkout", "name": "Checkout Service", "criticality": "CRITICAL", "dependencies": ["payment", "auth"]},
    {"id": "payment", "name": "Payment Service", "criticality": "CRITICAL", "dependencies": ["database", "notification"]},
    {"id": "auth", "name": "Authentication Service", "criticality": "HIGH", "dependencies": []},
    {"id": "notification", "name": "Notification Service", "criticality": "MEDIUM", "dependencies": []},
    {"id": "database", "name": "Database", "criticality": "CRITICAL", "dependencies": []},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lerp(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


@dataclass
class SimulatorState:
    scenario: str | None = None
    started_monotonic: float | None = None
    started_at: str | None = None
    sequence: int = 0
    alert_first_seen: dict[str, str] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    incident_created_at: str | None = None
    counterfactual_completed: bool = False
    incident_seed: dict[str, Any] | None = None
    remediation_state: str = "NOT_STARTED"
    remediation_started_monotonic: float | None = None
    verification_started_monotonic: float | None = None
    rollback_started_monotonic: float | None = None
    force_remediation_failure: bool = False
    pre_remediation_metrics: dict[str, float] | None = None
    resolution_timestamp: str | None = None
    rejection_timestamp: str | None = None
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    audit_keys: set[str] = field(default_factory=set)
    ml_incident_telemetry: dict[str, float] | None = None
    ml_feedback_done: bool = False


class EnterpriseSimulator:
    RECOVERY_DURATION = 8.0
    VERIFICATION_DURATION = 4.0
    ROLLBACK_DURATION = 4.0

    def __init__(self) -> None:
        self._lock = RLock()
        self._state = SimulatorState(sequence=max_incident_sequence())
        self._append_history(BASELINE_METRICS)

    def _audit(self, key: str, event_type: str, message: str, details: dict[str, Any] | None = None) -> None:
        if key in self._state.audit_keys:
            return
        self._state.audit_keys.add(key)
        event = {
            "timestamp": _utc_now(),
            "incident_id": f"INC-{self._state.sequence:03d}" if self._state.sequence else None,
            "event_type": event_type,
            "message": message,
            "details": details or {},
        }
        self._state.audit_events.append(event)
        save_audit_event(f"{self._state.sequence}:{key}", event)

    def _progress(self) -> float:
        if not self._state.scenario or self._state.started_monotonic is None:
            return 0.0
        duration = float(SCENARIOS[self._state.scenario]["duration"])
        elapsed = max(0.0, monotonic() - self._state.started_monotonic)
        return min(1.0, elapsed / duration)

    def _degraded_metrics(self) -> dict[str, float]:
        if not self._state.scenario:
            return dict(BASELINE_METRICS)
        progress = self._progress()
        eased = progress * progress * (3.0 - 2.0 * progress)
        targets = SCENARIOS[self._state.scenario]["targets"]
        metrics: dict[str, float] = {}
        for key, baseline in BASELINE_METRICS.items():
            metrics[key] = round(_lerp(float(baseline), float(targets[key]), eased), 1)
        metrics["failed_transactions"] = round(metrics["failed_transactions"])
        return metrics

    def _successful_recovery_target(self) -> dict[str, float]:
        return {
            "database_cpu": 68.0,
            "database_connections": 61.0,
            "payment_latency_ms": 410.0,
            "checkout_error_rate": 2.0,
            "api_5xx_rate": 1.0,
            "failed_transactions": 2.0,
            "traffic_rps": 850.0,
            "network_latency_ms": 48.0,
        }

    def _failed_recovery_target(self) -> dict[str, float]:
        base = self._state.pre_remediation_metrics or self._degraded_metrics()
        return {
            **base,
            "database_cpu": max(91.0, float(base["database_cpu"]) - 2.0),
            "database_connections": max(94.0, float(base["database_connections"]) - 2.0),
            "payment_latency_ms": max(3300.0, float(base["payment_latency_ms"]) - 350.0),
            "checkout_error_rate": max(24.0, float(base["checkout_error_rate"]) - 2.0),
            "api_5xx_rate": max(14.0, float(base["api_5xx_rate"]) - 1.0),
        }

    def _advance_lifecycle(self) -> None:
        state = self._state.remediation_state
        now = monotonic()
        if state == "EXECUTING" and self._state.remediation_started_monotonic is not None:
            if now - self._state.remediation_started_monotonic >= self.RECOVERY_DURATION:
                self._state.remediation_state = "VERIFYING"
                self._state.verification_started_monotonic = now
                self._audit("verify-start", "VERIFICATION_STARTED", "Post-remediation recovery verification started.")
        elif state == "VERIFYING" and self._state.verification_started_monotonic is not None:
            if now - self._state.verification_started_monotonic >= self.VERIFICATION_DURATION:
                if self._state.force_remediation_failure:
                    self._state.remediation_state = "ROLLBACK"
                    self._state.rollback_started_monotonic = now
                    self._audit("verify-fail", "RECOVERY_FAILED", "Recovery verification failed; rollback initiated.")
                    self._audit("rollback-start", "ROLLBACK_STARTED", "Automatic rollback started using the remediation contract.")
                    incident_id = f"INC-{self._state.sequence:03d}"
                    rollback_action = (((self._state.incident_seed or {}).get("remediation") or {}).get("contract") or {}).get("rollback_action")
                    notice = notifier.recovery_failed(incident_id, rollback_action)
                    self._audit("admin-notified-failed", "ADMIN_NOTIFICATION", f"Administrator recovery-failure notification status: {notice.get('status')}.", notice)
                else:
                    self._state.remediation_state = "RESOLVED"
                    self._state.resolution_timestamp = _utc_now()
                    self._audit("verify-success", "RECOVERY_VERIFIED", "Recovery verified against all remediation-contract conditions.")
                    self._audit("incident-closed", "INCIDENT_CLOSED", "Incident closed only after telemetry verification succeeded.")
                    incident_id = f"INC-{self._state.sequence:03d}"
                    action = (((self._state.incident_seed or {}).get("remediation") or {}).get("recommended_action") or {}).get("action")
                    notice = notifier.recovery_verified(incident_id, action)
                    self._audit("admin-notified-recovery", "ADMIN_NOTIFICATION", f"Administrator recovery notification status: {notice.get('status')}.", notice)
                    if not self._state.ml_feedback_done:
                        feedback = runtime.learn_verified_incident(
                            self._state.scenario,
                            self._state.ml_incident_telemetry,
                            f"INC-{self._state.sequence:03d}" if self._state.sequence else None,
                        )
                        self._state.ml_feedback_done = bool(feedback.get("learned")) or feedback.get("reason") == "Incident already learned."
                        if feedback.get("learned"):
                            self._audit(
                                "adaptive-learned",
                                "ADAPTIVE_MODEL_UPDATED",
                                f"Adaptive incident classifier learned verified label {feedback.get('confirmed_label')}.",
                                feedback,
                            )
        elif state == "ROLLBACK" and self._state.rollback_started_monotonic is not None:
            if now - self._state.rollback_started_monotonic >= self.ROLLBACK_DURATION:
                self._state.remediation_state = "ROLLED_BACK"
                self._audit("rollback-complete", "ROLLBACK_COMPLETED", "Previous simulator configuration restored. Incident remains open.")

    def _current_metrics(self) -> dict[str, float]:
        self._advance_lifecycle()
        state = self._state.remediation_state
        if state in {"NOT_STARTED", "AWAITING_APPROVAL", "REJECTED"}:
            return self._degraded_metrics()
        start = self._state.pre_remediation_metrics or self._degraded_metrics()
        if state == "EXECUTING":
            elapsed = monotonic() - (self._state.remediation_started_monotonic or monotonic())
            p = min(1.0, max(0.0, elapsed / self.RECOVERY_DURATION))
            eased = p * p * (3.0 - 2.0 * p)
            target = self._failed_recovery_target() if self._state.force_remediation_failure else self._successful_recovery_target()
            return {k: round(_lerp(float(start[k]), float(target[k]), eased), 1) for k in BASELINE_METRICS}
        if state == "VERIFYING":
            return self._failed_recovery_target() if self._state.force_remediation_failure else self._successful_recovery_target()
        if state == "RESOLVED":
            return self._successful_recovery_target()
        if state == "ROLLBACK":
            elapsed = monotonic() - (self._state.rollback_started_monotonic or monotonic())
            p = min(1.0, max(0.0, elapsed / self.ROLLBACK_DURATION))
            failed = self._failed_recovery_target()
            return {k: round(_lerp(float(failed[k]), float(start[k]), p), 1) for k in BASELINE_METRICS}
        if state == "ROLLED_BACK":
            return dict(start)
        return self._degraded_metrics()

    @staticmethod
    def _service_states(metrics: dict[str, float], scenario: str | None) -> list[dict[str, Any]]:
        states: dict[str, str] = {service["id"]: "HEALTHY" for service in SERVICES}
        if metrics["database_cpu"] >= 88 or metrics["database_connections"] >= 92:
            states["database"] = "CRITICAL"
        elif metrics["database_cpu"] >= 75 or metrics["database_connections"] >= 78:
            states["database"] = "WARNING"
        if metrics["payment_latency_ms"] >= 3000 or (scenario == "payment-failure" and metrics["payment_latency_ms"] >= 1800):
            states["payment"] = "CRITICAL"
        elif metrics["payment_latency_ms"] >= 800:
            states["payment"] = "WARNING"
        if metrics["checkout_error_rate"] >= 22:
            states["checkout"] = "CRITICAL"
        elif metrics["checkout_error_rate"] >= 5:
            states["checkout"] = "WARNING"
        if metrics["api_5xx_rate"] >= 15:
            states["api-gateway"] = "CRITICAL"
        elif metrics["api_5xx_rate"] >= 5:
            states["api-gateway"] = "WARNING"
        if scenario == "network-latency" and metrics["network_latency_ms"] >= 500:
            states["notification"] = "WARNING"
            states["auth"] = "WARNING"
        result = []
        for service in SERVICES:
            sid = service["id"]
            service_metrics: dict[str, float] = {}
            if sid == "database":
                service_metrics = {"cpu_percent": metrics["database_cpu"], "connections_percent": metrics["database_connections"]}
            elif sid == "payment":
                service_metrics = {"p95_latency_ms": metrics["payment_latency_ms"]}
            elif sid == "checkout":
                service_metrics = {"error_rate_percent": metrics["checkout_error_rate"]}
            elif sid == "api-gateway":
                service_metrics = {"5xx_rate_percent": metrics["api_5xx_rate"], "requests_per_second": metrics["traffic_rps"]}
            elif sid == "auth":
                service_metrics = {"latency_ms": round(74 + max(0.0, metrics["network_latency_ms"] - 38) * 0.35, 1)}
            elif sid == "notification":
                service_metrics = {"latency_ms": round(95 + max(0.0, metrics["network_latency_ms"] - 38) * 0.55, 1)}
            result.append({**service, "status": states[sid], "metrics": service_metrics})
        return result

    def _alerts(self, metrics: dict[str, float]) -> list[dict[str, Any]]:
        definitions = [
            ("DB_CONNECTION_HIGH", "database", "CRITICAL", "Database connection utilization is above safe capacity.", "database_connections", 85.0),
            ("DB_CPU_HIGH", "database", "CRITICAL", "Database CPU utilization is critically high.", "database_cpu", 85.0),
            ("PAYMENT_LATENCY_HIGH", "payment", "CRITICAL", "Payment P95 latency exceeds the service objective.", "payment_latency_ms", 1200.0),
            ("CHECKOUT_FAILURE_RATE_HIGH", "checkout", "CRITICAL", "Checkout failure rate is above the acceptable limit.", "checkout_error_rate", 8.0),
            ("API_5XX_HIGH", "api-gateway", "HIGH", "API Gateway 5xx responses exceed the threshold.", "api_5xx_rate", 5.0),
            ("TRANSACTION_FAILURE_HIGH", "payment", "HIGH", "Failed business transactions exceed the threshold.", "failed_transactions", 30.0),
            ("NETWORK_LATENCY_HIGH", "api-gateway", "HIGH", "Inter-service network latency is elevated.", "network_latency_ms", 250.0),
            ("TRAFFIC_SURGE", "api-gateway", "HIGH", "Inbound request volume is substantially above baseline.", "traffic_rps", 1600.0),
        ]
        alerts: list[dict[str, Any]] = []
        now = _utc_now()
        for alert_type, service, severity, message, metric, threshold in definitions:
            value = float(metrics[metric])
            if value >= threshold:
                if alert_type not in self._state.alert_first_seen:
                    self._state.alert_first_seen[alert_type] = now
                    self._audit(f"alert-{alert_type}", "ALERT_DETECTED", f"{alert_type} detected on {service}.", {"metric": metric, "value": value})
                alerts.append({
                    "id": f"ALT-{list(self._state.alert_first_seen).index(alert_type) + 1:03d}",
                    "timestamp": self._state.alert_first_seen[alert_type], "service": service, "type": alert_type,
                    "severity": severity, "message": message, "metric": metric, "value": round(value, 1), "threshold": threshold,
                })
        return alerts

    def _append_history(self, metrics: dict[str, float]) -> None:
        point = {"timestamp": _utc_now(), **{k: round(float(metrics[k]), 1) for k in (
            "database_cpu", "database_connections", "payment_latency_ms", "checkout_error_rate", "api_5xx_rate"
        )}}
        if not self._state.history or any(abs(float(self._state.history[-1].get(k, 0)) - float(point[k])) >= 0.1 for k in point if k != "timestamp"):
            self._state.history.append(point)
            self._state.history = self._state.history[-60:]

    def _ensure_incident_seed(self, alerts: list[dict[str, Any]], services: list[dict[str, Any]], metrics: dict[str, float]) -> None:
        if self._state.incident_seed is not None:
            return
        scenario = self._state.scenario
        correlation = correlate_alerts(alerts, services, scenario)
        if not correlation:
            return
        self._state.ml_incident_telemetry = dict(metrics)
        self._state.incident_created_at = _utc_now()
        severity = "CRITICAL" if any(alert["severity"] == "CRITICAL" for alert in alerts) else "HIGH"
        rca = analyze_root_cause(scenario, alerts, correlation["affected_services"])
        top = rca["top_hypothesis"] if rca else None
        impact = calculate_business_impact(scenario, metrics, correlation["affected_services"])
        remediation = select_minimum_safe_remediation(scenario, top["cause"] if top else None, top["confidence"] if top else 0)
        incident_risk = classify_incident_risk(severity, impact)
        if remediation and remediation["autonomy"].get("auto_execute"):
            self._state.remediation_state = "EXECUTING"
            self._state.pre_remediation_metrics = dict(metrics)
            self._state.remediation_started_monotonic = monotonic()
        elif remediation and remediation["autonomy"]["requires_approval"]:
            self._state.remediation_state = "AWAITING_APPROVAL"
        else:
            self._state.remediation_state = "NOT_STARTED"
        alert_types = [alert["type"] for alert in alerts]
        fingerprint = build_fingerprint(alert_types)
        incident_id = f"INC-{self._state.sequence:03d}"
        historical_match = find_historical_match(fingerprint, exclude_incident_id=incident_id)
        reasoning_debate = build_reasoning_debate(scenario, top, metrics, historical_match)
        self._state.incident_seed = {
            "severity": severity,
            "title": SCENARIOS[scenario]["label"] if scenario else "Correlated Incident",
            "related_alerts": [alert["id"] for alert in alerts], "alert_count": len(alerts),
            "alert_types": alert_types, "fingerprint": fingerprint,
            "affected_services": correlation["affected_services"], "correlation": correlation,
            "root_cause": top["cause"] if top else None, "confidence": top["confidence"] if top else 0,
            "rca": rca, "business_impact": impact, "remediation": remediation,
            "incident_risk": incident_risk,
            "historical_match": historical_match,
            "reasoning_debate": reasoning_debate,
        }
        self._audit("correlated", "ALERTS_CORRELATED", f"{len(alerts)} alerts correlated into one incident.")
        self._audit("incident-created", "INCIDENT_CREATED", f"INC-{self._state.sequence:03d} created with severity {severity}.")
        if top:
            self._audit("rca-complete", "RCA_COMPLETED", f"Leading root cause: {top['cause']} ({top['confidence']}%).")
        if remediation:
            self._audit("remediation-selected", "REMEDIATION_SELECTED", f"Minimum Safe Remediation selected: {remediation['recommended_action']['action']}.")
            if remediation["autonomy"].get("auto_execute"):
                self._audit("auto-execution", "AUTO_REMEDIATION_STARTED", "Low-risk remediation started automatically under autonomy policy.")
            elif remediation["autonomy"].get("requires_approval"):
                self._audit("approval-required", "HUMAN_APPROVAL_REQUIRED", "Remediation requires human approval because the action risk is not low.")

        notification_incident = {
            "id": incident_id,
            "severity": severity,
            "title": SCENARIOS[scenario]["label"] if scenario else "Correlated Incident",
            "root_cause": top["cause"] if top else None,
            "confidence": top["confidence"] if top else 0,
            "affected_services": correlation["affected_services"],
            "remediation": remediation,
        }
        notice = notifier.incident_detected(notification_incident)
        self._audit("admin-notified-detected", "ADMIN_NOTIFICATION", f"Administrator incident notification status: {notice.get('status')}.", notice)
        if remediation and remediation["autonomy"].get("requires_approval"):
            approval_notice = notifier.approval_required(notification_incident)
            self._audit("admin-notified-approval", "ADMIN_NOTIFICATION", f"Administrator approval notification status: {approval_notice.get('status')}.", approval_notice)

    def _verification(self, metrics: dict[str, float]) -> dict[str, Any] | None:
        if not self._state.incident_seed or not self._state.incident_seed.get("remediation"):
            return None
        from verifier import verify_recovery
        state = self._state.remediation_state
        if state not in {"VERIFYING", "RESOLVED", "ROLLBACK", "ROLLED_BACK"}:
            return None
        contract = self._state.incident_seed["remediation"]["contract"]
        result = verify_recovery(metrics, contract)
        if self._state.force_remediation_failure and state in {"VERIFYING", "ROLLBACK", "ROLLED_BACK"}:
            result["passed"] = False
            result["status"] = "FAILED"
        return result

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            metrics = self._current_metrics()
            learn_healthy = (
                self._state.scenario is None
                or self._state.remediation_state == "RESOLVED"
            )
            adaptive_monitoring = runtime.evaluate(metrics, learn_healthy=learn_healthy)
            self._append_history(metrics)
            services = self._service_states(metrics, self._state.scenario)
            alerts = self._alerts(metrics)
            self._ensure_incident_seed(alerts, services, metrics)
            seed = self._state.incident_seed
            if seed is not None and "adaptive_at_detection" not in seed:
                seed["adaptive_at_detection"] = dict(adaptive_monitoring)
            incident = None
            if seed:
                counterfactual = run_counterfactual(self._state.scenario, seed["rca"]["top_hypothesis"]) if self._state.counterfactual_completed else None
                verification = self._verification(metrics)
                status_map = {
                    "AWAITING_APPROVAL": "AWAITING_APPROVAL", "REJECTED": "REMEDIATION_REJECTED",
                    "EXECUTING": "REMEDIATING", "VERIFYING": "VERIFYING_RECOVERY", "RESOLVED": "RESOLVED",
                    "ROLLBACK": "ROLLBACK_IN_PROGRESS", "ROLLED_BACK": "OPEN_AFTER_ROLLBACK", "NOT_STARTED": "INVESTIGATING",
                }
                incident = {
                    "id": f"INC-{self._state.sequence:03d}", "created_at": self._state.incident_created_at,
                    "status": status_map.get(self._state.remediation_state, "INVESTIGATING"),
                    "scenario": self._state.scenario, **seed, "counterfactual": counterfactual,
                    "remediation_state": self._state.remediation_state, "verification": verification,
                    "force_remediation_failure": self._state.force_remediation_failure,
                    "resolved_at": self._state.resolution_timestamp,
                }
                if incident["remediation"]:
                    incident["remediation"] = {**incident["remediation"], "status": self._state.remediation_state}
                upsert_incident(incident, seed.get("alert_types", []), seed.get("fingerprint", []))
            healthy = sum(1 for s in services if s["status"] == "HEALTHY")
            critical = sum(1 for s in services if s["status"] == "CRITICAL")
            warning = sum(1 for s in services if s["status"] == "WARNING")
            resolved = self._state.remediation_state == "RESOLVED"
            active = bool(self._state.scenario) and not resolved
            phase_map = {"EXECUTING": "REMEDIATING", "VERIFYING": "VERIFYING", "RESOLVED": "RECOVERED", "ROLLBACK": "ROLLBACK", "ROLLED_BACK": "DEGRADED"}
            mttr = 0
            if self._state.started_at and self._state.resolution_timestamp:
                try:
                    a = datetime.fromisoformat(self._state.started_at); b = datetime.fromisoformat(self._state.resolution_timestamp); mttr = max(0, int((b-a).total_seconds()))
                except ValueError:
                    mttr = 0
            return {
                "system": {
                    "name": "AstraGuard", "subtitle": "Self-Verifying Autonomous Enterprise Incident Resolution Engine",
                    "system_status": "Recovery Verified" if resolved else ("Incident Active" if active else "Operational"),
                    "active_incidents": 1 if incident and not resolved else 0,
                    "critical_incidents": 1 if incident and incident["severity"] == "CRITICAL" and not resolved else 0,
                    "alerts": len(alerts), "services_healthy": healthy, "services_warning": warning, "services_critical": critical,
                    "services_total": len(services), "mttr_seconds": mttr, "auto_resolved": 1 if resolved else 0,
                },
                "simulation": {
                    "active": active, "scenario": self._state.scenario,
                    "scenario_label": SCENARIOS[self._state.scenario]["label"] if self._state.scenario else None,
                    "progress": round(self._progress()*100, 1) if self._state.scenario else 0.0,
                    "started_at": self._state.started_at, "phase": phase_map.get(self._state.remediation_state, "DEGRADED" if self._state.scenario else "HEALTHY"),
                },
                "metrics": metrics, "adaptive_monitoring": adaptive_monitoring, "services": services, "alerts": alerts, "incident": incident,
                "history": list(self._state.history), "audit": list(self._state.audit_events),
                "historical_incidents": list_incidents(limit=12),
                "persistent_audit": list_audit_events(limit=120),
                "notifications": notifier.history(limit=30),
                "notification_config": notifier.config(),
            }

    def inject(self, scenario: str) -> dict[str, Any]:
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        with self._lock:
            self._state = SimulatorState(sequence=self._state.sequence + 1)
            self._state.scenario = scenario; self._state.started_monotonic = monotonic(); self._state.started_at = _utc_now()
            self._append_history(BASELINE_METRICS)
            self._audit("incident-injected", "INCIDENT_INJECTED", f"Controlled scenario injected: {SCENARIOS[scenario]['label']}.")
            return self.snapshot()

    def run_counterfactual_test(self, incident_id: str) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot(); incident = current.get("incident")
            if not incident or incident["id"] != incident_id:
                raise ValueError("Incident not found")
            self._state.counterfactual_completed = True
            self._audit("counterfactual", "COUNTERFACTUAL_COMPLETED", "Counterfactual root-cause test completed.")
            return self.snapshot()

    def set_force_failure(self, enabled: bool) -> dict[str, Any]:
        with self._lock:
            self._state.force_remediation_failure = bool(enabled)
            self._audit(f"force-failure-{enabled}", "TEST_MODE_CHANGED", f"Force remediation failure {'enabled' if enabled else 'disabled'}.")
            return self.snapshot()

    def approve_remediation(self, incident_id: str) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot(); incident = current.get("incident")
            if not incident or incident["id"] != incident_id:
                raise ValueError("Incident not found")
            if self._state.remediation_state not in {"AWAITING_APPROVAL", "REJECTED", "ROLLED_BACK"}:
                raise ValueError(f"Remediation cannot be approved from state {self._state.remediation_state}")
            self._state.pre_remediation_metrics = dict(current["metrics"])
            self._state.remediation_state = "EXECUTING"
            self._state.remediation_started_monotonic = monotonic()
            self._state.verification_started_monotonic = None; self._state.rollback_started_monotonic = None
            self._audit("approved", "HUMAN_APPROVED", "Human approved the Level-2 remediation action.")
            self._audit("execution-start", "REMEDIATION_EXECUTING", "Remediation execution started.")
            return self.snapshot()

    def reject_remediation(self, incident_id: str) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot(); incident = current.get("incident")
            if not incident or incident["id"] != incident_id:
                raise ValueError("Incident not found")
            self._state.remediation_state = "REJECTED"; self._state.rejection_timestamp = _utc_now()
            self._audit("rejected", "HUMAN_REJECTED", "Human rejected the recommended remediation. Incident remains open.")
            return self.snapshot()

    def verify_now(self, incident_id: str) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot(); incident = current.get("incident")
            if not incident or incident["id"] != incident_id:
                raise ValueError("Incident not found")
            if self._state.remediation_state == "EXECUTING":
                self._state.remediation_state = "VERIFYING"; self._state.verification_started_monotonic = monotonic() - self.VERIFICATION_DURATION
            elif self._state.remediation_state == "VERIFYING":
                self._state.verification_started_monotonic = monotonic() - self.VERIFICATION_DURATION
            return self.snapshot()

    def rollback(self, incident_id: str) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot(); incident = current.get("incident")
            if not incident or incident["id"] != incident_id:
                raise ValueError("Incident not found")
            self._state.remediation_state = "ROLLBACK"; self._state.rollback_started_monotonic = monotonic()
            self._audit("manual-rollback", "ROLLBACK_STARTED", "Rollback manually initiated.")
            return self.snapshot()

    def reset_demo(self) -> dict[str, Any]:
        with self._lock:
            seq = self._state.sequence
            self._state = SimulatorState(sequence=seq)
            self._append_history(BASELINE_METRICS)
            return self.snapshot()


simulator = EnterpriseSimulator()
