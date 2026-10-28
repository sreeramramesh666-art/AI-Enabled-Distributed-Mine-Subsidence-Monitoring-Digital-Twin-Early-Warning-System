from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class SensorNodeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation_m: Optional[float] = Field(None, ge=-1000.0, le=9000.0)
    node_type: str = Field("multiparameter", max_length=64)
    installation_location: Optional[str] = Field(None, max_length=256)
    mine_panel: Optional[str] = Field(None, max_length=64, description="Associated mine panel, e.g. Panel-North-01")
    depth_m: Optional[float] = Field(None, ge=0.0, le=3000.0, description="Depth below surface in metres")
    extraction_method: Optional[str] = Field(None, max_length=64, description="Mining extraction method, e.g. Longwall, Bord and Pillar")
    geological_context: Optional[str] = Field(None, max_length=256, description="Geological overburden and fault proximity context")
    sampling_interval_sec: float = Field(5.0, ge=0.5, le=3600.0, description="Nominal sampling interval in seconds")
    last_calibration_date: Optional[datetime] = None
    calibration_status: str = Field("nominal", max_length=32, description="nominal, calibrating, degraded, suspect")
    firmware_version: Optional[str] = Field("v1.0.0", max_length=32)
    is_enabled: bool = True


class SensorNodeCreate(SensorNodeBase):
    node_id: str = Field(..., min_length=2, max_length=64)

    @field_validator("node_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v_stripped = v.strip()
        if not re.match(r"^[A-Za-z0-9_\-\.]{2,64}$", v_stripped):
            raise ValueError("node_id must be 2-64 alphanumeric characters, underscores, dashes or dots")
        return v_stripped


class SensorNodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    elevation_m: Optional[float] = Field(None, ge=-1000.0, le=9000.0)
    node_type: Optional[str] = Field(None, max_length=64)
    installation_location: Optional[str] = Field(None, max_length=256)
    mine_panel: Optional[str] = Field(None, max_length=64)
    depth_m: Optional[float] = Field(None, ge=0.0, le=3000.0)
    extraction_method: Optional[str] = Field(None, max_length=64)
    geological_context: Optional[str] = Field(None, max_length=256)
    sampling_interval_sec: Optional[float] = Field(None, ge=0.5, le=3600.0)
    last_calibration_date: Optional[datetime] = None
    calibration_status: Optional[str] = Field(None, max_length=32)
    firmware_version: Optional[str] = Field(None, max_length=32)
    is_enabled: Optional[bool] = None


class SensorNodeResponse(SensorNodeBase):
    node_id: str
    last_seen: Optional[datetime] = None
    battery_pct: Optional[float] = None
    connectivity_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorNodeList(BaseModel):
    total: int
    items: List[SensorNodeResponse]


class NodeBaselineResponse(BaseModel):
    node_id: str
    calculation_period_start: Optional[datetime] = None
    calculation_period_end: Optional[datetime] = None
    sample_count: int
    displacement_mean: Optional[float] = None
    displacement_std: Optional[float] = None
    tilt_x_mean: Optional[float] = None
    tilt_x_std: Optional[float] = None
    tilt_y_mean: Optional[float] = None
    tilt_y_std: Optional[float] = None
    temperature_mean: Optional[float] = None
    is_valid: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeBaselineRecalculate(BaseModel):
    period_hours: float = Field(72.0, ge=1.0, le=2160.0, description="Calculation window in hours")
