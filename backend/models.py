from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Service(BaseModel):
    id: str
    name: str
    status: HealthStatus = HealthStatus.HEALTHY
    criticality: str = "MEDIUM"
    metrics: dict[str, float] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    id: str
    timestamp: str
    service: str
    type: str
    severity: str
    message: str
    metric: str
    value: float
    threshold: float


class Incident(BaseModel):
    id: str
    created_at: str
    status: str
    severity: str
    alerts: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    root_cause: str | None = None
    confidence: float = 0.0
    business_impact: dict[str, Any] = Field(default_factory=dict)
