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
    firmware_version: Optional[str] = Field("v1.0.0", max_length=32)
    is_enabled: bool = True


class SensorNodeCreate(SensorNodeBase):
    node_id: str = Field(..., min_length=2, max_length=64)

    @field_validator("node_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-\.]{2,64}$", v):
            raise ValueError("node_id must be 2-64 alphanumeric characters, underscores, dashes or dots")
        return v.strip()


class SensorNodeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    elevation_m: Optional[float] = Field(None, ge=-1000.0, le=9000.0)
    node_type: Optional[str] = None
    installation_location: Optional[str] = None
    firmware_version: Optional[str] = None
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
