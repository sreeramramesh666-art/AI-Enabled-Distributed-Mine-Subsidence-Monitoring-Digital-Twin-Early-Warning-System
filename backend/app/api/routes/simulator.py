from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.app.simulator.engine import simulator_engine

router = APIRouter(prefix="/simulator", tags=["Simulator Control"])

ALLOWED_SCENARIOS = {
    "baseline",
    "gradual_settlement",
    "accelerating_subsidence",
    "sudden_collapse",
    "vibration_blast",
    "sensor_drift",
    "packet_loss",
    "testrig_baseline",
    "testrig_gradual",
    "testrig_differential",
    "testrig_vibration_only",
    "testrig_disconnect_reconnect",
    "testrig_comm_loss",
    "testrig_return_stable"
}


class SimulatorStartRequest(BaseModel):
    scenario: str = Field(
        "baseline",
        description="baseline, gradual_settlement, accelerating_subsidence, sudden_collapse, vibration_blast, sensor_drift, packet_loss"
    )
    interval_sec: float = Field(2.0, ge=0.5, le=60.0)
    node_count: int = Field(6, ge=1, le=10)
    seed: int = Field(42, ge=0)

    @field_validator("scenario")
    @classmethod
    def validate_scenario_name(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in ALLOWED_SCENARIOS:
            raise ValueError(f"Unknown scenario '{v}'. Allowed scenarios: {', '.join(sorted(ALLOWED_SCENARIOS))}")
        return s


@router.get("/status")
def get_simulator_status():
    return simulator_engine.get_status()


@router.post("/start")
async def start_simulator(req: SimulatorStartRequest):
    return await simulator_engine.start(
        scenario=req.scenario,
        interval_sec=req.interval_sec,
        node_count=req.node_count,
        seed=req.seed
    )


@router.post("/stop")
async def stop_simulator():
    return await simulator_engine.stop()


@router.post("/reset")
def reset_simulator():
    return simulator_engine.reset()
