import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.models import SensorNode, TelemetryRecord, AuditEvent
from backend.app.schemas.telemetry import TelemetryIngest, TelemetryBatchIngest, TelemetryBatchResponse
from backend.app.ingestion.message_validation import validate_physical_measurements
from backend.app.ingestion.deduplication import DeduplicationChecker
from backend.app.analytics.rules import (
    compute_vector_tilt, compute_kinematics, evaluate_geotechnical_rules
)
from backend.app.analytics.risk_scoring import calculate_risk_profile
from backend.app.analytics.anomaly_detection import ml_detector
from backend.app.services.alert_service import AlertService
from backend.app.realtime.websocket_manager import ws_manager

logger = logging.getLogger("mineguard.telemetry")


class TelemetryService:
    @staticmethod
    async def process_single_telemetry(
        db: Session,
        telemetry: TelemetryIngest,
        skip_ws: bool = False
    ) -> Tuple[Optional[TelemetryRecord], Optional[str], bool]:
        """
        Process and persist a single telemetry frame.
        Returns: (record, error_message, was_duplicate)
        """
        # 1. Verify registered node exists
        node = db.query(SensorNode).filter(SensorNode.node_id == telemetry.node_id).first()
        if not node:
            return None, f"Node '{telemetry.node_id}' is not registered.", False

        if not node.is_enabled:
            return None, f"Node '{telemetry.node_id}' is disabled.", False

        # 2. Check for duplicate observation
        is_dup = DeduplicationChecker.is_duplicate(
            db=db,
            event_id=telemetry.event_id,
            node_id=telemetry.node_id,
            sequence_number=telemetry.sequence_number
        )
        if is_dup:
            return None, "Duplicate observation detected.", True

        # 3. Validate physical bounds without silent mutation
        is_valid, err_msg, quality = validate_physical_measurements(telemetry)
        if not is_valid:
            logger.warning(f"Telemetry validation failed for node {telemetry.node_id}: {err_msg}")
            return None, err_msg, False

        # 4. Compute vector tilt
        vector_tilt = compute_vector_tilt(telemetry.tilt_x_deg, telemetry.tilt_y_deg)

        # 5. Fetch previous valid record for kinematics calculation
        ts_utc = telemetry.timestamp.replace(tzinfo=timezone.utc) if telemetry.timestamp.tzinfo is None else telemetry.timestamp
        prev_record = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == telemetry.node_id,
                TelemetryRecord.timestamp < ts_utc
            )
            .order_by(desc(TelemetryRecord.timestamp))
            .first()
        )

        velocity_mm_hr, accel_mm_hr2 = compute_kinematics(
            current_time=ts_utc,
            current_disp=telemetry.displacement_mm,
            prev_record=prev_record
        )

        # 6. Create TelemetryRecord
        now_utc = datetime.now(timezone.utc)
        record = TelemetryRecord(
            event_id=telemetry.event_id,
            node_id=telemetry.node_id,
            sequence_number=telemetry.sequence_number,
            timestamp=ts_utc,
            received_at=now_utc,
            displacement_mm=telemetry.displacement_mm,
            tilt_x_deg=telemetry.tilt_x_deg,
            tilt_y_deg=telemetry.tilt_y_deg,
            vector_tilt_deg=vector_tilt,
            velocity_mm_hr=velocity_mm_hr,
            acceleration_mm_hr2=accel_mm_hr2,
            vibration_rms_ms2=telemetry.vibration_rms_ms2,
            peak_acceleration_ms2=telemetry.peak_acceleration_ms2,
            temperature_c=telemetry.temperature_c,
            crack_width_mm=telemetry.crack_width_mm,
            battery_voltage_v=telemetry.battery_voltage_v,
            battery_pct=telemetry.battery_pct,
            sensor_quality=quality,
            data_source=telemetry.data_source,
            calibration_status=telemetry.calibration_status,
            raw_metadata=telemetry.raw_metadata
        )
        db.add(record)

        # 7. Update node health
        if node.last_seen is None or ts_utc >= node.last_seen.replace(tzinfo=timezone.utc if node.last_seen.tzinfo is None else None):
            node.last_seen = ts_utc
            node.connectivity_status = "ONLINE"
            if telemetry.battery_pct is not None:
                node.battery_pct = telemetry.battery_pct

        # 8. Evaluate Geotechnical Rules
        findings = evaluate_geotechnical_rules(
            node_id=telemetry.node_id,
            timestamp=ts_utc,
            displacement_mm=telemetry.displacement_mm,
            vector_tilt_deg=vector_tilt,
            velocity_mm_hr=velocity_mm_hr,
            acceleration_mm_hr2=accel_mm_hr2,
            vibration_rms_ms2=telemetry.vibration_rms_ms2,
            battery_pct=telemetry.battery_pct,
            quality=quality
        )

        # 9. Optional ML multivariate anomaly check
        obs_dict = {
            "displacement_mm": telemetry.displacement_mm,
            "tilt_x_deg": telemetry.tilt_x_deg,
            "tilt_y_deg": telemetry.tilt_y_deg,
            "velocity_mm_hr": velocity_mm_hr,
            "vibration_rms_ms2": telemetry.vibration_rms_ms2,
            "temperature_c": telemetry.temperature_c
        }
        is_ml_anomaly, ml_score, ml_factor = ml_detector.predict(obs_dict)
        if is_ml_anomaly:
            from backend.app.analytics.rules import RuleFinding
            findings.append(RuleFinding(
                severity="WATCH",
                category="SENSOR_DRIFT",
                title=f"Multivariate Anomaly Detected by Isolation Forest (Top Feature: {ml_factor})",
                description=f"Isolation forest detected multi-sensor pattern divergence. Anomaly score: {ml_score:.3f}. Primary factor: {ml_factor}.",
                triggering_rule="ML_ISOLATION_FOREST",
                evidence={"score": ml_score, "primary_factor": ml_factor}
            ))

        # 10. Persist alerts
        new_alerts = []
        for finding in findings:
            alert = AlertService.create_or_deduplicate_alert(
                db=db,
                node_id=telemetry.node_id,
                severity=finding.severity,
                category=finding.category,
                title=finding.title,
                description=finding.description,
                triggering_rule=finding.triggering_rule,
                evidence=finding.evidence
            )
            if alert:
                new_alerts.append(alert)

        db.commit()
        db.refresh(record)

        # 11. Broadcast to WebSocket clients
        if not skip_ws:
            # Telemetry broadcast
            await ws_manager.broadcast("telemetry", {
                "id": record.id,
                "event_id": record.event_id,
                "node_id": record.node_id,
                "timestamp": record.timestamp.isoformat(),
                "displacement_mm": record.displacement_mm,
                "velocity_mm_hr": record.velocity_mm_hr,
                "acceleration_mm_hr2": record.acceleration_mm_hr2,
                "vector_tilt_deg": record.vector_tilt_deg,
                "vibration_rms_ms2": record.vibration_rms_ms2,
                "temperature_c": record.temperature_c,
                "battery_pct": record.battery_pct,
                "data_source": record.data_source
            })

            # Alert broadcast if any
            for a in new_alerts:
                await ws_manager.broadcast("alert", {
                    "alert_id": a.alert_id,
                    "node_id": a.node_id,
                    "severity": a.severity,
                    "category": a.category,
                    "title": a.title,
                    "description": a.description,
                    "created_at": a.created_at.isoformat()
                })

        return record, None, False

    @staticmethod
    async def process_batch_telemetry(
        db: Session,
        batch: TelemetryBatchIngest
    ) -> TelemetryBatchResponse:
        """
        Process array of telemetry frames atomically.
        Used by gateways during network replay.
        """
        ingested_count = 0
        duplicates_skipped = 0
        errors = []

        # Sort batch by timestamp to ensure chronological kinematics derivation
        sorted_records = sorted(batch.records, key=lambda r: r.timestamp)

        for item in sorted_records:
            try:
                record, err, was_dup = await TelemetryService.process_single_telemetry(
                    db=db,
                    telemetry=item,
                    skip_ws=False
                )
                if was_dup:
                    duplicates_skipped += 1
                elif err:
                    errors.append(f"Node {item.node_id} seq {item.sequence_number}: {err}")
                elif record:
                    ingested_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"Error ingesting item {item.event_id}: {e}")
                errors.append(f"Unexpected error: {str(e)}")

        return TelemetryBatchResponse(
            ingested_count=ingested_count,
            duplicates_skipped=duplicates_skipped,
            errors=errors
        )
