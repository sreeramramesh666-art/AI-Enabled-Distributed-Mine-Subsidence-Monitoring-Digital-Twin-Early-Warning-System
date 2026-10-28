from datetime import datetime, timezone
import json
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SensorNode(Base):
    __tablename__ = "sensor_nodes"

    node_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    node_type = Column(String(64), default="multiparameter", nullable=False)
    installation_location = Column(String(256), nullable=True)
    mine_panel = Column(String(64), nullable=True, index=True)  # e.g. "Panel-North-01", "Panel-West-03"
    depth_m = Column(Float, nullable=True)  # e.g. 185.0 metres
    extraction_method = Column(String(64), nullable=True)  # e.g. "Longwall Retreading", "Bord and Pillar"
    geological_context = Column(String(256), nullable=True)  # e.g. "Sandstone Overburden, 40m from Fault F-2"
    sampling_interval_sec = Column(Float, default=5.0, nullable=False)
    last_calibration_date = Column(DateTime, nullable=True)
    calibration_status = Column(String(32), default="nominal", nullable=False)  # nominal, calibrating, degraded, suspect
    firmware_version = Column(String(32), default="v1.0.0", nullable=True)
    last_seen = Column(DateTime, nullable=True)
    battery_pct = Column(Float, nullable=True)
    connectivity_status = Column(String(32), default="OFFLINE", nullable=False)  # ONLINE, STALE, OFFLINE
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    telemetry = relationship("TelemetryRecord", back_populates="node", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="node", cascade="all, delete-orphan")
    baseline = relationship("NodeBaseline", back_populates="node", uselist=False, cascade="all, delete-orphan")


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    node_id = Column(String(64), ForeignKey("sensor_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    test_run_id = Column(String(64), ForeignKey("test_runs.test_run_id", ondelete="SET NULL"), nullable=True, index=True)
    sequence_number = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=utc_now, nullable=False)

    # Physical measurements (SI units, nullable to ensure missing is never 0.0)
    displacement_mm = Column(Float, nullable=True)
    tilt_x_deg = Column(Float, nullable=True)
    tilt_y_deg = Column(Float, nullable=True)
    vector_tilt_deg = Column(Float, nullable=True)
    velocity_mm_hr = Column(Float, nullable=True)
    acceleration_mm_hr2 = Column(Float, nullable=True)
    vibration_rms_ms2 = Column(Float, nullable=True)
    peak_acceleration_ms2 = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    crack_width_mm = Column(Float, nullable=True)
    battery_voltage_v = Column(Float, nullable=True)
    battery_pct = Column(Float, nullable=True)

    # Baseline-relative derived values
    baseline_relative_displacement_mm = Column(Float, nullable=True)
    baseline_relative_tilt_deg = Column(Float, nullable=True)

    # Quality and provenance
    sensor_quality_state = Column(String(32), default="valid", nullable=False)  # valid, stale, uncalibrated, out_of_range, suspect
    sensor_quality = Column(JSON, nullable=True)
    data_source = Column(String(32), default="rest", nullable=False)  # simulator, rest, mqtt, imported, testrig
    calibration_status = Column(String(32), default="nominal", nullable=True)
    is_interpolated = Column(Boolean, default=False, nullable=False)
    raw_metadata = Column(JSON, nullable=True)

    node = relationship("SensorNode", back_populates="telemetry")
    test_run = relationship("TestRun", back_populates="telemetry_records")

    __table_args__ = (
        Index("idx_node_timestamp", "node_id", "timestamp"),
        Index("idx_node_seq", "node_id", "sequence_number"),
        Index("idx_test_run", "test_run_id"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, index=True, nullable=False)
    node_id = Column(String(64), ForeignKey("sensor_nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    test_run_id = Column(String(64), ForeignKey("test_runs.test_run_id", ondelete="SET NULL"), nullable=True, index=True)
    mine_panel = Column(String(64), nullable=True, index=True)
    sensor_type = Column(String(64), nullable=True)  # DISPLACEMENT, TILT, VIBRATION, CRACK, COMBINED
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, WARNING, WATCH, DATA_UNRELIABLE, INFO
    category = Column(String(32), nullable=False, index=True)  # DISPLACEMENT, VELOCITY, ACCELERATION, TILT, VIBRATION, SENSOR_DRIFT, BATTERY, STALE_DATA
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE (NEW), ACKNOWLEDGED, UNDER_INVESTIGATION, RESOLVED, REOPENED
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)
    trend_evidence = Column(JSON, nullable=True)
    triggering_rule = Column(String(128), nullable=False)

    acknowledged_by = Column(String(128), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledgement_note = Column(Text, nullable=True)

    investigated_by = Column(String(128), nullable=True)
    investigated_at = Column(DateTime, nullable=True)
    investigation_notes = Column(Text, nullable=True)

    resolved_by = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    reopened_by = Column(String(128), nullable=True)
    reopened_at = Column(DateTime, nullable=True)
    reopen_notes = Column(Text, nullable=True)

    lifecycle_history = Column(JSON, nullable=True)

    node = relationship("SensorNode", back_populates="alerts")
    test_run = relationship("TestRun", back_populates="alerts")


class NodeBaseline(Base):
    __tablename__ = "node_baselines"

    node_id = Column(String(64), ForeignKey("sensor_nodes.node_id", ondelete="CASCADE"), primary_key=True)
    calculation_period_start = Column(DateTime, nullable=True)
    calculation_period_end = Column(DateTime, nullable=True)
    sample_count = Column(Integer, default=0, nullable=False)

    displacement_mean = Column(Float, nullable=True)
    displacement_std = Column(Float, nullable=True)
    tilt_x_mean = Column(Float, nullable=True)
    tilt_x_std = Column(Float, nullable=True)
    tilt_y_mean = Column(Float, nullable=True)
    tilt_y_std = Column(Float, nullable=True)
    temperature_mean = Column(Float, nullable=True)

    is_valid = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    node = relationship("SensorNode", back_populates="baseline")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    category = Column(String(64), nullable=False)
    node_id = Column(String(64), nullable=True, index=True)
    alert_id = Column(String(64), nullable=True, index=True)
    actor = Column(String(128), default="system", nullable=False)
    action = Column(String(128), nullable=False)
    outcome = Column(String(32), default="SUCCESS", nullable=False)
    details = Column(JSON, nullable=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_run_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    scenario = Column(String(64), nullable=False)
    test_conditions = Column(String(256), nullable=False)
    target_node_id = Column(String(64), nullable=True)
    status = Column(String(32), default="RUNNING", nullable=False, index=True)  # RUNNING, COMPLETED, ABORTED
    start_time = Column(DateTime, default=utc_now, nullable=False)
    end_time = Column(DateTime, nullable=True)

    intended_movement_mm = Column(Float, nullable=True)
    reference_movement_mm = Column(Float, nullable=True)
    sensor_reported_movement_mm = Column(Float, nullable=True)
    measurement_error_mm = Column(Float, nullable=True)
    detection_latency_sec = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    telemetry_records = relationship("TelemetryRecord", back_populates="test_run")
    alerts = relationship("Alert", back_populates="test_run")

