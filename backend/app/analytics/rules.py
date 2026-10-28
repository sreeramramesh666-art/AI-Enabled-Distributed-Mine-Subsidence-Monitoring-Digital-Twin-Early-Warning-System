import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from backend.app.core.config import settings
from backend.app.db.models import TelemetryRecord, NodeBaseline


def compute_vector_tilt(tilt_x: Optional[float], tilt_y: Optional[float]) -> Optional[float]:
    """Calculate resultant vector tilt angle in degrees: sqrt(tilt_x^2 + tilt_y^2)."""
    if tilt_x is None and tilt_y is None:
        return None
    x = tilt_x or 0.0
    y = tilt_y or 0.0
    return round(math.sqrt(x**2 + y**2), 4)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in metres between two WGS84 coordinates using Haversine formula."""
    r = 6371000.0  # Mean radius of Earth in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_kinematics(
    current_time: datetime,
    current_disp: Optional[float],
    prev_record: Optional[TelemetryRecord],
    include_diagnostics: bool = False
) -> Any:
    """
    Calculate deformation velocity (mm/hr) and acceleration (mm/hr^2).
    Requires valid timestamps and measurements. Handles irregular sampling.
    Returns (velocity_mm_hr, acceleration_mm_hr2) by default, or
    (velocity_mm_hr, acceleration_mm_hr2, diagnostics) if include_diagnostics=True.
    """
    diagnostics: Dict[str, Any] = {
        "delta_sec": 0.0,
        "delta_disp_mm": 0.0,
        "is_irregular_interval": False,
        "uncertainty_note": None
    }

    if current_disp is None or prev_record is None or prev_record.displacement_mm is None:
        if include_diagnostics:
            diagnostics["uncertainty_note"] = "Missing observation data for kinematics calculation"
            return None, None, diagnostics
        return None, None

    t_curr = current_time.replace(tzinfo=timezone.utc) if current_time.tzinfo is None else current_time
    t_prev = prev_record.timestamp.replace(tzinfo=timezone.utc) if prev_record.timestamp.tzinfo is None else prev_record.timestamp

    delta_sec = (t_curr - t_prev).total_seconds()
    diagnostics["delta_sec"] = delta_sec

    if delta_sec < 0.5:
        # Avoid division by zero or jitter from near-simultaneous packets
        diagnostics["uncertainty_note"] = f"Near-simultaneous timestamp gap ({delta_sec:.2f}s < 0.5s); kinematics skipped to avoid division by zero"
        if include_diagnostics:
            return None, None, diagnostics
        return None, None

    delta_hours = delta_sec / 3600.0
    delta_disp = current_disp - prev_record.displacement_mm
    diagnostics["delta_disp_mm"] = delta_disp
    diagnostics["dt_hours"] = delta_hours

    if delta_sec > 300:
        diagnostics["is_irregular_interval"] = True
        diagnostics["uncertainty_note"] = f"Sampling interval ({delta_sec:.1f}s) exceeds nominal frequency; rate represents time-averaged velocity"

    velocity_mm_hr = round(delta_disp / delta_hours, 4)

    acceleration_mm_hr2 = None
    if prev_record.velocity_mm_hr is not None:
        delta_v = velocity_mm_hr - prev_record.velocity_mm_hr
        acceleration_mm_hr2 = round(delta_v / delta_hours, 4)

    diagnostics["is_accelerating"] = bool(acceleration_mm_hr2 is not None and acceleration_mm_hr2 > 0)

    if include_diagnostics:
        return velocity_mm_hr, acceleration_mm_hr2, diagnostics
    return velocity_mm_hr, acceleration_mm_hr2


class RuleFinding:
    def __init__(
        self,
        severity: str,  # CRITICAL, WARNING, WATCH, DATA_UNRELIABLE, INFO
        category: str,  # DISPLACEMENT, VELOCITY, ACCELERATION, TILT, VIBRATION, BATTERY, SENSOR_DRIFT, SENSOR_DISAGREEMENT, STALE_DATA
        title: str,
        description: str,
        triggering_rule: str,
        evidence: Dict[str, Any],
        uncertainty: str = "MODERATE_SINGLE_NODE"  # HIGH_CONFIDENCE_CORROBORATED, MODERATE_SINGLE_NODE, HIGH_UNCERTAINTY_STALE_DATA, INSTRUMENT_DISAGREEMENT
    ):
        self.severity = severity
        self.category = category
        self.title = title
        self.description = description
        self.triggering_rule = triggering_rule
        self.evidence = evidence
        self.uncertainty = uncertainty


def evaluate_geotechnical_rules(
    node_id: str,
    timestamp: datetime,
    displacement_mm: Optional[float],
    vector_tilt_deg: Optional[float],
    velocity_mm_hr: Optional[float],
    acceleration_mm_hr2: Optional[float],
    vibration_rms_ms2: Optional[float],
    battery_pct: Optional[float],
    quality: Dict[str, Any],
    prev_record: Optional[TelemetryRecord] = None,
    baseline: Optional[NodeBaseline] = None,
    recent_history: Optional[List[TelemetryRecord]] = None,
    spatial_neighbors: Optional[List[Dict[str, Any]]] = None,
    tilt_x_deg: Optional[float] = None,
    tilt_y_deg: Optional[float] = None,
) -> List[RuleFinding]:
    """
    Evaluate deterministic, interpretable geotechnical decision rules against current telemetry.
    Attaches measurements, time windows, active thresholds, rule metadata, and uncertainty.
    """
    findings: List[RuleFinding] = []

    t_curr = timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp
    t_prev = (prev_record.timestamp.replace(tzinfo=timezone.utc) if prev_record.timestamp.tzinfo is None else prev_record.timestamp) if prev_record else None

    # Common measurement evidence envelope
    meas_envelope = {
        "displacement_mm": displacement_mm,
        "tilt_x_deg": tilt_x_deg,
        "tilt_y_deg": tilt_y_deg,
        "velocity_mm_hr": velocity_mm_hr,
        "acceleration_mm_hr2": acceleration_mm_hr2,
        "vector_tilt_deg": vector_tilt_deg,
        "vibration_rms_ms2": vibration_rms_ms2,
        "battery_pct": battery_pct,
    }
    time_window_envelope = {
        "timestamp": t_curr.isoformat(),
        "prev_timestamp": t_prev.isoformat() if t_prev else None,
        "interval_sec": (t_curr - t_prev).total_seconds() if t_prev else None
    }
    model_meta = {
        "model_name": "DeterministicGeotechnicalRules_v1",
        "interpretable": True,
        "is_probability_of_collapse": False,
        "dgms_compliance_notice": "Algorithmic decision rules provide early awareness. Evacuation requires qualified geotechnical surveyor assessment."
    }

    # 1. Acceleration in deformation rate (Tertiary Creep Warning)
    if acceleration_mm_hr2 is not None and acceleration_mm_hr2 >= settings.ACCEL_WARNING_MM_HR2:
        if velocity_mm_hr is not None and velocity_mm_hr > 0.1:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="ACCELERATION",
                title="Accelerating Ground Movement Detected (Tertiary Creep)",
                description=(
                    f"Deformation rate is accelerating at {acceleration_mm_hr2:.2f} mm/hr² "
                    f"(critical threshold: {settings.ACCEL_WARNING_MM_HR2} mm/hr²). "
                    f"Positive acceleration combined with velocity ({velocity_mm_hr:.2f} mm/hr) indicates tertiary creep phase."
                ),
                triggering_rule="RULE_CRITICAL_ACCELERATION",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_CRITICAL_ACCELERATION",
                    "model_metadata": model_meta,
                    "thresholds": {"accel_critical_mm_hr2": settings.ACCEL_WARNING_MM_HR2},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))

    # 2. Sudden Step Displacement / Fault Slip
    if prev_record and prev_record.displacement_mm is not None and displacement_mm is not None and t_prev is not None:
        delta_d_step = abs(displacement_mm - prev_record.displacement_mm)
        dt_step = (t_curr - t_prev).total_seconds()
        if delta_d_step >= settings.STEP_DISPLACEMENT_THRESHOLD_MM and dt_step <= 300:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="DISPLACEMENT",
                title="Sudden Step Displacement Detected (Possible Fault Slip)",
                description=(
                    f"Instantaneous ground displacement increment of {delta_d_step:.2f} mm occurred in {dt_step:.1f}s "
                    f"(threshold: {settings.STEP_DISPLACEMENT_THRESHOLD_MM} mm). "
                    "Indicates abrupt shear displacement along rock mass discontinuity."
                ),
                triggering_rule="RULE_SUDDEN_FAULT_SLIP",
                evidence={
                    "measurements": meas_envelope,
                    "step_delta_mm": delta_d_step,
                    "step_duration_sec": dt_step,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_SUDDEN_FAULT_SLIP",
                    "model_metadata": model_meta,
                    "thresholds": {"step_threshold_mm": settings.STEP_DISPLACEMENT_THRESHOLD_MM},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))

    # 3. Deformation Velocity / Rate
    if velocity_mm_hr is not None:
        abs_v = abs(velocity_mm_hr)
        if abs_v >= settings.RATE_CRITICAL_MM_HR:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="VELOCITY",
                title="Critical Rate of Ground Subsidence",
                description=f"Deformation velocity reached {velocity_mm_hr:.2f} mm/hr exceeding critical threshold of {settings.RATE_CRITICAL_MM_HR} mm/hr.",
                triggering_rule="RULE_CRITICAL_VELOCITY",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_CRITICAL_VELOCITY",
                    "model_metadata": model_meta,
                    "thresholds": {"rate_critical_mm_hr": settings.RATE_CRITICAL_MM_HR},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))
        elif abs_v >= settings.RATE_WARNING_MM_HR:
            findings.append(RuleFinding(
                severity="WARNING",
                category="VELOCITY",
                title="Elevated Rate of Ground Movement",
                description=f"Deformation velocity is {velocity_mm_hr:.2f} mm/hr exceeding warning threshold of {settings.RATE_WARNING_MM_HR} mm/hr.",
                triggering_rule="RULE_WARNING_VELOCITY",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_WARNING_VELOCITY",
                    "model_metadata": model_meta,
                    "thresholds": {"rate_warning_mm_hr": settings.RATE_WARNING_MM_HR},
                    "uncertainty": "MODERATE_SINGLE_NODE"
                },
                uncertainty="MODERATE_SINGLE_NODE"
            ))

    # 4. Cumulative Displacement (raw or relative to baseline datum)
    if displacement_mm is not None:
        disp_eval = displacement_mm
        baseline_offset = 0.0
        if baseline and baseline.is_valid and baseline.displacement_mean is not None:
            baseline_offset = baseline.displacement_mean
            disp_eval = displacement_mm - baseline_offset

        abs_disp = abs(disp_eval)
        if abs_disp >= settings.DISPLACEMENT_CRITICAL_MM:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="DISPLACEMENT",
                title="Critical Cumulative Subsidence Limit Exceeded",
                description=f"Cumulative displacement has reached {disp_eval:.2f} mm (critical limit: {settings.DISPLACEMENT_CRITICAL_MM} mm).",
                triggering_rule="RULE_CRITICAL_DISPLACEMENT",
                evidence={
                    "measurements": meas_envelope,
                    "baseline_offset_mm": baseline_offset,
                    "evaluated_displacement_mm": disp_eval,
                    "net_displacement_mm": disp_eval,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_CRITICAL_DISPLACEMENT",
                    "model_metadata": model_meta,
                    "thresholds": {"disp_critical_mm": settings.DISPLACEMENT_CRITICAL_MM},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))
        elif abs_disp >= settings.DISPLACEMENT_WARNING_MM:
            findings.append(RuleFinding(
                severity="WARNING",
                category="DISPLACEMENT",
                title="Warning Cumulative Subsidence Limit Exceeded",
                description=f"Cumulative displacement is {disp_eval:.2f} mm (warning limit: {settings.DISPLACEMENT_WARNING_MM} mm).",
                triggering_rule="RULE_WARNING_DISPLACEMENT",
                evidence={
                    "measurements": meas_envelope,
                    "baseline_offset_mm": baseline_offset,
                    "evaluated_displacement_mm": disp_eval,
                    "net_displacement_mm": disp_eval,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_WARNING_DISPLACEMENT",
                    "model_metadata": model_meta,
                    "thresholds": {"disp_warning_mm": settings.DISPLACEMENT_WARNING_MM},
                    "uncertainty": "MODERATE_SINGLE_NODE"
                },
                uncertainty="MODERATE_SINGLE_NODE"
            ))

    # 5. Resultant Vector Tilt & Baseline Tilt Shift
    if vector_tilt_deg is not None:
        if vector_tilt_deg >= settings.TILT_CRITICAL_DEG:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="TILT",
                title="Critical Inclinometer Tilt Exceeded",
                description=f"Vector tilt reached {vector_tilt_deg:.2f}° exceeding critical threshold of {settings.TILT_CRITICAL_DEG}°.",
                triggering_rule="RULE_CRITICAL_TILT",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_CRITICAL_TILT",
                    "model_metadata": model_meta,
                    "thresholds": {"tilt_critical_deg": settings.TILT_CRITICAL_DEG},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))
        elif vector_tilt_deg >= settings.TILT_WARNING_DEG:
            findings.append(RuleFinding(
                severity="WARNING",
                category="TILT",
                title="Elevated Inclinometer Tilt Detected",
                description=f"Vector tilt is {vector_tilt_deg:.2f}° exceeding warning threshold of {settings.TILT_WARNING_DEG}°.",
                triggering_rule="RULE_WARNING_TILT",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_WARNING_TILT",
                    "model_metadata": model_meta,
                    "thresholds": {"tilt_warning_deg": settings.TILT_WARNING_DEG},
                    "uncertainty": "MODERATE_SINGLE_NODE"
                },
                uncertainty="MODERATE_SINGLE_NODE"
            ))

    # 6. Persistent Baseline Tilt Departure
    if baseline and baseline.is_valid and baseline.tilt_x_mean is not None and baseline.tilt_y_mean is not None:
        cur_tx = tilt_x_deg if tilt_x_deg is not None else (prev_record.tilt_x_deg if prev_record else None)
        cur_ty = tilt_y_deg if tilt_y_deg is not None else (prev_record.tilt_y_deg if prev_record else None)
        if cur_tx is not None and cur_ty is not None:
            tx_diff = cur_tx - baseline.tilt_x_mean
            ty_diff = cur_ty - baseline.tilt_y_mean
            tilt_offset = round(math.sqrt(tx_diff**2 + ty_diff**2), 4)
        elif vector_tilt_deg is not None:
            baseline_vec = math.sqrt(baseline.tilt_x_mean**2 + baseline.tilt_y_mean**2)
            tilt_offset = round(abs(vector_tilt_deg - baseline_vec), 4)
        else:
            tilt_offset = 0.0

        if tilt_offset >= settings.TILT_WARNING_DEG:
            findings.append(RuleFinding(
                severity="WARNING",
                category="TILT",
                title="Persistent Inclinometer Baseline Departure",
                description=(
                    f"Resultant tilt has shifted {tilt_offset:.2f}° relative to calibrated initial baseline "
                    f"(baseline window: {baseline.sample_count} observations)."
                ),
                triggering_rule="RULE_PERSISTENT_TILT_SHIFT",
                evidence={
                    "measurements": meas_envelope,
                    "tilt_offset_from_baseline_deg": tilt_offset,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_PERSISTENT_TILT_SHIFT",
                    "model_metadata": model_meta,
                    "thresholds": {"tilt_warning_deg": settings.TILT_WARNING_DEG},
                    "uncertainty": "MODERATE_SINGLE_NODE"
                },
                uncertainty="MODERATE_SINGLE_NODE"
            ))

    # 7. Dynamic Seismic / Blasting Vibration Discrimination
    if vibration_rms_ms2 is not None:
        delta_d_vib = 0.0
        if prev_record and prev_record.displacement_mm is not None and displacement_mm is not None:
            delta_d_vib = abs(displacement_mm - prev_record.displacement_mm)

        if vibration_rms_ms2 >= settings.VIBRATION_WARNING_MS2 and delta_d_vib <= 0.15:
            # Controlled blasting event with high transient vibration but negligible permanent displacement
            findings.append(RuleFinding(
                severity="WATCH",
                category="VIBRATION",
                title="Transient Production Blasting Vibration (No Ground Settlement)",
                description=(
                    f"Dynamic vibration RMS reached {vibration_rms_ms2:.2f} m/s² with negligible vertical ground displacement "
                    f"({delta_d_vib:.3f} mm). Classified as production blast impact rather than structural slope failure."
                ),
                triggering_rule="RULE_TRANSIENT_BLASTING_VIBRATION",
                evidence={
                    "measurements": meas_envelope,
                    "displacement_increment_mm": delta_d_vib,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_TRANSIENT_BLASTING_VIBRATION",
                    "model_metadata": model_meta,
                    "thresholds": {"vibration_warning_ms2": settings.VIBRATION_WARNING_MS2},
                    "uncertainty": "HIGH_CONFIDENCE_BLAST_DISCRIMINATION"
                },
                uncertainty="HIGH_CONFIDENCE_BLAST_DISCRIMINATION"
            ))
        elif vibration_rms_ms2 >= settings.VIBRATION_CRITICAL_MS2:
            findings.append(RuleFinding(
                severity="CRITICAL",
                category="VIBRATION",
                title="Severe Ground Vibration / Dynamic Seismic Hazard",
                description=f"Vibration RMS reached {vibration_rms_ms2:.2f} m/s² (critical limit: {settings.VIBRATION_CRITICAL_MS2} m/s²).",
                triggering_rule="RULE_CRITICAL_VIBRATION",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_CRITICAL_VIBRATION",
                    "model_metadata": model_meta,
                    "thresholds": {"vibration_critical_ms2": settings.VIBRATION_CRITICAL_MS2},
                    "uncertainty": "HIGH_CONFIDENCE_PHYSICAL"
                },
                uncertainty="HIGH_CONFIDENCE_PHYSICAL"
            ))
        elif vibration_rms_ms2 >= settings.VIBRATION_WARNING_MS2:
            findings.append(RuleFinding(
                severity="WARNING",
                category="VIBRATION",
                title="High Dynamic Ground Vibration",
                description=f"Vibration RMS is {vibration_rms_ms2:.2f} m/s² (warning limit: {settings.VIBRATION_WARNING_MS2} m/s²).",
                triggering_rule="RULE_WARNING_VIBRATION",
                evidence={
                    "measurements": meas_envelope,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_WARNING_VIBRATION",
                    "model_metadata": model_meta,
                    "thresholds": {"vibration_warning_ms2": settings.VIBRATION_WARNING_MS2},
                    "uncertainty": "MODERATE_SINGLE_NODE"
                },
                uncertainty="MODERATE_SINGLE_NODE"
            ))

    # 8. Cross-Sensor Channel Disagreement (Inclinometer vs Extensometer)
    if prev_record and prev_record.displacement_mm is not None and displacement_mm is not None:
        delta_d = abs(displacement_mm - prev_record.displacement_mm)
        prev_vt = compute_vector_tilt(prev_record.tilt_x_deg, prev_record.tilt_y_deg) or 0.0
        curr_vt = vector_tilt_deg or 0.0
        delta_tilt = abs(curr_vt - prev_vt)

        # High rotational tilt with zero vertical displacement
        if delta_tilt >= 2.5 and delta_d <= 0.08 and (vibration_rms_ms2 or 0.0) < 1.0:
            findings.append(RuleFinding(
                severity="WARNING",
                category="SENSOR_DISAGREEMENT",
                title="Sensor Disagreement: Rotational Tilt Without Vertical Displacement",
                description=(
                    f"Resultant tilt shifted by {delta_tilt:.2f}° while vertical displacement increment was negligible "
                    f"({delta_d:.3f} mm). Indicates potential mounting bracket loosening or localized mechanical disturbance."
                ),
                triggering_rule="RULE_SENSOR_DISAGREEMENT_TILT",
                evidence={
                    "measurements": meas_envelope,
                    "delta_tilt_deg": delta_tilt,
                    "delta_displacement_mm": delta_d,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_SENSOR_DISAGREEMENT_TILT",
                    "model_metadata": model_meta,
                    "uncertainty": "INSTRUMENT_DISAGREEMENT"
                },
                uncertainty="INSTRUMENT_DISAGREEMENT"
            ))
        # High vertical displacement with zero tilt change on a multiparameter node
        elif delta_d >= 10.0 and delta_tilt <= 0.05 and (vibration_rms_ms2 or 0.0) < 1.0:
            findings.append(RuleFinding(
                severity="WARNING",
                category="SENSOR_DISAGREEMENT",
                title="Sensor Disagreement: Large Displacement Without Inclinometer Response",
                description=(
                    f"Vertical displacement shifted by {delta_d:.2f} mm while vector tilt remained unchanged "
                    f"({delta_tilt:.3f}°). Recommends field inspection of extensometer anchor cable."
                ),
                triggering_rule="RULE_SENSOR_DISAGREEMENT_DISP",
                evidence={
                    "measurements": meas_envelope,
                    "delta_displacement_mm": delta_d,
                    "delta_tilt_deg": delta_tilt,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_SENSOR_DISAGREEMENT_DISP",
                    "model_metadata": model_meta,
                    "uncertainty": "INSTRUMENT_DISAGREEMENT"
                },
                uncertainty="INSTRUMENT_DISAGREEMENT"
            ))

    # 9. Faulty Sensors: Frozen Output Check
    if recent_history and len(recent_history) >= 5:
        disps = [r.displacement_mm for r in recent_history if r.displacement_mm is not None]
        if len(disps) >= 5 and displacement_mm is not None and all(d == displacement_mm for d in disps):
            findings.append(RuleFinding(
                severity="DATA_UNRELIABLE",
                category="SENSOR_DRIFT",
                title="Frozen Transducer Output Detected",
                description=(
                    f"Node reported {len(disps) + 1} successive bitwise-identical displacement measurements "
                    f"({displacement_mm:.4f} mm). Suggests stuck ADC converter, firmware lockup, or severed transducer signal line."
                ),
                triggering_rule="RULE_FROZEN_SENSOR",
                evidence={
                    "measurements": meas_envelope,
                    "identical_consecutive_count": len(disps) + 1,
                    "time_window": time_window_envelope,
                    "rule_name": "RULE_FROZEN_SENSOR",
                    "model_metadata": model_meta,
                    "uncertainty": "FROZEN_SENSOR_ERROR"
                },
                uncertainty="FROZEN_SENSOR_ERROR"
            ))

    # 10. Faulty Sensors: Slow Monotonic Drift Without Movement
    if recent_history and len(recent_history) >= 6:
        # Check if tilt is monotonically creeping while displacement and vibration are completely zero
        tilts = [compute_vector_tilt(r.tilt_x_deg, r.tilt_y_deg) for r in recent_history]
        valid_tilts = [t for t in tilts if t is not None]
        if len(valid_tilts) >= 6 and vector_tilt_deg is not None:
            all_tilts = valid_tilts + [vector_tilt_deg]
            is_monotonic = all(all_tilts[i] <= all_tilts[i+1] for i in range(len(all_tilts)-1))
            total_tilt_drift = all_tilts[-1] - all_tilts[0]
            if is_monotonic and total_tilt_drift >= 0.8 and (displacement_mm is None or abs(displacement_mm) <= 0.1):
                findings.append(RuleFinding(
                    severity="WATCH",
                    category="SENSOR_DRIFT",
                    title="Electronic Sensor Drift Suspected",
                    description=(
                        f"Inclinometer channel has exhibited monotonic drift ({total_tilt_drift:.2f}°) over "
                        f"{len(all_tilts)} observations with zero corresponding vertical ground movement. "
                        "Indicates thermal or electronic baseline drift rather than macro pit instability."
                    ),
                    triggering_rule="RULE_SENSOR_DRIFT",
                    evidence={
                        "measurements": meas_envelope,
                        "drift_amount_deg": total_tilt_drift,
                        "time_window": time_window_envelope,
                        "rule_name": "RULE_SENSOR_DRIFT",
                        "model_metadata": model_meta,
                        "uncertainty": "HIGH_UNCERTAINTY_DRIFT"
                    },
                    uncertainty="HIGH_UNCERTAINTY_DRIFT"
                ))

    # 11. Battery Warning
    if battery_pct is not None and battery_pct <= settings.BATTERY_LOW_PCT:
        findings.append(RuleFinding(
            severity="WARNING",
            category="BATTERY",
            title="Monitoring Node Battery Depleted",
            description=f"Node battery is at {battery_pct:.1f}% (critical recharge threshold: {settings.BATTERY_LOW_PCT}%).",
            triggering_rule="RULE_LOW_BATTERY",
            evidence={
                "measurements": meas_envelope,
                "time_window": time_window_envelope,
                "rule_name": "RULE_LOW_BATTERY",
                "model_metadata": model_meta,
                "thresholds": {"battery_low_pct": settings.BATTERY_LOW_PCT},
                "uncertainty": "HIGH_CONFIDENCE_DIAGNOSTIC"
            },
            uncertainty="HIGH_CONFIDENCE_DIAGNOSTIC"
        ))

    # 12. Spatial Corroboration Pattern
    if spatial_neighbors and len(spatial_neighbors) > 0:
        # Check if current node has any active physical movement alert
        has_physical_alert = any(
            f.category in ("DISPLACEMENT", "VELOCITY", "ACCELERATION", "TILT") and f.severity in ("CRITICAL", "WARNING")
            for f in findings
        )
        if has_physical_alert:
            # Count moving proximate neighbors within 500m
            moving_neighbors = [
                n for n in spatial_neighbors
                if abs(n.get("displacement_mm") or 0.0) >= settings.DISPLACEMENT_WARNING_MM
                or abs(n.get("velocity_mm_hr") or 0.0) >= settings.RATE_WARNING_MM_HR
            ]
            if len(moving_neighbors) >= 1:
                # Corroborated macro ground subsidence!
                neighbor_ids = [n.get("node_id") for n in moving_neighbors]
                findings.append(RuleFinding(
                    severity="CRITICAL",
                    category="DISPLACEMENT",
                    title="Spatial Macro Subsidence Corroborated Across Neighbouring Nodes",
                    description=(
                        f"Elevated movement at node {node_id} is spatially corroborated by {len(moving_neighbors)} "
                        f"neighbouring sensor node(s) ({', '.join(neighbor_ids)}) within 500m radius. "
                        "Confirms contiguous ground mass displacement across open-cast bench sector."
                    ),
                    triggering_rule="RULE_MACRO_SUBSIDENCE_CORROBORATED",
                    evidence={
                        "measurements": meas_envelope,
                        "corroborating_nodes": neighbor_ids,
                        "time_window": time_window_envelope,
                        "rule_name": "RULE_MACRO_SUBSIDENCE_CORROBORATED",
                        "model_metadata": model_meta,
                        "uncertainty": "HIGH_CONFIDENCE_CORROBORATED"
                    },
                    uncertainty="HIGH_CONFIDENCE_CORROBORATED"
                ))
                # Update uncertainty on all findings
                for f in findings:
                    if f.category in ("DISPLACEMENT", "VELOCITY", "ACCELERATION"):
                        f.uncertainty = "HIGH_CONFIDENCE_CORROBORATED"
            else:
                # Movement is unconfirmed by neighbors
                for f in findings:
                    if f.category in ("DISPLACEMENT", "VELOCITY", "ACCELERATION") and f.uncertainty == "MODERATE_SINGLE_NODE":
                        f.uncertainty = "UNCONFIRMED_SINGLE_POINT"

    return findings
