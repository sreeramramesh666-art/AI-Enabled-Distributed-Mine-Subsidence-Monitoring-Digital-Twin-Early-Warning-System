from typing import Optional
from pydantic import BaseModel, Field, model_validator


class SettingsUpdate(BaseModel):
    TILT_WARNING_DEG: Optional[float] = Field(None, ge=0.1, le=80.0)
    TILT_CRITICAL_DEG: Optional[float] = Field(None, ge=0.2, le=90.0)
    DISPLACEMENT_WARNING_MM: Optional[float] = Field(None, ge=0.5, le=4000.0)
    DISPLACEMENT_CRITICAL_MM: Optional[float] = Field(None, ge=1.0, le=5000.0)
    RATE_WARNING_MM_HR: Optional[float] = Field(None, ge=0.1, le=500.0)
    RATE_CRITICAL_MM_HR: Optional[float] = Field(None, ge=0.2, le=1000.0)
    ACCEL_WARNING_MM_HR2: Optional[float] = Field(None, ge=0.01, le=200.0)
    VIBRATION_WARNING_MS2: Optional[float] = Field(None, ge=0.1, le=100.0)
    VIBRATION_CRITICAL_MS2: Optional[float] = Field(None, ge=0.2, le=200.0)
    BATTERY_LOW_PCT: Optional[float] = Field(None, ge=1.0, le=50.0)
    STALE_DATA_TIMEOUT_SEC: Optional[int] = Field(None, ge=10, le=86400)

    @model_validator(mode="after")
    def validate_hierarchy(self):
        if self.TILT_WARNING_DEG is not None and self.TILT_CRITICAL_DEG is not None:
            if self.TILT_WARNING_DEG >= self.TILT_CRITICAL_DEG:
                raise ValueError("TILT_WARNING_DEG must be less than TILT_CRITICAL_DEG")

        if self.DISPLACEMENT_WARNING_MM is not None and self.DISPLACEMENT_CRITICAL_MM is not None:
            if self.DISPLACEMENT_WARNING_MM >= self.DISPLACEMENT_CRITICAL_MM:
                raise ValueError("DISPLACEMENT_WARNING_MM must be less than DISPLACEMENT_CRITICAL_MM")

        if self.RATE_WARNING_MM_HR is not None and self.RATE_CRITICAL_MM_HR is not None:
            if self.RATE_WARNING_MM_HR >= self.RATE_CRITICAL_MM_HR:
                raise ValueError("RATE_WARNING_MM_HR must be less than RATE_CRITICAL_MM_HR")

        if self.VIBRATION_WARNING_MS2 is not None and self.VIBRATION_CRITICAL_MS2 is not None:
            if self.VIBRATION_WARNING_MS2 >= self.VIBRATION_CRITICAL_MS2:
                raise ValueError("VIBRATION_WARNING_MS2 must be less than VIBRATION_CRITICAL_MS2")

        return self


class SettingsResponse(BaseModel):
    tilt_warning_deg: float
    tilt_critical_deg: float
    displacement_warning_mm: float
    displacement_critical_mm: float
    rate_warning_mm_hr: float
    rate_critical_mm_hr: float
    accel_warning_mm_hr2: float
    vibration_warning_ms2: float
    vibration_critical_ms2: float
    battery_low_pct: float
    stale_data_timeout_sec: int
    mqtt_enabled: bool
    environment: str
    is_demonstration_config: bool = True

