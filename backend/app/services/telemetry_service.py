import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.app.core.config import settings
from backend.app.db.models import SensorNode, TelemetryRecord, AuditEvent, NodeBaseline
from backend.app.schemas.telemetry import (
    TelemetryIngest, TelemetryBatchIngest, TelemetryBatchResponse,
    GatewayMessagePayload, GatewayReplayPayload, GatewayReplayResponse
)
from backend.app.ingestion.message_validation import validate_physical_measurements
from backend.app.ingestion.deduplication import DeduplicationChecker
from backend.app.analytics.rules import (
    compute_vector_tilt, compute_kinematics, evaluate_geotechnical_rules, haversine_distance_m
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
        skip_ws: bool = False,
        commit_transaction: bool = True
    ) -> Tuple[Optional[TelemetryRecord], Optional[str], bool]:
        """
        Process and persist a single telemetry frame.
        Handles physical validation, deduplication, kinematics derivation,
        out-of-order corrections, and geotechnical alerting.
        Returns: (record, error_message, was_duplicate)
        """
        # 1. Verify registered node exists
        node = db.query(SensorNode).filter(SensorNode.node_id == telemetry.node_id).first()
        if not node:
            return None, f"Node '{telemetry.node_id}' is not registered.", False

        if not node.is_enabled:
            return None, f"Node '{telemetry.node_id}' is disabled.", False

        # 2. Check for duplicate observation in DB
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

        now_utc = datetime.now(timezone.utc)
        elapsed_since_meas = (now_utc - ts_utc).total_seconds()
        is_delayed_replay = elapsed_since_meas > settings.STALE_DATA_TIMEOUT_SEC

        # 6. Fetch baseline for relative kinematic tracking
        baseline = node.baseline or db.query(NodeBaseline).filter(NodeBaseline.node_id == telemetry.node_id).first()
        baseline_rel_disp = None
        baseline_rel_tilt = None
        if baseline and baseline.is_valid:
            if telemetry.displacement_mm is not None and baseline.baseline_disp_mean is not None:
                baseline_rel_disp = round(telemetry.displacement_mm - baseline.baseline_disp_mean, 4)
            if vector_tilt is not None and baseline.baseline_tilt_vector_mean is not None:
                baseline_rel_tilt = round(vector_tilt - baseline.baseline_tilt_vector_mean, 4)

        # 7. Evaluate explicit sensor quality state: valid, stale, uncalibrated, out_of_range, suspect
        quality_state = "valid"
        if telemetry.sensor_quality_state:
            quality_state = telemetry.sensor_quality_state
        elif is_delayed_replay:
            quality_state = "stale"
        elif (telemetry.calibration_status in ["uncalibrated", "calibrating"] or
              (node.calibration_status and node.calibration_status in ["uncalibrated", "calibrating"])):
            quality_state = "uncalibrated"
        elif quality == "BAD":
            quality_state = "out_of_range"
        elif (quality in ["SUSPECT", "DEGRADED"] or
              telemetry.calibration_status == "suspect" or
              (node.calibration_status and node.calibration_status == "suspect")):
            quality_state = "suspect"

        # 8. Create TelemetryRecord
        assigned_event_id = telemetry.event_id or str(uuid.uuid4())
        record = TelemetryRecord(
            event_id=assigned_event_id,
            node_id=telemetry.node_id,
            test_run_id=telemetry.test_run_id,
            sequence_number=telemetry.sequence_number,
            timestamp=ts_utc,
            received_at=now_utc,
            displacement_mm=telemetry.displacement_mm,
            baseline_relative_displacement_mm=baseline_rel_disp,
            tilt_x_deg=telemetry.tilt_x_deg,
            tilt_y_deg=telemetry.tilt_y_deg,
            vector_tilt_deg=vector_tilt,
            baseline_relative_tilt_deg=baseline_rel_tilt,
            velocity_mm_hr=velocity_mm_hr,
            acceleration_mm_hr2=accel_mm_hr2,
            vibration_rms_ms2=telemetry.vibration_rms_ms2,
            peak_acceleration_ms2=telemetry.peak_acceleration_ms2,
            temperature_c=telemetry.temperature_c,
            crack_width_mm=telemetry.crack_width_mm,
            battery_voltage_v=telemetry.battery_voltage_v,
            battery_pct=telemetry.battery_pct,
            sensor_quality=quality,
            sensor_quality_state=quality_state,
            data_source=telemetry.data_source,
            calibration_status=telemetry.calibration_status,
            raw_metadata=telemetry.raw_metadata
        )
        db.add(record)

        # 7. Update node health (only if this measurement is newer than what node has seen)
        node_ls = node.last_seen.replace(tzinfo=timezone.utc) if node.last_seen and node.last_seen.tzinfo is None else node.last_seen
        if node_ls is None or ts_utc >= node_ls:
            node.last_seen = ts_utc
            if not is_delayed_replay:
                node.connectivity_status = "ONLINE"
            if telemetry.battery_pct is not None:
                node.battery_pct = telemetry.battery_pct
            if telemetry.firmware_version:
                node.firmware_version = telemetry.firmware_version

        # 8. Out-of-order kinematics correction for immediately following record
        next_record = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == telemetry.node_id,
                TelemetryRecord.timestamp > ts_utc
            )
            .order_by(asc(TelemetryRecord.timestamp))
            .first()
        )
        if next_record and next_record.displacement_mm is not None and telemetry.displacement_mm is not None:
            # Recalculate next record's velocity relative to this newly inserted record
            next_ts = next_record.timestamp.replace(tzinfo=timezone.utc) if next_record.timestamp.tzinfo is None else next_record.timestamp
            dt_hours = (next_ts - ts_utc).total_seconds() / 3600.0
            if dt_hours >= (0.5 / 3600.0):
                new_v = round((next_record.displacement_mm - telemetry.displacement_mm) / dt_hours, 4)
                next_record.velocity_mm_hr = new_v
                if velocity_mm_hr is not None:
                    next_record.acceleration_mm_hr2 = round((new_v - velocity_mm_hr) / dt_hours, 4)

        # 9. Baseline, recent history, and spatial neighbor context
        baseline = node.baseline or db.query(NodeBaseline).filter(NodeBaseline.node_id == telemetry.node_id).first()

        recent_records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == telemetry.node_id,
                TelemetryRecord.timestamp < ts_utc
            )
            .order_by(desc(TelemetryRecord.timestamp))
            .limit(10)
            .all()
        )
        recent_history = list(reversed(recent_records))

        spatial_neighbors = []
        if node.latitude is not None and node.longitude is not None:
            candidate_nodes = (
                db.query(SensorNode)
                .filter(
                    SensorNode.node_id != telemetry.node_id,
                    SensorNode.is_enabled.is_(True),
                    SensorNode.latitude.isnot(None),
                    SensorNode.longitude.isnot(None)
                )
                .all()
            )
            for c_node in candidate_nodes:
                dist_m = haversine_distance_m(node.latitude, node.longitude, c_node.latitude, c_node.longitude)
                if dist_m <= settings.SPATIAL_CORROBORATION_RADIUS_M:
                    n_rec = (
                        db.query(TelemetryRecord)
                        .filter(TelemetryRecord.node_id == c_node.node_id)
                        .order_by(desc(TelemetryRecord.timestamp))
                        .first()
                    )
                    if n_rec:
                        spatial_neighbors.append({
                            "node_id": c_node.node_id,
                            "distance_m": round(dist_m, 1),
                            "displacement_mm": n_rec.displacement_mm,
                            "velocity_mm_hr": n_rec.velocity_mm_hr,
                            "timestamp": n_rec.timestamp
                        })

        # Evaluate Geotechnical Rules
        findings = evaluate_geotechnical_rules(
            node_id=telemetry.node_id,
            timestamp=ts_utc,
            displacement_mm=telemetry.displacement_mm,
            vector_tilt_deg=vector_tilt,
            velocity_mm_hr=velocity_mm_hr,
            acceleration_mm_hr2=accel_mm_hr2,
            vibration_rms_ms2=telemetry.vibration_rms_ms2,
            battery_pct=telemetry.battery_pct,
            quality=quality,
            prev_record=prev_record,
            baseline=baseline,
            recent_history=recent_history,
            spatial_neighbors=spatial_neighbors,
            tilt_x_deg=telemetry.tilt_x_deg,
            tilt_y_deg=telemetry.tilt_y_deg
        )

        # 10. Optional ML multivariate anomaly check
        obs_dict = {
            "displacement_mm": telemetry.displacement_mm,
            "tilt_x_deg": telemetry.tilt_x_deg,
            "tilt_y_deg": telemetry.tilt_y_deg,
            "velocity_mm_hr": velocity_mm_hr,
            "vibration_rms_ms2": telemetry.vibration_rms_ms2,
            "temperature_c": telemetry.temperature_c
        }
        is_ml_anomaly, ml_score, ml_factor, ml_meta = ml_detector.predict(obs_dict, include_metadata=True)
        if is_ml_anomaly:
            from backend.app.analytics.rules import RuleFinding
            findings.append(RuleFinding(
                severity="WATCH",
                category="SENSOR_DRIFT",
                title=f"Multivariate Statistical Outlier Detected by Isolation Forest (Top Feature: {ml_factor})",
                description=(
                    f"Isolation forest flagged multi-sensor pattern divergence from baseline manifold. "
                    f"Decision outlier score: {ml_score:.4f}. Primary contributing channel: {ml_factor}. "
                    "Note: Decision scores indicate statistical novelty, not empirical collapse probability."
                ),
                triggering_rule="ML_ISOLATION_FOREST_OUTLIER",
                evidence={
                    "score": ml_score,
                    "primary_factor": ml_factor,
                    "model_metadata": ml_meta,
                    "measurements": obs_dict,
                    "uncertainty": "UNSUPERVISED_STATISTICAL_NOVELTY"
                },
                uncertainty="UNSUPERVISED_STATISTICAL_NOVELTY"
            ))

        # 11. Persist alerts
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
                evidence=finding.evidence,
                test_run_id=telemetry.test_run_id
            )
            if alert:
                new_alerts.append(alert)

        if commit_transaction:
            db.commit()
            db.refresh(record)

        # 12. Broadcast to WebSocket clients (suppress emergency broadcast for delayed replay)
        if not skip_ws and not is_delayed_replay:
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

            await ws_manager.broadcast("node_status", {
                "node_id": node.node_id,
                "connectivity_status": node.connectivity_status,
                "last_seen": node.last_seen.isoformat() if node.last_seen else None,
                "battery_pct": node.battery_pct,
                "firmware_version": node.firmware_version,
                "is_enabled": node.is_enabled
            })

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
        Process array of telemetry frames.
        If batch.atomic is True: any validation failure or unknown node causes complete rollback.
        Guarantees that a malformed batch never partially corrupts the database.
        """
        ingested_count = 0
        duplicates_skipped = 0
        errors: List[str] = []

        # Sort batch chronologically
        sorted_records = sorted(batch.records, key=lambda r: r.timestamp)

        # In-batch duplicate tracking
        seen_events: Set[str] = set()
        seen_seqs: Set[Tuple[str, int]] = set()

        # Step 1: Pre-validation when atomic=True
        if batch.atomic:
            for idx, item in enumerate(sorted_records):
                # Verify node exists
                node = db.query(SensorNode.node_id, SensorNode.is_enabled).filter(SensorNode.node_id == item.node_id).first()
                if not node:
                    errors.append(f"Item #{idx}: Unknown node '{item.node_id}'")
                elif not node[1]:
                    errors.append(f"Item #{idx}: Node '{item.node_id}' is disabled")

                # Validate bounds
                is_valid, err_msg, _ = validate_physical_measurements(item)
                if not is_valid:
                    errors.append(f"Item #{idx} ({item.node_id}): {err_msg}")

                # Check in-batch duplicates
                if item.event_id in seen_events:
                    # duplicate within batch
                    pass
                else:
                    seen_events.add(item.event_id)

                if item.sequence_number is not None:
                    key = (item.node_id, item.sequence_number)
                    if key in seen_seqs:
                        pass
                    else:
                        seen_seqs.add(key)

            if errors:
                # Malformed batch in atomic mode: abort without persisting anything
                return TelemetryBatchResponse(
                    ingested_count=0,
                    duplicates_skipped=0,
                    errors=errors
                )

        # Step 2: Ingest records in a unified transaction
        seen_events.clear()
        seen_seqs.clear()

        try:
            for item in sorted_records:
                # Check in-batch duplicate
                is_in_batch_dup = False
                if item.event_id in seen_events:
                    is_in_batch_dup = True
                else:
                    seen_events.add(item.event_id)

                if item.sequence_number is not None:
                    key = (item.node_id, item.sequence_number)
                    if key in seen_seqs:
                        is_in_batch_dup = True
                    else:
                        seen_seqs.add(key)

                if is_in_batch_dup:
                    duplicates_skipped += 1
                    continue

                record, err, was_dup = await TelemetryService.process_single_telemetry(
                    db=db,
                    telemetry=item,
                    skip_ws=True,  # Avoid spamming websocket in large batch
                    commit_transaction=False
                )
                if was_dup:
                    duplicates_skipped += 1
                elif err:
                    errors.append(f"Node {item.node_id} seq {item.sequence_number}: {err}")
                    if batch.atomic:
                        db.rollback()
                        return TelemetryBatchResponse(ingested_count=0, duplicates_skipped=0, errors=errors)
                elif record:
                    ingested_count += 1

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error during batch commit: {e}", exc_info=True)
            return TelemetryBatchResponse(
                ingested_count=0,
                duplicates_skipped=0,
                errors=[f"Database transaction failure: {str(e)}"]
            )

        return TelemetryBatchResponse(
            ingested_count=ingested_count,
            duplicates_skipped=duplicates_skipped,
            errors=errors
        )

    @staticmethod
    async def process_gateway_replay(
        db: Session,
        replay: GatewayReplayPayload
    ) -> GatewayReplayResponse:
        """
        Process store-and-forward batch telemetry replayed from an edge gateway after connectivity recovery.
        Guarantees:
        1. Safe against duplicate batch delivery (idempotent deduplication by event_id and node_id+sequence).
        2. Correct chronological sorting and out-of-order kinematics correction.
        3. Suppresses live emergency alarms for historical buffered records while persisting alerts.
        4. Updates node status and creates an AuditEvent.
        """
        accepted_count = 0
        duplicates_skipped = 0
        rejected_count = 0
        errors: List[str] = []

        # Convert records to TelemetryIngest objects
        telemetry_items: List[TelemetryIngest] = []
        for raw_item in replay.records:
            if isinstance(raw_item, GatewayMessagePayload):
                item = raw_item.to_telemetry_ingest(data_source="gateway_replay")
            elif isinstance(raw_item, TelemetryIngest):
                item = raw_item
                item.data_source = "gateway_replay"
            elif isinstance(raw_item, dict):
                if "readings" in raw_item:
                    gw_msg = GatewayMessagePayload(**raw_item)
                    item = gw_msg.to_telemetry_ingest(data_source="gateway_replay")
                else:
                    item = TelemetryIngest(**raw_item)
                    item.data_source = "gateway_replay"
            else:
                rejected_count += 1
                errors.append(f"Unrecognized record format: {type(raw_item)}")
                continue

            if not item.gateway_id:
                item.gateway_id = replay.gateway_id
            telemetry_items.append(item)

        # Sort chronologically by measurement timestamp
        sorted_records = sorted(telemetry_items, key=lambda r: r.timestamp)

        # Track in-batch duplicates
        seen_events: Set[str] = set()
        seen_seqs: Set[Tuple[str, int]] = set()

        try:
            for item in sorted_records:
                # Check in-batch duplicate
                if item.event_id in seen_events:
                    duplicates_skipped += 1
                    continue
                seen_events.add(item.event_id)

                if item.sequence_number is not None:
                    seq_key = (item.node_id, item.sequence_number)
                    if seq_key in seen_seqs:
                        duplicates_skipped += 1
                        continue
                    seen_seqs.add(seq_key)

                record, err, was_dup = await TelemetryService.process_single_telemetry(
                    db=db,
                    telemetry=item,
                    skip_ws=True,  # Suppress live alarm flood during historical replay
                    commit_transaction=False
                )

                if was_dup:
                    duplicates_skipped += 1
                elif err:
                    rejected_count += 1
                    errors.append(f"Node {item.node_id}: {err}")
                elif record:
                    accepted_count += 1

            # Log audit event for replay
            audit = AuditEvent(
                category="INGESTION",
                node_id=None,
                actor=f"gateway:{replay.gateway_id}",
                action="GATEWAY_REPLAY_INGEST",
                outcome="SUCCESS" if rejected_count == 0 else ("PARTIAL" if accepted_count > 0 else "FAILED"),
                details={
                    "gateway_id": replay.gateway_id,
                    "batch_id": replay.batch_id,
                    "buffered_count": replay.buffered_count,
                    "accepted_count": accepted_count,
                    "duplicates_skipped": duplicates_skipped,
                    "rejected_count": rejected_count
                }
            )
            db.add(audit)
            db.commit()

            # Broadcast summary replay event over WebSocket
            await ws_manager.broadcast("gateway_replay_completed", {
                "gateway_id": replay.gateway_id,
                "batch_id": replay.batch_id,
                "accepted_count": accepted_count,
                "duplicates_skipped": duplicates_skipped,
                "rejected_count": rejected_count
            })

        except Exception as e:
            db.rollback()
            logger.error(f"Error during gateway replay batch commit: {e}", exc_info=True)
            return GatewayReplayResponse(
                gateway_id=replay.gateway_id,
                batch_id=replay.batch_id,
                received_count=len(replay.records),
                accepted_count=0,
                duplicates_skipped=0,
                rejected_count=len(replay.records),
                status="REJECTED",
                errors=[f"Database transaction failure: {str(e)}"]
            )

        status_str = "COMPLETED"
        if rejected_count > 0:
            status_str = "PARTIAL" if accepted_count > 0 else "REJECTED"

        return GatewayReplayResponse(
            gateway_id=replay.gateway_id,
            batch_id=replay.batch_id,
            received_count=len(replay.records),
            accepted_count=accepted_count,
            duplicates_skipped=duplicates_skipped,
            rejected_count=rejected_count,
            status=status_str,
            errors=errors
        )
