import csv
import io
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.app.db.models import TestRun, TelemetryRecord, Alert, AuditEvent, SensorNode
from backend.app.schemas.experiment import (
    TestRunStartRequest, TestRunReferenceUpdateRequest, TestRunCompleteRequest
)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

logger = logging.getLogger("mineguard.experiments")


class ExperimentService:
    @staticmethod
    def start_test_run(db: Session, request: TestRunStartRequest) -> TestRun:
        now_utc = datetime.now(timezone.utc)
        # Abort any currently running test runs
        active_runs = db.query(TestRun).filter(TestRun.status == "RUNNING").all()
        for run in active_runs:
            run.status = "ABORTED"
            run.end_time = now_utc
            run.notes = (run.notes or "") + " [Auto-aborted upon starting new test run]"

        test_run_id = f"TR-{now_utc.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

        test_run = TestRun(
            test_run_id=test_run_id,
            name=request.name,
            scenario=request.scenario,
            test_conditions=request.test_conditions,
            target_node_id=request.target_node_id,
            status="RUNNING",
            start_time=now_utc,
            intended_movement_mm=request.intended_movement_mm,
            notes=request.notes,
            created_at=now_utc
        )
        db.add(test_run)

        audit = AuditEvent(
            category="EXPERIMENT",
            node_id=request.target_node_id,
            actor="test_rig_operator",
            action="START_TEST_RUN",
            outcome="SUCCESS",
            details={
                "test_run_id": test_run_id,
                "scenario": request.scenario,
                "conditions": request.test_conditions,
                "intended_movement_mm": request.intended_movement_mm
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(test_run)
        return test_run

    @staticmethod
    def record_reference_movement(
        db: Session,
        test_run_id: str,
        request: TestRunReferenceUpdateRequest
    ) -> Optional[TestRun]:
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()
        if not test_run:
            return None

        test_run.reference_movement_mm = request.reference_movement_mm
        if request.notes:
            test_run.notes = f"{test_run.notes or ''}\nRef Movement Note: {request.notes}".strip()

        audit = AuditEvent(
            category="EXPERIMENT",
            node_id=test_run.target_node_id,
            actor="test_rig_operator",
            action="RECORD_REFERENCE_MOVEMENT",
            outcome="SUCCESS",
            details={
                "test_run_id": test_run_id,
                "reference_movement_mm": request.reference_movement_mm
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(test_run)
        return test_run

    @staticmethod
    def complete_test_run(
        db: Session,
        test_run_id: str,
        request: Optional[TestRunCompleteRequest] = None
    ) -> Optional[TestRun]:
        test_run = db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()
        if not test_run:
            return None

        now_utc = datetime.now(timezone.utc)
        test_run.end_time = now_utc
        test_run.status = "COMPLETED"
        if request and request.notes:
            test_run.notes = f"{test_run.notes or ''}\nCompletion Note: {request.notes}".strip()

        # Query all TelemetryRecords for this test run or target node in the time interval
        t_query = db.query(TelemetryRecord).filter(
            TelemetryRecord.timestamp >= test_run.start_time,
            TelemetryRecord.timestamp <= test_run.end_time
        )
        if test_run.target_node_id:
            t_query = t_query.filter(TelemetryRecord.node_id == test_run.target_node_id)

        records = t_query.order_by(TelemetryRecord.timestamp.asc()).all()

        total_samples = len(records)
        valid_samples = [r for r in records if r.displacement_mm is not None]
        stale_samples = [r for r in records if r.sensor_quality_state == "stale"]

        reported_movement = None
        if len(valid_samples) >= 2:
            initial_disp = valid_samples[0].displacement_mm
            final_disp = valid_samples[-1].displacement_mm
            reported_movement = round(final_disp - initial_disp, 4)
        elif len(valid_samples) == 1:
            reported_movement = valid_samples[0].displacement_mm

        test_run.sensor_reported_movement_mm = reported_movement

        # Compute measurement error against ground-truth reference
        ref_mv = test_run.reference_movement_mm if test_run.reference_movement_mm is not None else test_run.intended_movement_mm
        measurement_error_mm = None
        relative_error_pct = None
        if reported_movement is not None and ref_mv is not None:
            measurement_error_mm = round(abs(reported_movement - ref_mv), 4)
            if abs(ref_mv) > 0.0001:
                relative_error_pct = round((measurement_error_mm / abs(ref_mv)) * 100.0, 2)
            else:
                relative_error_pct = 0.0

        test_run.measurement_error_mm = measurement_error_mm

        # Query alerts created during test run
        a_query = db.query(Alert).filter(
            Alert.created_at >= test_run.start_time,
            Alert.created_at <= test_run.end_time
        )
        if test_run.target_node_id:
            a_query = a_query.filter(Alert.node_id == test_run.target_node_id)

        alerts = a_query.order_by(Alert.created_at.asc()).all()
        alerts_count = len(alerts)

        # Detection latency
        detection_latency_sec = None
        if alerts:
            earliest_alert = alerts[0]
            lat = (earliest_alert.created_at.replace(tzinfo=timezone.utc) - test_run.start_time.replace(tzinfo=timezone.utc)).total_seconds()
            detection_latency_sec = max(0.0, round(lat, 2))

        test_run.detection_latency_sec = detection_latency_sec

        # Compute expected packets for PDR calculation
        duration_sec = max(1.0, (test_run.end_time.replace(tzinfo=timezone.utc) - test_run.start_time.replace(tzinfo=timezone.utc)).total_seconds())
        # Target node sampling rate
        sampling_interval = 5.0
        if test_run.target_node_id:
            tn = db.query(SensorNode).filter(SensorNode.node_id == test_run.target_node_id).first()
            if tn and tn.sampling_interval_sec:
                sampling_interval = tn.sampling_interval_sec

        expected_packets = max(1, int(duration_sec / sampling_interval))
        pdr_pct = min(100.0, round((total_samples / expected_packets) * 100.0, 1))

        # Precision / recall / false alerts
        # In baseline / zero movement scenarios (or stable test rig), alerts are classified as false alerts
        is_zero_movement = (ref_mv is None or abs(ref_mv) < 0.05) and test_run.scenario in ["testrig_baseline", "testrig_return_stable", "testrig_vibration_only"]
        false_alerts_count = alerts_count if is_zero_movement else 0
        true_positives = 0 if is_zero_movement else (1 if alerts_count > 0 else 0)
        false_negatives = 1 if (not is_zero_movement and alerts_count == 0 and (ref_mv and abs(ref_mv) >= 5.0)) else 0

        precision = 1.0 if (true_positives + false_alerts_count == 0) else round(true_positives / (true_positives + false_alerts_count), 2)
        recall = 1.0 if (true_positives + false_negatives == 0) else round(true_positives / (true_positives + false_negatives), 2)
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0

        false_alerts_denominator = f"{false_alerts_count} false alerts / {total_samples} samples ({round(duration_sec, 0)}s duration)"

        metrics = {
            "test_run_id": test_run.test_run_id,
            "scenario": test_run.scenario,
            "test_conditions": test_run.test_conditions,
            "duration_sec": round(duration_sec, 2),
            "total_packets_received": total_samples,
            "expected_packets": expected_packets,
            "packet_delivery_ratio_pct": pdr_pct,
            "stale_samples_flagged": len(stale_samples),
            "ground_truth_movement_mm": ref_mv,
            "sensor_reported_movement_mm": reported_movement,
            "absolute_error_mm": measurement_error_mm,
            "relative_error_pct": relative_error_pct,
            "detection_latency_sec": detection_latency_sec,
            "alerts_generated_count": alerts_count,
            "false_alerts_count": false_alerts_count,
            "false_alerts_denominator": false_alerts_denominator,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "offline_recovery_verified": any(r.data_source == "gateway_replay" for r in records),
            "rig_reference_tracking": "Dial Indicator / Micrometer Plate Benchmark"
        }
        test_run.metrics = metrics

        audit = AuditEvent(
            category="EXPERIMENT",
            node_id=test_run.target_node_id,
            actor="test_rig_operator",
            action="COMPLETE_TEST_RUN",
            outcome="SUCCESS",
            details={
                "test_run_id": test_run_id,
                "error_mm": measurement_error_mm,
                "latency_sec": detection_latency_sec,
                "pdr_pct": pdr_pct,
                "false_alerts": false_alerts_denominator
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(test_run)
        return test_run

    @staticmethod
    def get_test_run(db: Session, test_run_id: str) -> Optional[TestRun]:
        return db.query(TestRun).filter(TestRun.test_run_id == test_run_id).first()

    @staticmethod
    def list_test_runs(
        db: Session,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[TestRun], int]:
        query = db.query(TestRun)
        if status:
            query = query.filter(TestRun.status == status.upper())
        total = query.count()
        items = query.order_by(TestRun.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def export_test_run_csv(db: Session, test_run_id: str) -> str:
        test_run = ExperimentService.get_test_run(db, test_run_id)
        if not test_run:
            raise ValueError(f"Test run '{test_run_id}' not found.")

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["MineGuard-AI Test-Rig Experiment Evaluation (Table 12 Format)"])
        writer.writerow(["Test Run ID", test_run.test_run_id])
        writer.writerow(["Scenario", test_run.scenario])
        writer.writerow(["Test Conditions", test_run.test_conditions])
        writer.writerow(["Target Node", test_run.target_node_id or "All"])
        writer.writerow(["Status", test_run.status])
        writer.writerow(["Start Time UTC", test_run.start_time.isoformat() if test_run.start_time else ""])
        writer.writerow(["End Time UTC", test_run.end_time.isoformat() if test_run.end_time else ""])
        writer.writerow(["Ground Truth Movement (mm)", test_run.reference_movement_mm if test_run.reference_movement_mm is not None else test_run.intended_movement_mm])
        writer.writerow(["Sensor Reported Movement (mm)", test_run.sensor_reported_movement_mm])
        writer.writerow(["Absolute Measurement Error (mm)", test_run.measurement_error_mm])
        writer.writerow(["Detection Latency (s)", test_run.detection_latency_sec])
        
        metrics = test_run.metrics or {}
        writer.writerow(["Packet Delivery Ratio (%)", metrics.get("packet_delivery_ratio_pct", "")])
        writer.writerow(["False Alerts", metrics.get("false_alerts_denominator", "")])
        writer.writerow(["Precision", metrics.get("precision", "")])
        writer.writerow(["Recall", metrics.get("recall", "")])
        writer.writerow(["F1 Score", metrics.get("f1_score", "")])
        writer.writerow([])

        # Telemetry Section
        writer.writerow(["Telemetry Series During Test Run"])
        writer.writerow([
            "Timestamp UTC", "Node ID", "Displacement (mm)", "Baseline Relative Disp (mm)",
            "Tilt Vector (deg)", "Velocity (mm/hr)", "Acceleration (mm/hr2)",
            "Vibration RMS (m/s2)", "Quality State", "Data Source"
        ])

        records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.timestamp >= test_run.start_time,
                TelemetryRecord.timestamp <= (test_run.end_time or datetime.now(timezone.utc))
            )
            .order_by(TelemetryRecord.timestamp.asc())
            .limit(2000)
            .all()
        )
        for r in records:
            writer.writerow([
                r.timestamp.isoformat(),
                r.node_id,
                r.displacement_mm if r.displacement_mm is not None else "",
                r.baseline_relative_displacement_mm if r.baseline_relative_displacement_mm is not None else "",
                r.vector_tilt_deg if r.vector_tilt_deg is not None else "",
                r.velocity_mm_hr if r.velocity_mm_hr is not None else "",
                r.acceleration_mm_hr2 if r.acceleration_mm_hr2 is not None else "",
                r.vibration_rms_ms2 if r.vibration_rms_ms2 is not None else "",
                r.sensor_quality_state or "",
                r.data_source or ""
            ])

        return output.getvalue()

    @staticmethod
    def export_test_run_pdf(db: Session, test_run_id: str) -> bytes:
        test_run = ExperimentService.get_test_run(db, test_run_id)
        if not test_run:
            raise ValueError(f"Test run '{test_run_id}' not found.")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TestRunTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        sub_style = ParagraphStyle(
            'TestRunSub',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=14
        )
        section_style = ParagraphStyle(
            'TestRunSection',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=10,
            spaceAfter=6
        )
        cell_style = ParagraphStyle(
            'TestRunCell',
            parent=styles['Normal'],
            fontSize=8,
            leading=10
        )
        cell_bold = ParagraphStyle(
            'TestRunCellBold',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            leading=10
        )

        elements = []

        elements.append(Paragraph(f"MineGuard-AI Test-Rig Evaluation Report: {test_run.test_run_id}", title_style))
        elements.append(Paragraph(
            f"Scenario: {test_run.scenario} | Rig: {test_run.test_conditions} | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            sub_style
        ))

        # Scientific Disclaimer Box
        disc_text = (
            "<b>LABORATORY BENCHMARK DISCLOSURE:</b> This evaluation report measures mechanical displacement response on a "
            "controlled testbed with independent micrometer reference plate tracking. Sensor decision scores indicate statistical "
            "or geotechnical rule thresholds, not verified commercial mine-collapse probability or certified life-safety compliance."
        )
        elements.append(Paragraph(disc_text, cell_style))
        elements.append(Spacer(1, 10))

        # Table 12 Performance Summary
        elements.append(Paragraph("Table 12: Laboratory Test-Rig Benchmark Metrics", section_style))
        metrics = test_run.metrics or {}
        ref_mv = test_run.reference_movement_mm if test_run.reference_movement_mm is not None else test_run.intended_movement_mm

        table_data = [
            [Paragraph("Evaluation Metric", cell_bold), Paragraph("Observed Value", cell_bold), Paragraph("Reference / Target", cell_bold)],
            [Paragraph("Ground Truth Reference Movement", cell_style), Paragraph(f"{ref_mv} mm" if ref_mv is not None else "N/A", cell_style), Paragraph("Micrometer Gauge", cell_style)],
            [Paragraph("Sensor Reported Movement", cell_style), Paragraph(f"{test_run.sensor_reported_movement_mm} mm" if test_run.sensor_reported_movement_mm is not None else "N/A", cell_style), Paragraph("Telemetry Delta", cell_style)],
            [Paragraph("Absolute Measurement Error", cell_style), Paragraph(f"{test_run.measurement_error_mm} mm" if test_run.measurement_error_mm is not None else "N/A", cell_style), Paragraph("&lt; 1.5 mm SIH Spec", cell_style)],
            [Paragraph("Detection Latency", cell_style), Paragraph(f"{test_run.detection_latency_sec} s" if test_run.detection_latency_sec is not None else "N/A", cell_style), Paragraph("&lt; 10 s SIH Spec", cell_style)],
            [Paragraph("Packet Delivery Ratio (PDR)", cell_style), Paragraph(f"{metrics.get('packet_delivery_ratio_pct', 'N/A')}%", cell_style), Paragraph("&gt; 95% Target", cell_style)],
            [Paragraph("False Alerts Denominator", cell_style), Paragraph(str(metrics.get("false_alerts_denominator", "0")), cell_style), Paragraph("0 during stable period", cell_style)],
            [Paragraph("Precision / Recall / F1", cell_style), Paragraph(f"P: {metrics.get('precision', 'N/A')} | R: {metrics.get('recall', 'N/A')} | F1: {metrics.get('f1_score', 'N/A')}", cell_style), Paragraph("Balanced Geotechnical Rule Base", cell_style)]
        ]

        t = Table(table_data, colWidths=[180, 200, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 14))

        # Recent Telemetry Log Summary
        elements.append(Paragraph("Sample Telemetry Chronology", section_style))
        records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.timestamp >= test_run.start_time,
                TelemetryRecord.timestamp <= (test_run.end_time or datetime.now(timezone.utc))
            )
            .order_by(TelemetryRecord.timestamp.asc())
            .limit(10)
            .all()
        )
        t_rows = [
            [Paragraph("Time (UTC)", cell_bold), Paragraph("Node", cell_bold), Paragraph("Disp (mm)", cell_bold), Paragraph("Tilt (°)", cell_bold), Paragraph("Velocity (mm/h)", cell_bold), Paragraph("Quality", cell_bold)]
        ]
        for r in records:
            t_rows.append([
                Paragraph(r.timestamp.strftime("%H:%M:%S"), cell_style),
                Paragraph(r.node_id, cell_style),
                Paragraph(f"{r.displacement_mm:.2f}" if r.displacement_mm is not None else "-", cell_style),
                Paragraph(f"{r.vector_tilt_deg:.2f}" if r.vector_tilt_deg is not None else "-", cell_style),
                Paragraph(f"{r.velocity_mm_hr:.2f}" if r.velocity_mm_hr is not None else "-", cell_style),
                Paragraph(r.sensor_quality_state or "valid", cell_style)
            ])
        t_table = Table(t_rows, colWidths=[90, 100, 80, 70, 100, 100])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_table)

        doc.build(elements)
        return buffer.getvalue()

