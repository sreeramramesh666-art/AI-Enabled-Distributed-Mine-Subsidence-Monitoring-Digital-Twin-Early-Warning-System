from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import uuid


class GatewayUnitsMetadata(BaseModel):
    displacement: str = Field("mm", description="Displacement unit (SI: millimetres)")
    tilt: str = Field("deg", description="Tilt angle unit (degrees)")
    velocity: str = Field("mm/hr", description="Deformation velocity unit (mm per hour)")
    vibration: str = Field("m/s2", description="Vibration root-mean-square acceleration unit")
    temperature: str = Field("C", description="Ambient temperature unit (Celsius)")
    crack_width: str = Field("mm", description="Joint / fracture aperture unit (millimetres)")
    battery_voltage: str = Field("V", description="Node battery rail potential (Volts)")
    battery: str = Field("%", description="State-of-charge percentage")


class GatewaySensorReadings(BaseModel):
    displacement_mm: Optional[float] = Field(None, ge=-5000.0, le=5000.0)
    tilt_x_deg: Optional[float] = Field(None, ge=-90.0, le=90.0)
    tilt_y_deg: Optional[float] = Field(None, ge=-90.0, le=90.0)
    vibration_rms_ms2: Optional[float] = Field(None, ge=0.0, le=200.0)
    peak_acceleration_ms2: Optional[float] = Field(None, ge=0.0, le=500.0)
    temperature_c: Optional[float] = Field(None, ge=-50.0, le=100.0)
    crack_width_mm: Optional[float] = Field(None, ge=0.0, le=1000.0)
    battery_voltage_v: Optional[float] = Field(None, ge=0.0, le=30.0)
    battery_pct: Optional[float] = Field(None, ge=0.0, le=100.0)


class GatewayQualityMetadata(BaseModel):
    sensor_status: str = Field("nominal", description="Transducer status: nominal, degraded, calibrating, error")
    rssi_dbm: Optional[int] = Field(None, ge=-150, le=0, description="LoRa / RF signal strength in dBm")
    snr_db: Optional[float] = Field(None, ge=-30.0, le=30.0, description="Signal-to-noise ratio in dB")
    is_physically_bounded: bool = Field(True, description="Physical bounds plausibility flag")
    has_missing_data: bool = Field(False, description="Channel dropout indicator")


class TelemetryIngest(BaseModel):
    event_id: Optional[str] = None
    node_id: str = Field(..., min_length=2, max_length=64)
    gateway_id: Optional[str] = Field(None, max_length=64)
    test_run_id: Optional[str] = Field(None, max_length=64)
    sequence_number: Optional[int] = Field(None, ge=0)
    timestamp: datetime
    data_source: str = Field("rest", max_length=32)
    firmware_version: Optional[str] = Field(None, max_length=32)
    units: Optional[Dict[str, str]] = None

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

    sensor_quality_state: Optional[str] = Field("valid", max_length=32, description="valid, stale, uncalibrated, out_of_range, suspect")
    sensor_quality: Optional[Dict[str, Any]] = None
    calibration_status: Optional[str] = "nominal"
    is_interpolated: bool = False
    raw_metadata: Optional[Dict[str, Any]] = None

    @field_validator("event_id", mode="before")
    @classmethod
    def set_event_id(cls, v):
        if not v:
            return str(uuid.uuid4())
        return str(v)

    @model_validator(mode="before")
    @classmethod
    def unpack_nested_gateway_format(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # If submitted in structured gateway format with "readings" sub-dictionary:
            readings = values.get("readings")
            if isinstance(readings, dict):
                for k, v in readings.items():
                    if k not in values or values[k] is None:
                        values[k] = v
            # If submitted with "quality" sub-dictionary:
            quality = values.get("quality")
            if isinstance(quality, dict) and not values.get("sensor_quality"):
                values["sensor_quality"] = quality
        return values


class GatewayMessagePayload(BaseModel):
    """
    Canonical gateway message format representing aggregated RF radio mesh packets
    forwarded by an edge LoRaWAN/ESP-NOW gateway.
    """
    node_id: str = Field(..., min_length=2, max_length=64)
    gateway_id: Optional[str] = Field(None, max_length=64)
    event_id: Optional[str] = None
    sequence_number: Optional[int] = Field(None, ge=0)
    timestamp: datetime
    firmware_version: Optional[str] = Field(None, max_length=32)
    units: Optional[GatewayUnitsMetadata] = Field(default_factory=GatewayUnitsMetadata)
    readings: GatewaySensorReadings
    quality: Optional[GatewayQualityMetadata] = Field(default_factory=GatewayQualityMetadata)
    raw_metadata: Optional[Dict[str, Any]] = None

    @field_validator("event_id", mode="before")
    @classmethod
    def set_event_id(cls, v):
        if not v:
            return str(uuid.uuid4())
        return str(v)

    def to_telemetry_ingest(self, data_source: str = "gateway_mqtt") -> TelemetryIngest:
        """Convert structured gateway message payload to TelemetryIngest."""
        q_dict = self.quality.model_dump() if self.quality else None
        u_dict = self.units.model_dump() if self.units else None
        return TelemetryIngest(
            event_id=self.event_id,
            node_id=self.node_id,
            gateway_id=self.gateway_id,
            sequence_number=self.sequence_number,
            timestamp=self.timestamp,
            data_source=data_source,
            firmware_version=self.firmware_version,
            units=u_dict,
            displacement_mm=self.readings.displacement_mm,
            tilt_x_deg=self.readings.tilt_x_deg,
            tilt_y_deg=self.readings.tilt_y_deg,
            vibration_rms_ms2=self.readings.vibration_rms_ms2,
            peak_acceleration_ms2=self.readings.peak_acceleration_ms2,
            temperature_c=self.readings.temperature_c,
            crack_width_mm=self.readings.crack_width_mm,
            battery_voltage_v=self.readings.battery_voltage_v,
            battery_pct=self.readings.battery_pct,
            sensor_quality=q_dict,
            raw_metadata=self.raw_metadata
        )


class TelemetryBatchIngest(BaseModel):
    records: List[TelemetryIngest] = Field(..., min_length=1, max_length=1000)
    atomic: bool = Field(True, description="When true, any validation or foreign key failure rolls back the entire batch.")


class GatewayReplayPayload(BaseModel):
    """
    Store-and-forward batch replay format uploaded by an edge gateway
    after temporary network connectivity recovery.
    """
    gateway_id: str = Field(..., min_length=2, max_length=64)
    batch_id: str = Field(..., min_length=2, max_length=64)
    transmitted_at: datetime
    buffered_count: int = Field(..., ge=1, le=2000)
    is_replay: bool = Field(True)
    records: List[Union[GatewayMessagePayload, TelemetryIngest]] = Field(..., min_length=1)

    @field_validator("batch_id", mode="before")
    @classmethod
    def set_batch_id(cls, v):
        if not v:
            return str(uuid.uuid4())
        return str(v)


class GatewayReplayResponse(BaseModel):
    gateway_id: str
    batch_id: str
    received_count: int
    accepted_count: int
    duplicates_skipped: int
    rejected_count: int
    status: str  # COMPLETED, PARTIAL, REJECTED
    errors: List[str] = []


class TelemetryResponse(BaseModel):
    id: int
    event_id: str
    node_id: str
    test_run_id: Optional[str] = None
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

    baseline_relative_displacement_mm: Optional[float] = None
    baseline_relative_tilt_deg: Optional[float] = None
    sensor_quality_state: str = "valid"
    sensor_quality: Optional[Dict[str, Any]] = None
    calibration_status: Optional[str] = None
    is_interpolated: bool = False

    model_config = ConfigDict(from_attributes=True)


class TelemetryBatchResponse(BaseModel):
    ingested_count: int
    duplicates_skipped: int
    errors: List[str] = []


class TelemetryQuery(BaseModel):
    node_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time:
            if self.start_time > self.end_time:
                raise ValueError("start_time must be earlier than or equal to end_time")
        return self
