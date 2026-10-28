import math
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.models import SensorNode, NodeBaseline, TelemetryRecord, Alert, AuditEvent
from backend.app.schemas.telemetry import TelemetryIngest
from backend.app.services.node_service import NodeService
from backend.app.services.alert_service import AlertService
from backend.app.services.telemetry_service import TelemetryService
from backend.app.analytics.rules import (
    compute_kinematics,
    compute_vector_tilt,
    evaluate_geotechnical_rules,
    haversine_distance_m,
    RuleFinding
)
from backend.app.analytics.risk_scoring import calculate_risk_profile
from backend.app.analytics.anomaly_detection import MultivariateAnomalyDetector


def test_node_baseline_establishment_and_storage(db_session: Session):
    """
    Verify establishing, computing, and persisting per-node baseline statistics.
    Validates mean/std calculation, sample threshold, and audit trail logging.
    """
    node_id = "TEST-NODE-01"
    now = datetime.now(timezone.utc)

    # 1. Insert 10 synthetic baseline records with known parameters
    # Displacement ~ 2.50 mm (values 2.0 to 3.0), tilt_x ~ 0.40 deg, tilt_y ~ 0.30 deg
    displacements = [2.0, 2.2, 2.4, 2.5, 2.5, 2.6, 2.7, 2.7, 2.8, 3.0]
    expected_mean = sum(displacements) / len(displacements)  # 2.54 mm

    for i, d in enumerate(displacements):
        rec = TelemetryRecord(
            event_id=str(uuid.uuid4()),
            node_id=node_id,
            sequence_number=i + 1,
            timestamp=now - timedelta(hours=10 - i),
            received_at=now - timedelta(hours=10 - i),
            displacement_mm=d,
            tilt_x_deg=0.40,
            tilt_y_deg=0.30,
            temperature_c=25.0,
            data_source="simulator"
        )
        db_session.add(rec)
    db_session.commit()

    # 2. Recalculate baseline over 24-hour window
    baseline = NodeService.recalculate_baseline(db=db_session, node_id=node_id, period_hours=24.0)

    assert baseline is not None
    assert baseline.is_valid is True
    assert baseline.sample_count == 10
    assert baseline.displacement_mean == pytest.approx(expected_mean, rel=1e-3)
    assert baseline.tilt_x_mean == pytest.approx(0.40, rel=1e-3)
    assert baseline.tilt_y_mean == pytest.approx(0.30, rel=1e-3)
    assert baseline.displacement_std is not None
    assert baseline.displacement_std > 0.0

    # 3. Verify AuditEvent created
    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.node_id == node_id, AuditEvent.action == "RECALCULATE_BASELINE")
        .first()
    )
    assert audit is not None
    assert audit.outcome == "SUCCESS"
    assert audit.details["sample_count"] == 10

    # 4. Insufficient data test: create a new node with only 2 records (< 5 threshold)
    new_node_id = "SPARSE-NODE-01"
    sparse_node = SensorNode(
        node_id=new_node_id,
        name="Sparse Telemetry Node",
        latitude=23.75,
        longitude=86.42,
        is_enabled=True
    )
    db_session.add(sparse_node)
    for i in range(2):
        db_session.add(TelemetryRecord(
            event_id=str(uuid.uuid4()),
            node_id=new_node_id,
            sequence_number=i + 1,
            timestamp=now - timedelta(minutes=10 - i),
            received_at=now - timedelta(minutes=10 - i),
            displacement_mm=1.0
        ))
    db_session.commit()

    sparse_baseline = NodeService.recalculate_baseline(db=db_session, node_id=new_node_id, period_hours=24.0)
    assert sparse_baseline is not None
    assert sparse_baseline.is_valid is False
    assert sparse_baseline.sample_count == 2


def test_kinematics_derivation_actual_timestamps():
    """
    Calculate deformation velocity (mm/hr) and acceleration (mm/hr^2) using actual timestamps.
    Handles irregular sampling intervals and sub-second interval guards.
    """
    t0 = datetime(2026, 10, 28, 6, 0, 0, tzinfo=timezone.utc)

    # Initial frame
    r0 = TelemetryRecord(
        node_id="NODE-KIN",
        timestamp=t0,
        displacement_mm=10.0,
        velocity_mm_hr=None
    )

    # Case A: 120 seconds later (0.03333 hours), displacement moves +0.5 mm
    # Expected v = 0.5 mm / (120/3600 hr) = 0.5 * 30 = 15.0 mm/hr
    t1 = t0 + timedelta(seconds=120)
    v1, a1 = compute_kinematics(current_time=t1, current_disp=10.5, prev_record=r0)
    assert v1 == pytest.approx(15.0, rel=1e-3)
    assert a1 is None  # No prior velocity to derive acceleration

    # Case B: 180 seconds after t1 (0.05 hours), displacement moves +1.5 mm
    # New v2 = 1.5 mm / (180/3600 hr) = 1.5 * 20 = 30.0 mm/hr
    # Acceleration a = (30.0 - 15.0) / 0.05 hr = 15.0 / 0.05 = 300.0 mm/hr^2
    r1 = TelemetryRecord(
        node_id="NODE-KIN",
        timestamp=t1,
        displacement_mm=10.5,
        velocity_mm_hr=v1
    )
    t2 = t1 + timedelta(seconds=180)
    v2, a2, diag = compute_kinematics(current_time=t2, current_disp=12.0, prev_record=r1, include_diagnostics=True)
    assert v2 == pytest.approx(30.0, rel=1e-3)
    assert a2 == pytest.approx(300.0, rel=1e-3)
    assert diag["dt_hours"] == pytest.approx(0.05, rel=1e-3)
    assert diag["is_accelerating"] is True

    # Case C: Sub-second guard (interval < 0.5 sec) to avoid near-zero division noise
    r2 = TelemetryRecord(node_id="NODE-KIN", timestamp=t2, displacement_mm=12.0)
    t_instant = t2 + timedelta(milliseconds=200)
    v_guard, a_guard = compute_kinematics(current_time=t_instant, current_disp=12.1, prev_record=r2)
    assert v_guard is None
    assert a_guard is None


def test_stable_baseline_data_no_false_alerts():
    """
    Synthetic series with minor zero-mean measurement noise (+/- 0.02 mm).
    Must NOT trigger any alerts, and risk profile must be strictly NORMAL.
    """
    now = datetime.now(timezone.utc)
    quality = {"is_physically_bounded": True, "has_missing_data": False}

    # Stable readings: displacement 0.02 mm, vector tilt 0.1 deg, zero vibration
    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=0.02,
        vector_tilt_deg=0.1,
        velocity_mm_hr=0.01,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.05,
        battery_pct=95.0,
        quality=quality
    )
    assert len(findings) == 0

    risk = calculate_risk_profile(
        displacement_mm=0.02,
        velocity_mm_hr=0.01,
        acceleration_mm_hr2=0.0,
        vector_tilt_deg=0.1,
        quality=quality,
        connectivity_status="ONLINE"
    )
    assert risk.category == "NORMAL"
    assert risk.overall_score < 20.0
    assert risk.data_quality_score == 100.0
    assert len(risk.active_indicators) == 0


def test_gradual_subsidence_threshold_crossings():
    """
    Verify gradual cumulative deformation crossing warning (15 mm) and critical (30 mm) thresholds,
    both with raw displacement and with baseline datum subtraction.
    """
    now = datetime.now(timezone.utc)
    quality = {"is_physically_bounded": True, "has_missing_data": False}

    # 1. Below warning threshold (14.5 mm < 15.0 mm)
    findings_safe = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=14.5,
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.5,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality=quality
    )
    disp_findings_safe = [f for f in findings_safe if f.category == "DISPLACEMENT"]
    assert len(disp_findings_safe) == 0

    # 2. Warning crossing (15.5 mm >= 15.0 mm)
    findings_warn = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=15.5,
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.5,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality=quality
    )
    disp_warn = [f for f in findings_warn if f.triggering_rule == "RULE_WARNING_DISPLACEMENT"]
    assert len(disp_warn) == 1
    assert disp_warn[0].severity == "WARNING"
    assert disp_warn[0].evidence["measurements"]["displacement_mm"] == 15.5

    # 3. Critical crossing (31.0 mm >= 30.0 mm)
    findings_crit = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=31.0,
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.5,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality=quality
    )
    disp_crit = [f for f in findings_crit if f.triggering_rule == "RULE_CRITICAL_DISPLACEMENT"]
    assert len(disp_crit) == 1
    assert disp_crit[0].severity == "CRITICAL"

    # 4. Baseline datum offset compensation:
    # Sensor installed at raw 10.0 mm datum. Current reading 22.0 mm -> net displacement 12.0 mm (< 15.0 mm warning)
    baseline = NodeBaseline(
        node_id="TEST-NODE-01",
        displacement_mean=10.0,
        is_valid=True,
        sample_count=50
    )
    findings_offset_safe = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=22.0,
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.5,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality=quality,
        baseline=baseline
    )
    disp_offset_safe = [f for f in findings_offset_safe if f.category == "DISPLACEMENT"]
    assert len(disp_offset_safe) == 0

    # Current reading 26.0 mm -> net displacement 16.0 mm (>= 15.0 mm warning)
    findings_offset_warn = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=26.0,
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.5,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality=quality,
        baseline=baseline
    )
    disp_offset_warn = [f for f in findings_offset_warn if f.triggering_rule == "RULE_WARNING_DISPLACEMENT"]
    assert len(disp_offset_warn) == 1
    assert disp_offset_warn[0].evidence["baseline_offset_mm"] == 10.0
    assert disp_offset_warn[0].evidence["net_displacement_mm"] == 16.0


def test_accelerating_movement_tertiary_creep():
    """
    Tertiary creep: acceleration >= 0.5 mm/hr^2 combined with velocity > 0.1 mm/hr.
    Must trigger RULE_CRITICAL_ACCELERATION with HIGH_CONFIDENCE_PHYSICAL uncertainty.
    """
    now = datetime.now(timezone.utc)
    quality = {"is_physically_bounded": True, "has_missing_data": False}

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=8.0,
        vector_tilt_deg=1.2,
        velocity_mm_hr=1.5,
        acceleration_mm_hr2=0.85,  # >= 0.5 mm/hr^2
        vibration_rms_ms2=0.2,
        battery_pct=88.0,
        quality=quality
    )
    accel_findings = [f for f in findings if f.triggering_rule == "RULE_CRITICAL_ACCELERATION"]
    assert len(accel_findings) == 1
    assert accel_findings[0].severity == "CRITICAL"
    assert accel_findings[0].category == "ACCELERATION"
    assert "Tertiary Creep" in accel_findings[0].title
    assert accel_findings[0].uncertainty == "HIGH_CONFIDENCE_PHYSICAL"
    assert accel_findings[0].evidence["model_metadata"]["is_probability_of_collapse"] is False


def test_sudden_step_fault_slip():
    """
    Sudden step displacement increment >= 8.0 mm within short time window (<= 300s).
    Simulates abrupt shear displacement / fault slip.
    """
    t0 = datetime(2026, 10, 28, 8, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=25)

    prev = TelemetryRecord(
        node_id="TEST-NODE-01",
        timestamp=t0,
        displacement_mm=2.0
    )

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=t1,
        displacement_mm=11.2,  # delta = 9.2 mm >= 8.0 mm
        vector_tilt_deg=0.5,
        velocity_mm_hr=None,
        acceleration_mm_hr2=None,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        prev_record=prev
    )

    slip_findings = [f for f in findings if f.triggering_rule == "RULE_SUDDEN_FAULT_SLIP"]
    assert len(slip_findings) == 1
    assert slip_findings[0].severity == "CRITICAL"
    assert slip_findings[0].category == "DISPLACEMENT"
    assert slip_findings[0].evidence["step_delta_mm"] == pytest.approx(9.2, rel=1e-3)
    assert slip_findings[0].evidence["step_duration_sec"] == 25.0


def test_vibration_without_displacement_blasting_discrimination():
    """
    Distinguishes transient production blasting vibration from ground subsidence.
    High dynamic vibration (>= 3.0 m/s^2) with negligible displacement (|delta d| <= 0.15 mm)
    must trigger RULE_TRANSIENT_BLASTING_VIBRATION (severity WATCH) and NOT physical subsidence alerts.
    """
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=10)

    prev = TelemetryRecord(
        node_id="TEST-NODE-01",
        timestamp=t0,
        displacement_mm=5.00
    )

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=t1,
        displacement_mm=5.02,  # delta = 0.02 mm <= 0.15 mm
        vector_tilt_deg=0.2,
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=7.8,  # High dynamic vibration >= 3.0 m/s^2
        battery_pct=95.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        prev_record=prev
    )

    blast_findings = [f for f in findings if f.triggering_rule == "RULE_TRANSIENT_BLASTING_VIBRATION"]
    assert len(blast_findings) == 1
    assert blast_findings[0].severity == "WATCH"
    assert blast_findings[0].uncertainty == "HIGH_CONFIDENCE_BLAST_DISCRIMINATION"

    # CRITICAL: Verify NO critical subsidence alert was generated
    assert not any(f.triggering_rule == "RULE_CRITICAL_DISPLACEMENT" for f in findings)
    assert not any(f.triggering_rule == "RULE_CRITICAL_ACCELERATION" for f in findings)


def test_anti_false_safe_missing_and_stale_data():
    """
    Verify that missing measurements, stale telemetry, or offline nodes
    CANNOT silently produce a false 'NORMAL' or 'SAFE' status.
    """
    # 1. Missing physical channels (both displacement and tilt are None)
    risk_missing = calculate_risk_profile(
        displacement_mm=None,
        velocity_mm_hr=None,
        acceleration_mm_hr2=None,
        vector_tilt_deg=None,
        quality={"is_physically_bounded": True, "has_missing_data": True},
        connectivity_status="ONLINE"
    )
    assert risk_missing.category == "DATA_UNRELIABLE"
    assert risk_missing.data_quality_score <= 20.0
    assert "NO_PHYSICAL_MEASUREMENTS" in risk_missing.active_indicators

    # 2. Stale data (even if historical displacement was zero)
    risk_stale = calculate_risk_profile(
        displacement_mm=0.0,
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vector_tilt_deg=0.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        connectivity_status="STALE"
    )
    assert risk_stale.category == "DATA_UNRELIABLE"
    assert "STALE_DATA_HEARTBEAT" in risk_stale.active_indicators

    # 3. Offline node
    risk_offline = calculate_risk_profile(
        displacement_mm=0.0,
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vector_tilt_deg=0.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        connectivity_status="OFFLINE"
    )
    assert risk_offline.category == "DATA_UNRELIABLE"
    assert risk_offline.data_quality_score == 0.0
    assert "NODE_OFFLINE" in risk_offline.active_indicators


def test_faulty_sensors_frozen_transducer_output():
    """
    Frozen output: 5 successive bitwise-identical displacement readings.
    Must trigger RULE_FROZEN_SENSOR with DATA_UNRELIABLE severity.
    """
    now = datetime.now(timezone.utc)
    identical_val = 6.7891

    recent_history = [
        TelemetryRecord(
            node_id="TEST-NODE-01",
            timestamp=now - timedelta(seconds=(5 - i) * 30),
            displacement_mm=identical_val
        )
        for i in range(5)
    ]

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=identical_val,  # 6th identical measurement
        vector_tilt_deg=0.5,
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.0,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        recent_history=recent_history
    )

    frozen = [f for f in findings if f.triggering_rule == "RULE_FROZEN_SENSOR"]
    assert len(frozen) == 1
    assert frozen[0].severity == "DATA_UNRELIABLE"
    assert frozen[0].category == "SENSOR_DRIFT"
    assert frozen[0].uncertainty == "FROZEN_SENSOR_ERROR"


def test_faulty_sensors_monotonic_electronic_drift():
    """
    Electronic drift: tilt monotonically increases >= 0.8 deg over >= 6 observations
    while vertical ground displacement remains strictly zero (<= 0.1 mm).
    Must trigger RULE_SENSOR_DRIFT (severity WATCH).
    """
    now = datetime.now(timezone.utc)
    tilt_values = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2]

    recent_history = [
        TelemetryRecord(
            node_id="TEST-NODE-01",
            timestamp=now - timedelta(minutes=(6 - i) * 5),
            tilt_x_deg=t,
            tilt_y_deg=0.0,
            displacement_mm=0.0
        )
        for i, t in enumerate(tilt_values)
    ]

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=0.0,
        vector_tilt_deg=1.4,  # total drift 1.4 - 0.2 = 1.2 >= 0.8 deg
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.0,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        recent_history=recent_history
    )

    drift = [f for f in findings if f.triggering_rule == "RULE_SENSOR_DRIFT"]
    assert len(drift) == 1
    assert drift[0].severity == "WATCH"
    assert drift[0].category == "SENSOR_DRIFT"
    assert drift[0].uncertainty == "HIGH_UNCERTAINTY_DRIFT"


def test_sensor_disagreement_cross_channel():
    """
    Sensor disagreement: sudden large rotational tilt shift (>= 2.5 deg)
    with negligible vertical displacement increment (<= 0.08 mm).
    Indicates mechanical bracket disturbance or sensor malfunction.
    """
    t0 = datetime.now(timezone.utc)
    t1 = t0 + timedelta(seconds=60)

    prev = TelemetryRecord(
        node_id="TEST-NODE-01",
        timestamp=t0,
        displacement_mm=3.00,
        tilt_x_deg=0.2,
        tilt_y_deg=0.2
    )

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=t1,
        displacement_mm=3.01,  # delta = 0.01 mm
        vector_tilt_deg=3.2,   # delta tilt = ~2.92 deg >= 2.5 deg
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.05,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        prev_record=prev
    )

    disagree = [f for f in findings if f.triggering_rule == "RULE_SENSOR_DISAGREEMENT_TILT"]
    assert len(disagree) == 1
    assert disagree[0].severity == "WARNING"
    assert disagree[0].uncertainty == "INSTRUMENT_DISAGREEMENT"


def test_persistent_inclinometer_baseline_departure():
    """
    Persistent baseline tilt departure: resultant tilt shifts >= 2.0 deg relative
    to the calibrated initial baseline window.
    """
    now = datetime.now(timezone.utc)
    baseline = NodeBaseline(
        node_id="TEST-NODE-01",
        tilt_x_mean=0.30,
        tilt_y_mean=0.20,
        is_valid=True,
        sample_count=80
    )

    findings = evaluate_geotechnical_rules(
        node_id="TEST-NODE-01",
        timestamp=now,
        displacement_mm=2.0,
        vector_tilt_deg=None,
        velocity_mm_hr=0.0,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=92.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        baseline=baseline,
        tilt_x_deg=2.50,  # dx = 2.20
        tilt_y_deg=1.80   # dy = 1.60 -> offset = sqrt(2.2^2 + 1.6^2) = 2.72 deg >= 2.0 deg
    )

    tilt_shift = [f for f in findings if f.triggering_rule == "RULE_PERSISTENT_TILT_SHIFT"]
    assert len(tilt_shift) == 1
    assert tilt_shift[0].severity == "WARNING"
    assert tilt_shift[0].category == "TILT"
    assert tilt_shift[0].evidence["tilt_offset_from_baseline_deg"] >= 2.0


def test_spatial_neighbor_corroboration():
    """
    Spatial corroboration across neighbouring nodes:
    When a target node undergoes elevated movement and a neighbouring node
    within 500m also exhibits elevated movement, trigger RULE_MACRO_SUBSIDENCE_CORROBORATED.
    """
    now = datetime.now(timezone.utc)

    # 1. Target node moving (displacement = 16.0 mm >= 15.0 mm warning threshold)
    # Neighbour within 150m is ALSO moving (displacement = 18.0 mm)
    spatial_neighbors_active = [
        {
            "node_id": "NODE-BENCH-02",
            "distance_m": 125.0,
            "displacement_mm": 18.0,
            "velocity_mm_hr": 3.2,
            "timestamp": now
        }
    ]

    findings_corroborated = evaluate_geotechnical_rules(
        node_id="NODE-BENCH-01",
        timestamp=now,
        displacement_mm=16.0,
        vector_tilt_deg=0.5,
        velocity_mm_hr=1.2,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        spatial_neighbors=spatial_neighbors_active
    )

    macro_subs = [f for f in findings_corroborated if f.triggering_rule == "RULE_MACRO_SUBSIDENCE_CORROBORATED"]
    assert len(macro_subs) == 1
    assert macro_subs[0].severity == "CRITICAL"
    assert macro_subs[0].uncertainty == "HIGH_CONFIDENCE_CORROBORATED"
    assert "NODE-BENCH-02" in macro_subs[0].evidence["corroborating_nodes"]

    # 2. In contrast, if neighbour within radius is STABLE (displacement = 0.5 mm),
    # movement is classified as UNCONFIRMED_SINGLE_POINT
    spatial_neighbors_stable = [
        {
            "node_id": "NODE-BENCH-02",
            "distance_m": 125.0,
            "displacement_mm": 0.5,
            "velocity_mm_hr": 0.0,
            "timestamp": now
        }
    ]

    findings_unconfirmed = evaluate_geotechnical_rules(
        node_id="NODE-BENCH-01",
        timestamp=now,
        displacement_mm=16.0,
        vector_tilt_deg=0.5,
        velocity_mm_hr=1.2,
        acceleration_mm_hr2=0.0,
        vibration_rms_ms2=0.1,
        battery_pct=90.0,
        quality={"is_physically_bounded": True, "has_missing_data": False},
        spatial_neighbors=spatial_neighbors_stable
    )

    assert not any(f.triggering_rule == "RULE_MACRO_SUBSIDENCE_CORROBORATED" for f in findings_unconfirmed)
    disp_unconfirmed = [f for f in findings_unconfirmed if f.category == "DISPLACEMENT"]
    assert len(disp_unconfirmed) >= 1
    assert disp_unconfirmed[0].uncertainty == "UNCONFIRMED_SINGLE_POINT"


def test_isolation_forest_anomaly_detector_training_and_disclaimer():
    """
    Multivariate Anomaly Detection via Isolation Forest:
    1. Rejects training with insufficient samples (< 30).
    2. Successfully trains with >= 30 valid samples.
    3. Detects multidimensional outliers.
    4. Guarantees output is an unsupervised decision score (-1 to 1) and NEVER a probability of collapse.
    """
    detector = MultivariateAnomalyDetector()

    # 1. Sample sufficiency guard
    sparse_data = [{"displacement_mm": 0.1 * i, "velocity_mm_hr": 0.05} for i in range(15)]
    fit_result = detector.fit_baseline(sparse_data)
    assert fit_result is False
    assert detector.is_trained is False

    is_anom, score, factor, meta = detector.predict({"displacement_mm": 10.0}, include_metadata=True)
    assert is_anom is False
    assert meta["status"] == "UNTRAINED_INSUFFICIENT_DATA"

    # 2. Train with sufficient baseline samples (40 nominal records)
    nominal_baseline = [
        {
            "displacement_mm": 1.0 + (i % 5) * 0.05,
            "tilt_x_deg": 0.2 + (i % 3) * 0.02,
            "tilt_y_deg": 0.15 + (i % 4) * 0.01,
            "velocity_mm_hr": 0.02,
            "vibration_rms_ms2": 0.05,
            "temperature_c": 22.0 + (i % 6) * 0.5
        }
        for i in range(40)
    ]
    fit_success = detector.fit_baseline(nominal_baseline)
    assert fit_success is True
    assert detector.is_trained is True
    assert detector.sample_count == 40

    # 3. Test nominal point (close to baseline manifold)
    nominal_obs = {
        "displacement_mm": 1.05,
        "tilt_x_deg": 0.22,
        "tilt_y_deg": 0.16,
        "velocity_mm_hr": 0.02,
        "vibration_rms_ms2": 0.05,
        "temperature_c": 23.0
    }
    is_nominal_anom, nom_score, _, nom_meta = detector.predict(nominal_obs, include_metadata=True)
    assert is_nominal_anom is False
    assert nom_score > 0.0  # Positive decision score = inlier

    # 4. Test extreme multidimensional outlier
    outlier_obs = {
        "displacement_mm": 28.5,
        "tilt_x_deg": 5.8,
        "tilt_y_deg": 4.2,
        "velocity_mm_hr": 8.0,
        "vibration_rms_ms2": 6.5,
        "temperature_c": 45.0
    }
    is_outlier, out_score, primary_factor, out_meta = detector.predict(outlier_obs, include_metadata=True)
    assert is_outlier is True
    assert out_score < 0.0  # Negative decision score = anomaly
    assert primary_factor is not None

    # 5. Strict safety check: Never present as collapse probability
    assert out_meta["is_probability_of_collapse"] is False
    assert "NOT an empirical probability" in out_meta["disclaimer"]

    status = detector.get_status()
    assert status["is_probability_of_collapse"] is False
    assert status["trained"] is True


def test_alert_deduplication_and_severity_escalation(db_session: Session):
    """
    Verify alert lifecycle persistence:
    1. Initial alert creation logs TRIGGER_ALERT audit.
    2. Subsequent duplicate alert within active status is deduplicated.
    3. Severity escalation (WARNING -> CRITICAL) updates alert and logs ESCALATE_ALERT audit.
    4. Explicit acknowledgement and resolution lifecycle.
    """
    node_id = "TEST-NODE-01"

    # Step 1: Create WARNING alert
    alert1 = AlertService.create_or_deduplicate_alert(
        db=db_session,
        node_id=node_id,
        severity="WARNING",
        category="DISPLACEMENT",
        title="Elevated Displacement",
        description="Ground displacement is 16.0 mm",
        triggering_rule="RULE_WARNING_DISPLACEMENT",
        evidence={"displacement_mm": 16.0}
    )
    assert alert1 is not None
    assert alert1.severity == "WARNING"
    assert alert1.status == "ACTIVE"
    alert_id = alert1.alert_id

    # Verify audit event for trigger
    trigger_audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.alert_id == alert_id, AuditEvent.action == "CREATE_ALERT")
        .first()
    )
    assert trigger_audit is not None

    # Step 2: Duplicate alert with same rule while active -> returns existing alert without creating second row
    alert2 = AlertService.create_or_deduplicate_alert(
        db=db_session,
        node_id=node_id,
        severity="WARNING",
        category="DISPLACEMENT",
        title="Elevated Displacement",
        description="Ground displacement is 17.0 mm",
        triggering_rule="RULE_WARNING_DISPLACEMENT",
        evidence={"displacement_mm": 17.0}
    )
    assert alert2 is not None
    assert alert2.alert_id == alert_id

    active_count = db_session.query(Alert).filter(Alert.node_id == node_id, Alert.status == "ACTIVE").count()
    assert active_count == 1

    # Step 3: Escalation: movement worsens to CRITICAL for this node/category
    alert3 = AlertService.create_or_deduplicate_alert(
        db=db_session,
        node_id=node_id,
        severity="CRITICAL",
        category="DISPLACEMENT",
        title="Critical Subsidence Displacement",
        description="Ground displacement is 32.0 mm",
        triggering_rule="RULE_CRITICAL_DISPLACEMENT",
        evidence={"displacement_mm": 32.0}
    )
    assert alert3 is not None
    assert alert3.alert_id == alert_id  # Escalated in-place
    assert alert3.severity == "CRITICAL"

    escalate_audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.alert_id == alert_id, AuditEvent.action == "ESCALATE_ALERT")
        .first()
    )
    assert escalate_audit is not None
    assert escalate_audit.details["old_severity"] == "WARNING"
    assert escalate_audit.details["new_severity"] == "CRITICAL"

    # Step 4: Acknowledge alert
    ack_alert = AlertService.acknowledge_alert(
        db=db_session,
        alert_id=alert_id,
        actor="geotech_engineer_alpha"
    )
    assert ack_alert.status == "ACKNOWLEDGED"
    assert ack_alert.acknowledged_by == "geotech_engineer_alpha"

    ack_audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.alert_id == alert_id, AuditEvent.action == "ACKNOWLEDGE_ALERT")
        .first()
    )
    assert ack_audit is not None

    # Step 5: Resolve alert
    res_alert = AlertService.resolve_alert(
        db=db_session,
        alert_id=alert_id,
        actor="geotech_engineer_alpha",
        resolution_notes="Bench visual inspection completed. Discontinuity stabilized."
    )
    assert res_alert.status == "RESOLVED"
    assert res_alert.resolved_by == "geotech_engineer_alpha"

    res_audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.alert_id == alert_id, AuditEvent.action == "RESOLVE_ALERT")
        .first()
    )
    assert res_audit is not None
