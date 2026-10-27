import math
from datetime import datetime, timezone, timedelta
from backend.app.analytics.rules import (
    compute_vector_tilt, compute_kinematics, evaluate_geotechnical_rules
)
from backend.app.db.models import TelemetryRecord


def test_vector_tilt_calculation():
    # 3-4-5 triangle: 3.0 deg and 4.0 deg -> 5.0 deg
    result = compute_vector_tilt(3.0, 4.0)
    assert math.isclose(result, 5.0, abs_tol=1e-3)
    assert compute_vector_tilt(None, None) is None


def test_kinematics_derivation():
    t0 = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=3600)  # 1 hour later

    prev = TelemetryRecord(
        timestamp=t0,
        displacement_mm=10.0,
        velocity_mm_hr=2.0
    )

    # Displacement moves from 10.0 mm to 15.0 mm in 1 hour -> velocity = 5.0 mm/hr
    v, a = compute_kinematics(t1, 15.0, prev)
    assert v == 5.0
    # Acceleration = (5.0 - 2.0) / 1.0 hr = 3.0 mm/hr^2
    assert a == 3.0


def test_critical_geotechnical_rules():
    ts = datetime.now(timezone.utc)
    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=ts,
        displacement_mm=35.0,  # Critical > 30.0 mm
        vector_tilt_deg=6.0,   # Critical > 5.0 deg
        velocity_mm_hr=6.0,    # Critical > 5.0 mm/hr
        acceleration_mm_hr2=0.8,  # Critical > 0.5 mm/hr^2
        vibration_rms_ms2=10.0, # Critical > 8.0 m/s^2
        battery_pct=15.0,      # Low < 20%
        quality={}
    )

    severities = [f.severity for f in findings]
    categories = [f.category for f in findings]

    assert "CRITICAL" in severities
    assert "ACCELERATION" in categories
    assert "DISPLACEMENT" in categories
    assert "TILT" in categories
    assert "BATTERY" in categories
