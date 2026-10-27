import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from backend.app.core.config import settings
from backend.app.db.models import TelemetryRecord


def compute_vector_tilt(tilt_x: Optional[float], tilt_y: Optional[float]) -> Optional[float]:
    """Calculate resultant vector tilt angle in degrees: sqrt(tilt_x^2 + tilt_y^2)."""
    if tilt_x is None and tilt_y is None:
        return None
    x = tilt_x or 0.0
    y = tilt_y or 0.0
    return round(math.sqrt(x**2 + y**2), 4)


def compute_kinematics(
    current_time: datetime,
    current_disp: Optional[float],
    prev_record: Optional[TelemetryRecord]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate deformation velocity (mm/hr) and acceleration (mm/hr^2).
    Requires valid timestamps and measurements. Handles irregular sampling.
    """
    if current_disp is None or prev_record is None or prev_record.displacement_mm is None:
        return None, None

    t_curr = current_time.replace(tzinfo=timezone.utc) if current_time.tzinfo is None else current_time
    t_prev = prev_record.timestamp.replace(tzinfo=timezone.utc) if prev_record.timestamp.tzinfo is None else prev_record.timestamp

    delta_sec = (t_curr - t_prev).total_seconds()
    if delta_sec < 0.5:
        # Avoid division by zero or jitter from near-simultaneous packets
        return None, None

    delta_hours = delta_sec / 3600.0
    delta_disp = current_disp - prev_record.displacement_mm
    velocity_mm_hr = round(delta_disp / delta_hours, 4)

    acceleration_mm_hr2 = None
    if prev_record.velocity_mm_hr is not None:
        delta_v = velocity_mm_hr - prev_record.velocity_mm_hr
        acceleration_mm_hr2 = round(delta_v / delta_hours, 4)

    return velocity_mm_hr, acceleration_mm_hr2


class RuleFinding:
    def __init__(
        self,
        severity: str,  # CRITICAL, WARNING, WATCH, DATA_UNRELIABLE, INFO
        category: str,  # DISPLACEMENT, VELOCITY, ACCELERATION, TILT, VIBRATION, BATTERY
        title: str,
        description: str,
        triggering_rule: str,
        evidence: Dict[str, Any]
    ):
        self.severity = severity
        self.category = category
        self.title = title
        self.description = description
        self.triggering_rule = triggering_rule
        self.evidence = evidence


def evaluate_geotechnical_rules(
    node_id: str,
    timestamp: datetime,
    displacement_mm: Optional[float],
    vector_tilt_deg: Optional[float],
    velocity_mm_hr: Optional[float],
    acceleration_mm_hr2: Optional[float],
    vibration_rms_ms2: Optional[float],
    battery_pct: Optional[float],
    quality: Dict[str, Any]
) -> List[RuleFinding]:
    """
    Evaluate deterministic, interpretable geotechnical decision rules against current telemetry.
    Returns list of RuleFinding instances.
    """
    findings: List[RuleFinding] = []

    # 1. Acceleration in deformation rate (Tertiary Creep Warning)
    if acceleration_mm_hr2 is not None and acceleration_mm_hr2 >= settings.ACCEL_WARNING_MM_HR2:
        findings.append(RuleFinding(
            severity="CRITICAL",
            category="ACCELERATION",
            title="Accelerating Ground Movement Detected (Tertiary Creep)",
            description=f"Deformation rate is accelerating at {acceleration_mm_hr2:.2f} mm/hr² (threshold: {settings.ACCEL_WARNING_MM_HR2} mm/hr²). Indicates escalating rock mass distress.",
            triggering_rule="RULE_CRITICAL_ACCELERATION",
            evidence={
                "acceleration_mm_hr2": acceleration_mm_hr2,
                "velocity_mm_hr": velocity_mm_hr,
                "displacement_mm": displacement_mm,
                "threshold_mm_hr2": settings.ACCEL_WARNING_MM_HR2
            }
        ))

    # 2. Deformation Velocity / Rate
    if velocity_mm_hr is not None:
        abs_v = abs(velocity_mm_hr)
        if abs_v >= settings.RATE_CRITICAL_MM_HR:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="VELOCITY",
                title="Critical Rate of Ground Subsidence",
                description=f"Deformation velocity reached {velocity_mm_hr:.2f} mm/hr exceeding critical threshold of {settings.RATE_CRITICAL_MM_HR} mm/hr.",
                triggering_rule="RULE_CRITICAL_VELOCITY",
                evidence={"velocity_mm_hr": velocity_mm_hr, "threshold": settings.RATE_CRITICAL_MM_HR}
            ))
        elif abs_v >= settings.RATE_WARNING_MM_HR:
            findings.append(RuleFinding(
                severity="WARNING",
                category="VELOCITY",
                title="Elevated Rate of Ground Movement",
                description=f"Deformation velocity is {velocity_mm_hr:.2f} mm/hr exceeding warning threshold of {settings.RATE_WARNING_MM_HR} mm/hr.",
                triggering_rule="RULE_WARNING_VELOCITY",
                evidence={"velocity_mm_hr": velocity_mm_hr, "threshold": settings.RATE_WARNING_MM_HR}
            ))

    # 3. Cumulative Displacement
    if displacement_mm is not None:
        abs_disp = abs(displacement_mm)
        if abs_disp >= settings.DISPLACEMENT_CRITICAL_MM:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="DISPLACEMENT",
                title="Critical Cumulative Subsidence Limit Exceeded",
                description=f"Cumulative displacement has reached {displacement_mm:.2f} mm (critical limit: {settings.DISPLACEMENT_CRITICAL_MM} mm).",
                triggering_rule="RULE_CRITICAL_DISPLACEMENT",
                evidence={"displacement_mm": displacement_mm, "threshold": settings.DISPLACEMENT_CRITICAL_MM}
            ))
        elif abs_disp >= settings.DISPLACEMENT_WARNING_MM:
            findings.append(RuleFinding(
                severity="WARNING",
                category="DISPLACEMENT",
                title="Warning Cumulative Subsidence Limit Exceeded",
                description=f"Cumulative displacement is {displacement_mm:.2f} mm (warning limit: {settings.DISPLACEMENT_WARNING_MM} mm).",
                triggering_rule="RULE_WARNING_DISPLACEMENT",
                evidence={"displacement_mm": displacement_mm, "threshold": settings.DISPLACEMENT_WARNING_MM}
            ))

    # 4. Resultant Vector Tilt
    if vector_tilt_deg is not None:
        if vector_tilt_deg >= settings.TILT_CRITICAL_DEG:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="TILT",
                title="Critical Inclinometer Tilt Exceeded",
                description=f"Vector tilt reached {vector_tilt_deg:.2f}° exceeding critical threshold of {settings.TILT_CRITICAL_DEG}°.",
                triggering_rule="RULE_CRITICAL_TILT",
                evidence={"vector_tilt_deg": vector_tilt_deg, "threshold": settings.TILT_CRITICAL_DEG}
            ))
        elif vector_tilt_deg >= settings.TILT_WARNING_DEG:
            findings.append(RuleFinding(
                severity="WARNING",
                category="TILT",
                title="Elevated Inclinometer Tilt Detected",
                description=f"Vector tilt is {vector_tilt_deg:.2f}° exceeding warning threshold of {settings.TILT_WARNING_DEG}°.",
                triggering_rule="RULE_WARNING_TILT",
                evidence={"vector_tilt_deg": vector_tilt_deg, "threshold": settings.TILT_WARNING_DEG}
            ))

    # 5. Dynamic Seismic / Blasting Vibration
    if vibration_rms_ms2 is not None:
        if vibration_rms_ms2 >= settings.VIBRATION_CRITICAL_MS2:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="VIBRATION",
                title="Severe Ground Vibration / Blast Impact",
                description=f"Vibration RMS reached {vibration_rms_ms2:.2f} m/s² (critical limit: {settings.VIBRATION_CRITICAL_MS2} m/s²).",
                triggering_rule="RULE_CRITICAL_VIBRATION",
                evidence={"vibration_rms_ms2": vibration_rms_ms2, "threshold": settings.VIBRATION_CRITICAL_MS2}
            ))
        elif vibration_rms_ms2 >= settings.VIBRATION_WARNING_MS2:
            findings.append(RuleFinding(
                severity="WARNING",
                category="VIBRATION",
                title="High Dynamic Ground Vibration",
                description=f"Vibration RMS is {vibration_rms_ms2:.2f} m/s² (warning limit: {settings.VIBRATION_WARNING_MS2} m/s²).",
                triggering_rule="RULE_WARNING_VIBRATION",
                evidence={"vibration_rms_ms2": vibration_rms_ms2, "threshold": settings.VIBRATION_WARNING_MS2}
            ))

    # 6. Battery Warning
    if battery_pct is not None and battery_pct <= settings.BATTERY_LOW_PCT:
        findings.append(RuleFinding(
            severity="WARNING",
            category="BATTERY",
            title="Monitoring Node Battery Depleted",
            description=f"Node battery is at {battery_pct:.1f}% (critical recharge threshold: {settings.BATTERY_LOW_PCT}%).",
            triggering_rule="RULE_LOW_BATTERY",
            evidence={"battery_pct": battery_pct, "threshold": settings.BATTERY_LOW_PCT}
        ))

    return findings
