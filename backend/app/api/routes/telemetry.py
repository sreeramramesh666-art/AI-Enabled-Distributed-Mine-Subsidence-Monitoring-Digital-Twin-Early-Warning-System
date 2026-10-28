from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.telemetry import (
    TelemetryIngest, TelemetryResponse, TelemetryBatchIngest, TelemetryBatchResponse,
    GatewayMessagePayload, GatewayReplayPayload, GatewayReplayResponse
)
from backend.app.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["Telemetry Ingestion"])


@router.post("", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_telemetry(telemetry_in: TelemetryIngest, db: Session = Depends(get_db)):
    record, error, is_dup = await TelemetryService.process_single_telemetry(db=db, telemetry=telemetry_in)
    if is_dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate observation with event_id '{telemetry_in.event_id}' or sequence '{telemetry_in.sequence_number}' already ingested."
        )
    if error:
        if "not registered" in error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        if "disabled" in error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error)
    return record


@router.post("/batch", response_model=TelemetryBatchResponse, status_code=status.HTTP_200_OK)
async def ingest_telemetry_batch(batch_in: TelemetryBatchIngest, db: Session = Depends(get_db)):
    res = await TelemetryService.process_batch_telemetry(db=db, batch=batch_in)
    if batch_in.atomic and res.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Atomic batch ingestion failed; all records rolled back.",
                "errors": res.errors
            }
        )
    return res


@router.post("/replay", response_model=GatewayReplayResponse, status_code=status.HTTP_200_OK)
async def ingest_gateway_replay(replay_in: GatewayReplayPayload, db: Session = Depends(get_db)):
    """
    Ingest buffered telemetry records replayed by an edge wireless gateway
    following temporary network partition or radio link recovery.
    Safe against duplicate batch submissions.
    """
    res = await TelemetryService.process_gateway_replay(db=db, replay=replay_in)
    return res


@router.get("/gateway-format")
def get_gateway_message_format() -> Dict[str, Any]:
    """
    Returns canonical schema and documentation for edge gateway firmware developers.
    Specifies SI units, required identifiers, and store-and-forward batch replay envelopes.
    """
    return {
        "description": "MineGuard-AI Canonical Edge Gateway Message Specification (SIH26025)",
        "transport_protocols": ["HTTP REST", "MQTT QoS 1"],
        "mqtt_topics": {
            "telemetry_live": "mineguard/gateways/{gateway_id}/telemetry",
            "node_direct": "mineguard/nodes/{node_id}/telemetry",
            "batch_replay": "mineguard/gateways/{gateway_id}/replay"
        },
        "si_units": {
            "displacement": "mm (millimetres)",
            "tilt": "deg (degrees)",
            "velocity": "mm/hr (millimetres per hour)",
            "acceleration": "mm/hr2 (millimetres per hour squared)",
            "vibration_rms": "m/s2 (metres per second squared)",
            "temperature": "C (degrees Celsius)",
            "battery_voltage": "V (Volts)",
            "battery_pct": "% (percentage)"
        },
        "sample_single_payload": {
            "gateway_id": "GW-BENCH-C-01",
            "node_id": "NODE-PIT-NORTH-01",
            "event_id": "c7b3d8a1-4321-4f1b-8712-4217bb654321",
            "sequence_number": 1042,
            "timestamp": "2026-10-28T06:30:00Z",
            "firmware_version": "v1.2.0",
            "units": {
                "displacement": "mm",
                "tilt": "deg",
                "velocity": "mm/hr",
                "vibration": "m/s2",
                "temperature": "C",
                "battery": "%"
            },
            "readings": {
                "displacement_mm": 12.45,
                "tilt_x_deg": 0.42,
                "tilt_y_deg": -0.15,
                "vibration_rms_ms2": 0.08,
                "peak_acceleration_ms2": 0.12,
                "temperature_c": 26.5,
                "crack_width_mm": 2.1,
                "battery_voltage_v": 3.65,
                "battery_pct": 88.0
            },
            "quality": {
                "sensor_status": "nominal",
                "rssi_dbm": -74,
                "snr_db": 9.2,
                "is_physically_bounded": True,
                "has_missing_data": False
            },
            "raw_metadata": {
                "radio_mesh_hops": 2,
                "gateway_received_at": "2026-10-28T06:30:01Z"
            }
        },
        "sample_replay_envelope": {
            "gateway_id": "GW-BENCH-C-01",
            "batch_id": "550e8400-e29b-41d4-a716-446655440000",
            "transmitted_at": "2026-10-28T06:45:00Z",
            "buffered_count": 25,
            "is_replay": True,
            "records": ["<array of sample_single_payload>"]
        }
    }
