from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.db.models import SystemSetting, AuditEvent
from backend.app.schemas.settings import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("", response_model=SettingsResponse)
def get_system_settings(db: Session = Depends(get_db)):
    """Return effective thresholds and configuration."""
    overrides = {s.key: s.value for s in db.query(SystemSetting).all()}

    return SettingsResponse(
        tilt_warning_deg=float(overrides.get("TILT_WARNING_DEG", settings.TILT_WARNING_DEG)),
        tilt_critical_deg=float(overrides.get("TILT_CRITICAL_DEG", settings.TILT_CRITICAL_DEG)),
        displacement_warning_mm=float(overrides.get("DISPLACEMENT_WARNING_MM", settings.DISPLACEMENT_WARNING_MM)),
        displacement_critical_mm=float(overrides.get("DISPLACEMENT_CRITICAL_MM", settings.DISPLACEMENT_CRITICAL_MM)),
        rate_warning_mm_hr=float(overrides.get("RATE_WARNING_MM_HR", settings.RATE_WARNING_MM_HR)),
        rate_critical_mm_hr=float(overrides.get("RATE_CRITICAL_MM_HR", settings.RATE_CRITICAL_MM_HR)),
        accel_warning_mm_hr2=float(overrides.get("ACCEL_WARNING_MM_HR2", settings.ACCEL_WARNING_MM_HR2)),
        vibration_warning_ms2=float(overrides.get("VIBRATION_WARNING_MS2", settings.VIBRATION_WARNING_MS2)),
        vibration_critical_ms2=float(overrides.get("VIBRATION_CRITICAL_MS2", settings.VIBRATION_CRITICAL_MS2)),
        battery_low_pct=float(overrides.get("BATTERY_LOW_PCT", settings.BATTERY_LOW_PCT)),
        stale_data_timeout_sec=int(overrides.get("STALE_DATA_TIMEOUT_SEC", settings.STALE_DATA_TIMEOUT_SEC)),
        mqtt_enabled=settings.MQTT_ENABLED,
        environment=settings.ENVIRONMENT,
        is_demonstration_config=True
    )


@router.patch("", response_model=SettingsResponse)
def update_system_setting(updates: SettingsUpdate, db: Session = Depends(get_db)):
    """Update runtime configurable thresholds with hierarchy and bounds validation."""
    data_dict = updates.model_dump(exclude_unset=True)

    for key_upper, val in data_dict.items():
        if val is not None:
            setting = db.query(SystemSetting).filter(SystemSetting.key == key_upper).first()
            if not setting:
                setting = SystemSetting(key=key_upper, value=val)
                db.add(setting)
            else:
                setting.value = val

            # Update running runtime settings object
            if hasattr(settings, key_upper):
                setattr(settings, key_upper, val)

    audit = AuditEvent(
        category="SETTINGS",
        actor="admin",
        action="UPDATE_SETTINGS",
        outcome="SUCCESS",
        details=data_dict
    )
    db.add(audit)
    db.commit()

    return get_system_settings(db)
