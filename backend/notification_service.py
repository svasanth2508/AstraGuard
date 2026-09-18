from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from threading import RLock
from typing import Any


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class NotificationService:
    """Optional SMTP notifications with an in-app notification log when SMTP is not configured."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sent_keys: set[str] = set()
        self._events: list[dict[str, Any]] = []

    def config(self) -> dict[str, Any]:
        enabled = _truthy(os.getenv("ASTRA_EMAIL_ENABLED"))
        host = os.getenv("ASTRA_SMTP_HOST", "")
        username = os.getenv("ASTRA_SMTP_USERNAME", "")
        admin = os.getenv("ASTRA_ADMIN_EMAIL", "")
        sender = os.getenv("ASTRA_FROM_EMAIL", username)
        return {
            "enabled": enabled,
            "configured": bool(enabled and host and admin and sender),
            "host": host or None,
            "port": int(os.getenv("ASTRA_SMTP_PORT", "587")),
            "username": username or None,
            "admin_email": admin or None,
            "from_email": sender or None,
            "use_tls": _truthy(os.getenv("ASTRA_SMTP_TLS", "true")),
        }

    def history(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events[-limit:])

    def _record(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._events.append(event)
            self._events = self._events[-100:]
        return event

    def send_once(self, key: str, subject: str, body: str, kind: str, incident_id: str | None) -> dict[str, Any]:
        with self._lock:
            if key in self._sent_keys:
                existing = next((e for e in reversed(self._events) if e.get("key") == key), None)
                return existing or {"key": key, "status": "DUPLICATE_SKIPPED"}
            self._sent_keys.add(key)

        cfg = self.config()
        event = {
            "key": key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "incident_id": incident_id,
            "subject": subject,
            "recipient": cfg.get("admin_email"),
            "status": "IN_APP_ONLY",
            "detail": "SMTP disabled or not configured; notification retained in AstraGuard.",
        }

        if not cfg["configured"]:
            return self._record(event)

        password = os.getenv("ASTRA_SMTP_PASSWORD", "")
        if not password:
            event["status"] = "EMAIL_FAILED"
            event["detail"] = "ASTRA_SMTP_PASSWORD is missing."
            return self._record(event)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = str(cfg["from_email"])
        msg["To"] = str(cfg["admin_email"])
        msg.set_content(body)

        try:
            with smtplib.SMTP(str(cfg["host"]), int(cfg["port"]), timeout=5) as smtp:
                smtp.ehlo()
                if cfg["use_tls"]:
                    smtp.starttls()
                    smtp.ehlo()
                if cfg.get("username"):
                    smtp.login(str(cfg["username"]), password)
                smtp.send_message(msg)
            event["status"] = "EMAIL_SENT"
            event["detail"] = "Administrator email sent successfully."
        except Exception as exc:  # demo system: surface transport failure without breaking incident processing
            event["status"] = "EMAIL_FAILED"
            event["detail"] = f"Email transport failed: {exc}"

        return self._record(event)

    def incident_detected(self, incident: dict[str, Any]) -> dict[str, Any]:
        incident_id = incident.get("id")
        subject = f"[AstraGuard] {incident.get('severity', 'HIGH')} incident detected — {incident_id}"
        body = (
            f"AstraGuard detected and correlated an incident.\n\n"
            f"Incident: {incident_id}\n"
            f"Scenario: {incident.get('title')}\n"
            f"Severity: {incident.get('severity')}\n"
            f"Root cause: {incident.get('root_cause')}\n"
            f"Confidence: {incident.get('confidence')}%\n"
            f"Affected services: {', '.join(incident.get('affected_services', []))}\n"
            f"Remediation policy: {((incident.get('remediation') or {}).get('autonomy') or {}).get('state', 'Pending')}\n"
        )
        return self.send_once(f"{incident_id}:detected", subject, body, "INCIDENT_DETECTED", incident_id)

    def approval_required(self, incident: dict[str, Any]) -> dict[str, Any]:
        incident_id = incident.get("id")
        action = ((incident.get("remediation") or {}).get("recommended_action") or {}).get("action")
        subject = f"[AstraGuard] Approval required — {incident_id}"
        body = f"Incident {incident_id} requires human approval.\n\nRecommended action: {action}\n"
        return self.send_once(f"{incident_id}:approval", subject, body, "APPROVAL_REQUIRED", incident_id)

    def recovery_verified(self, incident_id: str, action: str | None) -> dict[str, Any]:
        subject = f"[AstraGuard] Recovery verified — {incident_id}"
        body = f"Recovery has been verified for {incident_id}.\n\nRemediation: {action or 'N/A'}\nStatus: RESOLVED\n"
        return self.send_once(f"{incident_id}:recovered", subject, body, "RECOVERY_VERIFIED", incident_id)

    def recovery_failed(self, incident_id: str, rollback_action: str | None) -> dict[str, Any]:
        subject = f"[AstraGuard] Recovery failed / rollback started — {incident_id}"
        body = f"Recovery verification failed for {incident_id}.\n\nRollback: {rollback_action or 'Configured rollback'}\nIncident remains open.\n"
        return self.send_once(f"{incident_id}:failed", subject, body, "RECOVERY_FAILED", incident_id)


notifier = NotificationService()
