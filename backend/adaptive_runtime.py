from __future__ import annotations

import json
import math
import os
import pickle
import random
import statistics
from collections import deque
from pathlib import Path
from time import monotonic
from typing import Any

from river import anomaly, drift

try:
    from river import forest
    _ARF = getattr(forest, "ARFClassifier", None)
except Exception:
    _ARF = None

if _ARF is None:
    from river import tree


MODEL_DIR = Path(__file__).resolve().parent / "model_store"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = MODEL_DIR / "adaptive_runtime.pkl"
META_PATH = MODEL_DIR / "learning_state.json"

SCENARIO_LABELS = {
    "db-overload": "DB_OVERLOAD",
    "payment-failure": "PAYMENT_FAILURE",
    "network-latency": "NETWORK_LATENCY",
    "traffic-spike": "TRAFFIC_SPIKE",
}

CLASS_LABELS = [
    "HEALTHY",
    "DB_OVERLOAD",
    "PAYMENT_FAILURE",
    "NETWORK_LATENCY",
    "TRAFFIC_SPIKE",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def normalize_telemetry(telemetry: dict[str, Any]) -> dict[str, float]:
    """Normalize current Phase-9 telemetry to roughly 0..1 ranges.

    Half-Space Trees work best when features are similarly scaled. Values are
    clipped above 1 for extreme incidents instead of being discarded.
    """
    return {
        "db_cpu": min(_safe_float(telemetry.get("database_cpu", telemetry.get("db_cpu", 0))) / 100.0, 1.5),
        "db_connections": min(_safe_float(telemetry.get("database_connections", telemetry.get("db_connections", 0))) / 100.0, 1.5),
        "payment_latency": min(_safe_float(telemetry.get("payment_latency_ms", telemetry.get("payment_latency", 0))) / 6000.0, 1.5),
        "checkout_error_rate": min(_safe_float(telemetry.get("checkout_error_rate", 0)) / 50.0, 1.5),
        "api_5xx_rate": min(_safe_float(telemetry.get("api_5xx_rate", 0)) / 30.0, 1.5),
        "failed_transactions": min(_safe_float(telemetry.get("failed_transactions", 0)) / 250.0, 1.5),
        "traffic_rps": min(_safe_float(telemetry.get("traffic_rps", 0)) / 3500.0, 1.5),
        "network_latency": min(_safe_float(telemetry.get("network_latency_ms", telemetry.get("network_latency", 0))) / 1200.0, 1.5),
    }


def _healthy_sample() -> dict[str, float]:
    return {
        "database_cpu": random.uniform(35, 55),
        "database_connections": random.uniform(32, 58),
        "payment_latency_ms": random.uniform(170, 380),
        "checkout_error_rate": random.uniform(0.2, 2.5),
        "api_5xx_rate": random.uniform(0.1, 2.0),
        "failed_transactions": random.uniform(0, 4),
        "traffic_rps": random.uniform(700, 980),
        "network_latency_ms": random.uniform(22, 65),
    }


def _scenario_sample(label: str) -> dict[str, float]:
    if label == "HEALTHY":
        return _healthy_sample()
    if label == "DB_OVERLOAD":
        return {
            "database_cpu": random.uniform(82, 99),
            "database_connections": random.uniform(86, 100),
            "payment_latency_ms": random.uniform(1800, 5200),
            "checkout_error_rate": random.uniform(12, 38),
            "api_5xx_rate": random.uniform(7, 24),
            "failed_transactions": random.uniform(45, 190),
            "traffic_rps": random.uniform(720, 1100),
            "network_latency_ms": random.uniform(30, 100),
        }
    if label == "PAYMENT_FAILURE":
        return {
            "database_cpu": random.uniform(36, 64),
            "database_connections": random.uniform(34, 68),
            "payment_latency_ms": random.uniform(3000, 6000),
            "checkout_error_rate": random.uniform(18, 45),
            "api_5xx_rate": random.uniform(8, 24),
            "failed_transactions": random.uniform(75, 220),
            "traffic_rps": random.uniform(700, 1100),
            "network_latency_ms": random.uniform(25, 90),
        }
    if label == "NETWORK_LATENCY":
        return {
            "database_cpu": random.uniform(38, 62),
            "database_connections": random.uniform(38, 70),
            "payment_latency_ms": random.uniform(900, 2800),
            "checkout_error_rate": random.uniform(3, 16),
            "api_5xx_rate": random.uniform(2, 10),
            "failed_transactions": random.uniform(8, 90),
            "traffic_rps": random.uniform(700, 1050),
            "network_latency_ms": random.uniform(450, 1150),
        }
    if label == "TRAFFIC_SPIKE":
        return {
            "database_cpu": random.uniform(58, 88),
            "database_connections": random.uniform(58, 90),
            "payment_latency_ms": random.uniform(500, 1800),
            "checkout_error_rate": random.uniform(3, 14),
            "api_5xx_rate": random.uniform(2, 9),
            "failed_transactions": random.uniform(10, 85),
            "traffic_rps": random.uniform(1800, 3400),
            "network_latency_ms": random.uniform(50, 180),
        }
    raise ValueError(f"Unsupported bootstrap label: {label}")


def _new_classifier():
    if _ARF is not None:
        try:
            return _ARF(n_models=10, seed=42)
        except TypeError:
            return _ARF(seed=42)
    return tree.HoeffdingAdaptiveTreeClassifier(seed=42)


class AdaptiveRuntime:
    """Autonomous streaming-ML runtime for AstraGuard.

    - Half-Space Trees: online anomaly detection.
    - Adaptive Random Forest (or River adaptive-tree fallback): online incident classification.
    - ADWIN: concept-drift detection on verified-healthy telemetry only.
    - Verified incidents feed confirmed labels back into the classifier.
    - Model state is persisted across backend restarts.
    """

    def __init__(self) -> None:
        self.anomaly_model = anomaly.HalfSpaceTrees(n_trees=25, height=8, window_size=250, seed=42)
        self.classifier = _new_classifier()
        self.drift_detectors = {name: drift.ADWIN(delta=0.002) for name in normalize_telemetry({}).keys()}

        self.observations = 0
        self.healthy_observations = 0
        self.confirmed_incidents_learned = 0
        self.drift_events = 0
        self.bootstrap_examples = 0
        self.last_pattern = "LEARNING"
        self.last_raw_anomaly_score = 0.0
        self.last_anomaly_index = 0.0
        self.last_prediction = "HEALTHY"
        self.last_confidence = 0.0
        self.last_probabilities: dict[str, float] = {}
        self.baseline_status = "LEARNING"
        self.last_drift_feature: str | None = None
        self.last_drift_observation: int | None = None
        self.last_confirmed_incident_id: str | None = None
        self.last_confirmed_label: str | None = None
        self.last_saved_observation = 0

        self.healthy_score_window: deque[float] = deque(maxlen=500)
        self.suspicious_threshold = 0.45
        self.anomaly_threshold = 0.70

        self._last_eval_time = 0.0
        self._last_signature: tuple[float, ...] | None = None
        self._last_result: dict[str, Any] | None = None

        if not self._load():
            self._bootstrap()
            self.save()

    def _bootstrap(self) -> None:
        random.seed(42)

        # Give Half-Space Trees enough healthy streaming context to establish a baseline.
        for _ in range(700):
            telemetry = _healthy_sample()
            x = normalize_telemetry(telemetry)
            score = _safe_float(self.anomaly_model.score_one(x))
            self.anomaly_model.learn_one(x)
            self.observations += 1
            self.healthy_observations += 1
            if self.observations > 300:
                self.healthy_score_window.append(score)

        self._recalibrate_thresholds()

        # Seed only the broad scenario concepts. Online updates later come from verified outcomes.
        bootstrap_rows: list[tuple[dict[str, float], str]] = []
        for label in CLASS_LABELS:
            for _ in range(180):
                bootstrap_rows.append((_scenario_sample(label), label))
        random.shuffle(bootstrap_rows)
        for sample, label in bootstrap_rows:
            self.classifier.learn_one(normalize_telemetry(sample), label)
            self.bootstrap_examples += 1

        self.baseline_status = "STABLE"
        self.last_pattern = "NORMAL"

    def _recalibrate_thresholds(self) -> None:
        scores = sorted(self.healthy_score_window)
        if len(scores) < 50:
            return
        p95 = scores[min(len(scores) - 1, int(len(scores) * 0.95))]
        p995 = scores[min(len(scores) - 1, int(len(scores) * 0.995))]
        # Keep a minimum gap to prevent tiny numerical variations from causing alarms.
        self.suspicious_threshold = max(p95, 0.01)
        self.anomaly_threshold = max(p995, self.suspicious_threshold + 0.01)

    def _anomaly_index(self, score: float) -> float:
        if score <= self.suspicious_threshold:
            if self.suspicious_threshold <= 0:
                return 0.0
            return max(0.0, min(0.49, 0.49 * score / self.suspicious_threshold))
        if score < self.anomaly_threshold:
            width = max(1e-9, self.anomaly_threshold - self.suspicious_threshold)
            return 0.50 + 0.29 * (score - self.suspicious_threshold) / width
        # Above the healthy anomaly threshold, rise quickly but remain bounded.
        excess = score - self.anomaly_threshold
        return min(1.0, 0.80 + excess * 4.0)

    def _classify_pattern(self, score: float) -> str:
        if self.healthy_observations < 300:
            return "LEARNING"
        if score >= self.anomaly_threshold:
            return "ANOMALOUS"
        if score >= self.suspicious_threshold:
            return "SUSPICIOUS"
        return "NORMAL"

    @staticmethod
    def _signature(x: dict[str, float]) -> tuple[float, ...]:
        return tuple(round(x[k], 5) for k in sorted(x))

    def evaluate(self, telemetry: dict[str, Any], learn_healthy: bool) -> dict[str, Any]:
        x = normalize_telemetry(telemetry)
        signature = self._signature(x)
        now = monotonic()

        # Snapshot may be requested multiple times in the same server action. Avoid learning duplicates.
        if self._last_result is not None and self._last_signature == signature and now - self._last_eval_time < 0.45:
            return dict(self._last_result)

        raw_score = _safe_float(self.anomaly_model.score_one(x))
        pattern = self._classify_pattern(raw_score)
        anomaly_index = self._anomaly_index(raw_score)

        probabilities = self.classifier.predict_proba_one(x) or {}
        if probabilities:
            prediction = max(probabilities, key=probabilities.get)
            confidence = _safe_float(probabilities.get(prediction))
        else:
            prediction, confidence = "HEALTHY", 0.0

        drifted_features: list[str] = []
        if learn_healthy:
            self.anomaly_model.learn_one(x)
            self.observations += 1
            self.healthy_observations += 1
            self.healthy_score_window.append(raw_score)

            # ADWIN sees only telemetry already considered safe/healthy by the lifecycle.
            for name, value in x.items():
                detector = self.drift_detectors[name]
                detector.update(value)
                if bool(getattr(detector, "drift_detected", False)):
                    drifted_features.append(name)

            if drifted_features:
                self.drift_events += 1
                self.baseline_status = "ADAPTING"
                self.last_drift_feature = ", ".join(drifted_features)
                self.last_drift_observation = self.observations
                self.healthy_score_window.clear()
            elif self.baseline_status == "ADAPTING":
                if self.last_drift_observation is not None and self.observations - self.last_drift_observation >= 120:
                    self.baseline_status = "STABLE"
                    self._recalibrate_thresholds()
            elif self.healthy_observations % 100 == 0:
                self._recalibrate_thresholds()

        self.last_pattern = pattern
        self.last_raw_anomaly_score = raw_score
        self.last_anomaly_index = anomaly_index
        self.last_prediction = prediction
        self.last_confidence = confidence
        self.last_probabilities = {str(k): round(_safe_float(v), 4) for k, v in probabilities.items()}

        result = {
            "pattern": pattern,
            "anomaly_score": round(anomaly_index, 4),
            "raw_anomaly_score": round(raw_score, 6),
            "suspicious_threshold": round(self.suspicious_threshold, 6),
            "anomaly_threshold": round(self.anomaly_threshold, 6),
            "predicted_incident": prediction,
            "prediction_confidence": round(confidence, 4),
            "probabilities": self.last_probabilities,
            "learning_enabled": bool(learn_healthy),
            "baseline_status": self.baseline_status,
            "observations_learned": self.healthy_observations,
            "confirmed_incidents_learned": self.confirmed_incidents_learned,
            "drift_events": self.drift_events,
            "drifted_features": drifted_features,
            "model": {
                "anomaly_detector": "Half-Space Trees",
                "incident_classifier": "Adaptive Random Forest" if _ARF is not None else "Hoeffding Adaptive Tree",
                "drift_detector": "ADWIN",
            },
        }

        self._last_signature = signature
        self._last_eval_time = now
        self._last_result = dict(result)

        if learn_healthy and self.healthy_observations - self.last_saved_observation >= 50:
            self.save()

        return result

    def learn_verified_incident(self, scenario: str | None, telemetry: dict[str, Any] | None, incident_id: str | None) -> dict[str, Any]:
        label = SCENARIO_LABELS.get(str(scenario))
        if not label or not telemetry:
            return {"learned": False, "reason": "No confirmed scenario label or incident telemetry."}
        if incident_id and incident_id == self.last_confirmed_incident_id:
            return {"learned": False, "reason": "Incident already learned.", "label": label}

        x = normalize_telemetry(telemetry)
        # Repeat a few times so one verified incident has meaningful, but bounded, influence.
        for _ in range(5):
            self.classifier.learn_one(x, label)

        self.confirmed_incidents_learned += 1
        self.last_confirmed_incident_id = incident_id
        self.last_confirmed_label = label
        self.save()
        return {
            "learned": True,
            "confirmed_label": label,
            "incident_id": incident_id,
            "confirmed_incidents_learned": self.confirmed_incidents_learned,
        }

    def status(self) -> dict[str, Any]:
        return {
            "pattern": self.last_pattern,
            "anomaly_score": round(self.last_anomaly_index, 4),
            "raw_anomaly_score": round(self.last_raw_anomaly_score, 6),
            "predicted_incident": self.last_prediction,
            "prediction_confidence": round(self.last_confidence, 4),
            "probabilities": self.last_probabilities,
            "baseline_status": self.baseline_status,
            "observations_learned": self.healthy_observations,
            "confirmed_incidents_learned": self.confirmed_incidents_learned,
            "drift_events": self.drift_events,
            "last_drift_feature": self.last_drift_feature,
            "last_confirmed_label": self.last_confirmed_label,
            "bootstrap_examples": self.bootstrap_examples,
            "model_persistence": str(STATE_PATH),
            "model": {
                "anomaly_detector": "Half-Space Trees",
                "incident_classifier": "Adaptive Random Forest" if _ARF is not None else "Hoeffding Adaptive Tree",
                "drift_detector": "ADWIN",
            },
        }

    def save(self) -> bool:
        state = {
            "anomaly_model": self.anomaly_model,
            "classifier": self.classifier,
            "drift_detectors": self.drift_detectors,
            "observations": self.observations,
            "healthy_observations": self.healthy_observations,
            "confirmed_incidents_learned": self.confirmed_incidents_learned,
            "drift_events": self.drift_events,
            "bootstrap_examples": self.bootstrap_examples,
            "healthy_score_window": list(self.healthy_score_window),
            "suspicious_threshold": self.suspicious_threshold,
            "anomaly_threshold": self.anomaly_threshold,
            "baseline_status": self.baseline_status,
            "last_drift_feature": self.last_drift_feature,
            "last_drift_observation": self.last_drift_observation,
            "last_confirmed_incident_id": self.last_confirmed_incident_id,
            "last_confirmed_label": self.last_confirmed_label,
        }
        tmp = STATE_PATH.with_suffix(".tmp")
        try:
            with tmp.open("wb") as fh:
                pickle.dump(state, fh)
            os.replace(tmp, STATE_PATH)
            self.last_saved_observation = self.healthy_observations
            META_PATH.write_text(json.dumps({
                "observations_learned": self.healthy_observations,
                "confirmed_incidents_learned": self.confirmed_incidents_learned,
                "drift_events": self.drift_events,
                "baseline_status": self.baseline_status,
                "last_confirmed_label": self.last_confirmed_label,
            }, indent=2), encoding="utf-8")
            return True
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    def _load(self) -> bool:
        if not STATE_PATH.exists():
            return False
        try:
            with STATE_PATH.open("rb") as fh:
                state = pickle.load(fh)
            self.anomaly_model = state["anomaly_model"]
            self.classifier = state["classifier"]
            self.drift_detectors = state["drift_detectors"]
            self.observations = int(state.get("observations", 0))
            self.healthy_observations = int(state.get("healthy_observations", 0))
            self.confirmed_incidents_learned = int(state.get("confirmed_incidents_learned", 0))
            self.drift_events = int(state.get("drift_events", 0))
            self.bootstrap_examples = int(state.get("bootstrap_examples", 0))
            self.healthy_score_window = deque(state.get("healthy_score_window", []), maxlen=500)
            self.suspicious_threshold = float(state.get("suspicious_threshold", 0.45))
            self.anomaly_threshold = float(state.get("anomaly_threshold", 0.70))
            self.baseline_status = str(state.get("baseline_status", "STABLE"))
            self.last_drift_feature = state.get("last_drift_feature")
            self.last_drift_observation = state.get("last_drift_observation")
            self.last_confirmed_incident_id = state.get("last_confirmed_incident_id")
            self.last_confirmed_label = state.get("last_confirmed_label")
            self.last_saved_observation = self.healthy_observations
            self.last_pattern = "NORMAL"
            return True
        except Exception:
            return False


runtime = AdaptiveRuntime()
