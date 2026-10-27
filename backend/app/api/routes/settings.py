from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import SystemSetting, AuditEvent

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("")
def get_system_settings(db: Session = Depends(get_db)):
    """Return effective thresholds and configuration."""
    overrides = {s.key: s.value for s in db.query(SystemSetting).all()}

    return {
        "tilt_warning_deg": overrides.get("TILT_WARNING_DEG", settings.TILT_WARNING_DEG),
        "tilt_critical_deg": overrides.get("TILT_CRITICAL_DEG", settings.TILT_CRITICAL_DEG),
        "displacement_warning_mm": overrides.get("DISPLACEMENT_WARNING_MM", settings.DISPLACEMENT_WARNING_MM),
        "displacement_critical_mm": overrides.get("DISPLACEMENT_CRITICAL_MM", settings.DISPLACEMENT_CRITICAL_MM),
        "rate_warning_mm_hr": overrides.get("RATE_WARNING_MM_HR", settings.RATE_WARNING_MM_HR),
        "rate_critical_mm_hr": overrides.get("RATE_CRITICAL_MM_HR", settings.RATE_CRITICAL_MM_HR),
        "accel_warning_mm_hr2": overrides.get("ACCEL_WARNING_MM_HR2", settings.ACCEL_WARNING_MM_HR2),
        "vibration_warning_ms2": overrides.get("VIBRATION_WARNING_MS2", settings.VIBRATION_WARNING_MS2),
        "vibration_critical_ms2": overrides.get("VIBRATION_CRITICAL_MS2", settings.VIBRATION_CRITICAL_MS2),
        "battery_low_pct": overrides.get("BATTERY_LOW_PCT", settings.BATTERY_LOW_PCT),
        "stale_data_timeout_sec": overrides.get("STALE_DATA_TIMEOUT_SEC", settings.STALE_DATA_TIMEOUT_SEC),
        "mqtt_enabled": settings.MQTT_ENABLED,
        "environment": settings.ENVIRONMENT,
        "is_demonstration_config": True
    }


@router.patch("")
def update_system_setting(updates: Dict[str, Any], db: Session = Depends(get_db)):
    """Update runtime configurable thresholds."""
    allowed_keys = [
        "TILT_WARNING_DEG", "TILT_CRITICAL_DEG",
        "DISPLACEMENT_WARNING_MM", "DISPLACEMENT_CRITICAL_MM",
        "RATE_WARNING_MM_HR", "RATE_CRITICAL_MM_HR",
        "ACCEL_WARNING_MM_HR2", "VIBRATION_WARNING_MS2", "VIBRATION_CRITICAL_MS2",
        "BATTERY_LOW_PCT", "STALE_DATA_TIMEOUT_SEC"
    ]

    for key, val in updates.items():
        key_upper = key.upper()
        if key_upper in allowed_keys and isinstance(val, (int, float)):
            setting = db.query(SystemSetting).filter(SystemSetting.key == key_upper).first()
            if not setting:
                setting = SystemSetting(key=key_upper, value=val)
                db.add(setting)
            else:
                setting.value = val

            # Also update running settings object if match
            if hasattr(settings, key_upper):
                setattr(settings, key_upper, float(val))

    audit = AuditEvent(
        category="SETTINGS",
        actor="admin",
        action="UPDATE_SETTINGS",
        outcome="SUCCESS",
        details=updates
    )
    db.add(audit)
    db.commit()

    return get_system_settings(db)
