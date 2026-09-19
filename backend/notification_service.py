from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import RLock
from typing import Any

import resend


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class NotificationService:
    """
    AstraGuard notification service.

    Uses Resend HTTP API for email delivery.
    Falls back to in-app notification history if
    email delivery is disabled or not configured.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._sent_keys: set[str] = set()
        self._events: list[dict[str, Any]] = []

    def config(self) -> dict[str, Any]:
        enabled = _truthy(
            os.getenv("ASTRA_EMAIL_ENABLED")
        )

        api_key = os.getenv(
            "RESEND_API_KEY",
            "",
        )

        admin_email = os.getenv(
            "ASTRA_ADMIN_EMAIL",
            "",
        )

        from_email = os.getenv(
            "ASTRA_FROM_EMAIL",
            "AstraGuard <onboarding@resend.dev>",
        )

        configured = bool(
            enabled
            and api_key
            and admin_email
            and from_email
        )

        return {
            "enabled": enabled,
            "configured": configured,
            "provider": "Resend",
            "admin_email": admin_email or None,
            "from_email": from_email or None,
        }

    def history(
        self,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return list(
                self._events[-limit:]
            )

    def _record(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            self._events.append(event)

            self._events = (
                self._events[-100:]
            )

        return event

    def send_once(
        self,
        key: str,
        subject: str,
        body: str,
        kind: str,
        incident_id: str | None,
    ) -> dict[str, Any]:

        with self._lock:

            if key in self._sent_keys:

                existing = next(
                    (
                        event
                        for event
                        in reversed(
                            self._events
                        )
                        if event.get("key")
                        == key
                    ),
                    None,
                )

                return (
                    existing
                    or {
                        "key": key,
                        "status":
                            "DUPLICATE_SKIPPED",
                    }
                )

            self._sent_keys.add(key)

        cfg = self.config()

        event = {
            "key": key,
            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "kind": kind,

            "incident_id":
                incident_id,

            "subject":
                subject,

            "recipient":
                cfg.get(
                    "admin_email"
                ),

            "provider":
                "Resend",

            "status":
                "IN_APP_ONLY",

            "detail":
                (
                    "Email disabled or "
                    "Resend not configured."
                ),
        }

        if not cfg["configured"]:
            return self._record(
                event
            )

        api_key = os.getenv(
            "RESEND_API_KEY",
            "",
        )

        resend.api_key = api_key

        try:

            response = (
                resend.Emails.send(
                    {
                        "from":
                            str(
                                cfg[
                                    "from_email"
                                ]
                            ),

                        "to": [
                            str(
                                cfg[
                                    "admin_email"
                                ]
                            )
                        ],

                        "subject":
                            subject,

                        "text":
                            body,
                    }
                )
            )

            email_id = None

            if isinstance(
                response,
                dict,
            ):
                email_id = (
                    response.get(
                        "id"
                    )
                )

            else:
                email_id = getattr(
                    response,
                    "id",
                    None,
                )

            event[
                "status"
            ] = "EMAIL_SENT"

            event[
                "detail"
            ] = (
                "Administrator email "
                "sent successfully "
                "through Resend."
            )

            event[
                "email_id"
            ] = email_id

        except Exception as exc:

            event[
                "status"
            ] = "EMAIL_FAILED"

            event[
                "detail"
            ] = (
                f"Resend API failed: "
                f"{exc}"
            )

        return self._record(
            event
        )

    def incident_detected(
        self,
        incident: dict[str, Any],
    ) -> dict[str, Any]:

        incident_id = (
            incident.get("id")
        )

        severity = (
            incident.get(
                "severity",
                "HIGH",
            )
        )

        subject = (
            f"[AstraGuard] "
            f"{severity} incident "
            f"detected — "
            f"{incident_id}"
        )

        body = (
            "AstraGuard detected "
            "and correlated an incident."
            "\n\n"
            f"Incident: "
            f"{incident_id}\n"
            f"Scenario: "
            f"{incident.get('title')}\n"
            f"Severity: "
            f"{severity}\n"
            f"Root cause: "
            f"{incident.get('root_cause')}\n"
            f"Confidence: "
            f"{incident.get('confidence')}%\n"
            f"Affected services: "
            f"{', '.join(incident.get('affected_services', []))}\n"
        )

        return self.send_once(
            key=(
                f"{incident_id}:detected"
            ),
            subject=subject,
            body=body,
            kind="INCIDENT_DETECTED",
            incident_id=incident_id,
        )

    def approval_required(
        self,
        incident: dict[str, Any],
    ) -> dict[str, Any]:

        incident_id = (
            incident.get("id")
        )

        remediation = (
            incident.get(
                "remediation"
            )
            or {}
        )

        recommended = (
            remediation.get(
                "recommended_action"
            )
            or {}
        )

        action = (
            recommended.get(
                "action"
            )
        )

        subject = (
            "[AstraGuard] "
            "Approval required — "
            f"{incident_id}"
        )

        body = (
            f"Incident "
            f"{incident_id} "
            "requires human approval."
            "\n\n"
            f"Recommended action: "
            f"{action or 'N/A'}\n"
        )

        return self.send_once(
            key=(
                f"{incident_id}:approval"
            ),
            subject=subject,
            body=body,
            kind="APPROVAL_REQUIRED",
            incident_id=incident_id,
        )

    def recovery_verified(
        self,
        incident_id: str,
        action: str | None,
    ) -> dict[str, Any]:

        subject = (
            "[AstraGuard] "
            "Recovery verified — "
            f"{incident_id}"
        )

        body = (
            f"Recovery has been "
            f"verified for "
            f"{incident_id}."
            "\n\n"
            f"Remediation: "
            f"{action or 'N/A'}\n"
            "Status: RESOLVED\n"
        )

        return self.send_once(
            key=(
                f"{incident_id}:recovered"
            ),
            subject=subject,
            body=body,
            kind="RECOVERY_VERIFIED",
            incident_id=incident_id,
        )

    def recovery_failed(
        self,
        incident_id: str,
        rollback_action:
            str | None,
    ) -> dict[str, Any]:

        subject = (
            "[AstraGuard] "
            "Recovery failed / "
            "rollback started — "
            f"{incident_id}"
        )

        body = (
            "Recovery verification "
            f"failed for "
            f"{incident_id}."
            "\n\n"
            f"Rollback: "
            f"{rollback_action or 'Configured rollback'}\n"
            "Incident remains open.\n"
        )

        return self.send_once(
            key=(
                f"{incident_id}:failed"
            ),
            subject=subject,
            body=body,
            kind="RECOVERY_FAILED",
            incident_id=incident_id,
        )


notifier = NotificationService()
