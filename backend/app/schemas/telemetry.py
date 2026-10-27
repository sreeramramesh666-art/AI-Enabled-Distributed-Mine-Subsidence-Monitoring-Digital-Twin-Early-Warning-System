from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class TelemetryIngest(BaseModel):
    event_id: Optional[str] = None
    node_id: str = Field(..., min_length=2, max_length=64)
    sequence_number: Optional[int] = Field(None, ge=0)
    timestamp: datetime
    data_source: str = Field("rest", max_length=32)

    # Physical measurements in SI units
    displacement_mm: Optional[float] = Field(None, ge=-5000.0, le=5000.0)
    tilt_x_deg: Optional[float] = Field(None, ge=-90.0, le=90.0)
    tilt_y_deg: Optional[float] = Field(None, ge=-90.0, le=90.0)
    vibration_rms_ms2: Optional[float] = Field(None, ge=0.0, le=200.0)
    peak_acceleration_ms2: Optional[float] = Field(None, ge=0.0, le=500.0)
    temperature_c: Optional[float] = Field(None, ge=-50.0, le=100.0)
    crack_width_mm: Optional[float] = Field(None, ge=0.0, le=1000.0)
    battery_voltage_v: Optional[float] = Field(None, ge=0.0, le=30.0)
    battery_pct: Optional[float] = Field(None, ge=0.0, le=100.0)

    sensor_quality: Optional[Dict[str, Any]] = None
    calibration_status: Optional[str] = "nominal"
    raw_metadata: Optional[Dict[str, Any]] = None

    @field_validator("event_id", mode="before")
    @classmethod
    def set_event_id(cls, v):
        if not v:
            return str(uuid.uuid4())
        return str(v)


class TelemetryBatchIngest(BaseModel):
    records: List[TelemetryIngest] = Field(..., min_length=1, max_length=1000)


class TelemetryResponse(BaseModel):
    id: int
    event_id: str
    node_id: str
    sequence_number: Optional[int] = None
    timestamp: datetime
    received_at: datetime
    data_source: str

    displacement_mm: Optional[float] = None
    tilt_x_deg: Optional[float] = None
    tilt_y_deg: Optional[float] = None
    vector_tilt_deg: Optional[float] = None
    velocity_mm_hr: Optional[float] = None
    acceleration_mm_hr2: Optional[float] = None
    vibration_rms_ms2: Optional[float] = None
    peak_acceleration_ms2: Optional[float] = None
    temperature_c: Optional[float] = None
    crack_width_mm: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    battery_pct: Optional[float] = None
    sensor_quality: Optional[Dict[str, Any]] = None
    calibration_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TelemetryBatchResponse(BaseModel):
    ingested_count: int
    duplicates_skipped: int
    errors: List[str] = []
