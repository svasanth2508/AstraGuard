from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'astraguard.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class IncidentRecord(Base):
    __tablename__ = "incident_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    root_cause: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remediation_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recovery_successful: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fingerprint_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    alert_types_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    affected_services_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def max_incident_sequence() -> int:
    init_db()
    with SessionLocal() as session:
        value = session.execute(select(IncidentRecord.sequence).order_by(IncidentRecord.sequence.desc()).limit(1)).scalar_one_or_none()
        return int(value or 0)


def save_audit_event(event_key: str, event: dict[str, Any]) -> None:
    init_db()
    with SessionLocal() as session:
        existing = session.execute(select(AuditRecord.id).where(AuditRecord.event_key == event_key)).scalar_one_or_none()
        if existing is not None:
            return
        session.add(AuditRecord(
            incident_id=event.get("incident_id"),
            event_key=event_key,
            timestamp=str(event.get("timestamp") or ""),
            event_type=str(event.get("event_type") or "EVENT"),
            message=str(event.get("message") or ""),
            details_json=json.dumps(event.get("details") or {}, ensure_ascii=False),
        ))
        session.commit()


def upsert_incident(incident: dict[str, Any], alert_types: list[str], fingerprint: list[str]) -> None:
    init_db()
    incident_id = str(incident["id"])
    try:
        sequence = int(incident_id.split("-")[-1])
    except (ValueError, IndexError):
        sequence = 0
    remediation = incident.get("remediation") or {}
    action = (remediation.get("recommended_action") or {}).get("action")
    with SessionLocal() as session:
        record = session.get(IncidentRecord, incident_id)
        if record is None:
            record = IncidentRecord(
                id=incident_id,
                sequence=sequence,
                created_at=str(incident.get("created_at") or ""),
                status=str(incident.get("status") or "INVESTIGATING"),
                severity=str(incident.get("severity") or "HIGH"),
                title=str(incident.get("title") or "Incident"),
            )
            session.add(record)
        record.created_at = str(incident.get("created_at") or record.created_at)
        record.resolved_at = incident.get("resolved_at")
        record.status = str(incident.get("status") or record.status)
        record.scenario = incident.get("scenario")
        record.severity = str(incident.get("severity") or record.severity)
        record.title = str(incident.get("title") or record.title)
        record.root_cause = incident.get("root_cause")
        record.confidence = int(round(float(incident.get("confidence") or 0)))
        record.remediation_action = action
        record.recovery_successful = 1 if incident.get("status") == "RESOLVED" else 0
        record.fingerprint_json = json.dumps(sorted(set(fingerprint)), ensure_ascii=False)
        record.alert_types_json = json.dumps(sorted(set(alert_types)), ensure_ascii=False)
        record.affected_services_json = json.dumps(incident.get("affected_services") or [], ensure_ascii=False)
        record.payload_json = json.dumps(incident, ensure_ascii=False, default=str)
        record.updated_at = datetime.now(timezone.utc)
        session.commit()


def list_incidents(limit: int = 20, completed_only: bool = False) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        stmt = select(IncidentRecord)
        if completed_only:
            stmt = stmt.where(IncidentRecord.status == "RESOLVED")
        rows = session.execute(stmt.order_by(IncidentRecord.sequence.desc()).limit(limit)).scalars().all()
        return [
            {
                "id": row.id,
                "sequence": row.sequence,
                "created_at": row.created_at,
                "resolved_at": row.resolved_at,
                "status": row.status,
                "scenario": row.scenario,
                "severity": row.severity,
                "title": row.title,
                "root_cause": row.root_cause,
                "confidence": row.confidence,
                "remediation_action": row.remediation_action,
                "recovery_successful": bool(row.recovery_successful),
                "fingerprint": _loads(row.fingerprint_json, []),
                "alert_types": _loads(row.alert_types_json, []),
                "affected_services": _loads(row.affected_services_json, []),
            }
            for row in rows
        ]


def list_audit_events(incident_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with SessionLocal() as session:
        stmt = select(AuditRecord)
        if incident_id:
            stmt = stmt.where(AuditRecord.incident_id == incident_id)
        rows = session.execute(stmt.order_by(AuditRecord.id.desc()).limit(limit)).scalars().all()
        rows.reverse()
        return [
            {
                "timestamp": row.timestamp,
                "incident_id": row.incident_id,
                "event_type": row.event_type,
                "message": row.message,
                "details": _loads(row.details_json, {}),
            }
            for row in rows
        ]
