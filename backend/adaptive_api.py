from __future__ import annotations

from fastapi import APIRouter

from adaptive_runtime import runtime
from simulator import simulator

router = APIRouter(prefix="/api/adaptive", tags=["Adaptive Monitoring"])


@router.get("/status")
def adaptive_status() -> dict:
    return runtime.status()


@router.get("/live")
def adaptive_live() -> dict:
    snapshot = simulator.snapshot()
    return {
        "status": "ok",
        "source": "astraguard-live-telemetry",
        "telemetry": snapshot["metrics"],
        "adaptive_monitoring": snapshot.get("adaptive_monitoring", runtime.status()),
    }


@router.post("/save")
def save_models() -> dict:
    return {"saved": runtime.save(), "status": runtime.status()}
