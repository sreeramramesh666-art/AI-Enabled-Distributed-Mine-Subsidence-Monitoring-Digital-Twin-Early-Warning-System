import math
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from backend.app.schemas.telemetry import TelemetryIngest


# Physical plausibility limits for mining sensors
BOUNDS = {
    "displacement_mm": (-5000.0, 5000.0),
    "tilt_x_deg": (-90.0, 90.0),
    "tilt_y_deg": (-90.0, 90.0),
    "vibration_rms_ms2": (0.0, 200.0),
    "peak_acceleration_ms2": (0.0, 500.0),
    "temperature_c": (-50.0, 100.0),
    "crack_width_mm": (0.0, 1000.0),
    "battery_pct": (0.0, 100.0),
    "battery_voltage_v": (0.0, 30.0),
}


def validate_physical_measurements(telemetry: TelemetryIngest) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Validate that telemetry measurements fall within physically credible bounds.
    Does NOT mutate values; flags out-of-bound errors or quality indicators.
    """
    quality: Dict[str, Any] = telemetry.sensor_quality.copy() if telemetry.sensor_quality else {}
    quality["has_missing_data"] = False
    quality["anomalous_reading_detected"] = False

    # Check future timestamps (allowing 5 minute clock drift maximum)
    now_utc = datetime.now(timezone.utc)
    # Ensure telemetry timestamp is timezone-aware
    ts = telemetry.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    if (ts - now_utc).total_seconds() > 300:
        return False, "Measurement timestamp is in the future beyond acceptable clock drift", quality

    # Check physical plausibility
    for field, (low, high) in BOUNDS.items():
        val = getattr(telemetry, field, None)
        if val is not None:
            if math.isnan(val) or math.isinf(val):
                return False, f"Field {field} contains NaN or Infinite value", quality
            if not (low <= val <= high):
                return False, f"Field {field} value {val} is outside physically plausible limits [{low}, {high}]", quality
            quality[f"{field}_valid"] = True
        else:
            quality["has_missing_data"] = True

    return True, None, quality

