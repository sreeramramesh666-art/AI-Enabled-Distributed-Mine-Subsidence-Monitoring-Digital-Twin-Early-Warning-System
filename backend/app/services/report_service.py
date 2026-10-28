import csv
import io
import re
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.models import TelemetryRecord, Alert, SensorNode
from backend.app.services.analytics_service import AnalyticsService

# ReportLab imports for generating real PDF reports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def sanitize_csv_cell(value: Any) -> str:
    """Protect against CSV formula injection (CVE-2014-3524 / CWE-1236)."""
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


class ReportService:
    @staticmethod
    def export_csv(
        db: Session,
        node_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """Export telemetry data as RFC 4180 compliant CSV string."""
        if start_time and end_time and start_time > end_time:
            raise ValueError("start_time must be earlier than or equal to end_time")

        if node_id:
            node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
            if not node:
                raise ValueError(f"Sensor node '{node_id}' not found.")

        query = db.query(TelemetryRecord)
        if node_id:
            query = query.filter(TelemetryRecord.node_id == node_id)
        if start_time:
            query = query.filter(TelemetryRecord.timestamp >= start_time)
        if end_time:
            query = query.filter(TelemetryRecord.timestamp <= end_time)

        records = query.order_by(TelemetryRecord.timestamp.asc()).limit(5000).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "event_id", "node_id", "sequence_number", "timestamp_utc", "received_at_utc",
            "displacement_mm", "tilt_x_deg", "tilt_y_deg", "vector_tilt_deg",
            "velocity_mm_hr", "acceleration_mm_hr2", "vibration_rms_ms2", "peak_acceleration_ms2",
            "temperature_c", "crack_width_mm", "battery_pct", "data_source", "calibration_status"
        ])

        for r in records:
            writer.writerow([
                r.id,
                sanitize_csv_cell(r.event_id),
                sanitize_csv_cell(r.node_id),
                r.sequence_number or "",
                r.timestamp.isoformat() if r.timestamp else "",
                r.received_at.isoformat() if r.received_at else "",
                f"{r.displacement_mm:.3f}" if r.displacement_mm is not None else "",
                f"{r.tilt_x_deg:.2f}" if r.tilt_x_deg is not None else "",
                f"{r.tilt_y_deg:.2f}" if r.tilt_y_deg is not None else "",
                f"{r.vector_tilt_deg:.2f}" if r.vector_tilt_deg is not None else "",
                f"{r.velocity_mm_hr:.3f}" if r.velocity_mm_hr is not None else "",
                f"{r.acceleration_mm_hr2:.3f}" if r.acceleration_mm_hr2 is not None else "",
                f"{r.vibration_rms_ms2:.2f}" if r.vibration_rms_ms2 is not None else "",
                f"{r.peak_acceleration_ms2:.2f}" if r.peak_acceleration_ms2 is not None else "",
                f"{r.temperature_c:.1f}" if r.temperature_c is not None else "",
                f"{r.crack_width_mm:.2f}" if r.crack_width_mm is not None else "",
                f"{r.battery_pct:.1f}" if r.battery_pct is not None else "",
                sanitize_csv_cell(r.data_source),
                sanitize_csv_cell(r.calibration_status)
            ])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(
        db: Session,
        node_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> bytes:
        """
        Generate a comprehensive geotechnical monitoring PDF summary.
        Includes SI units, alerts breakdown, simulation notice, and limitations.
        """
        if start_time and end_time and start_time > end_time:
            raise ValueError("start_time must be earlier than or equal to end_time")

        if node_id:
            node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
            if not node:
                raise ValueError(f"Sensor node '{node_id}' not found.")

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
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a")
        )
        subtitle_style = ParagraphStyle(
            "SubTitleStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569")
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=8,
            spaceAfter=4
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#334155")
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#b91c1c")
        )

        elements = []

        # Title & Metadata
        elements.append(Paragraph("MineGuard-AI Geotechnical Monitoring Report", title_style))
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        filter_note = f" (Filtered: Node {node_id})" if node_id else " (Entire Mine Concession)"
        elements.append(Paragraph(f"SIH26025 Automated Geohazard & Subsidence Telemetry Audit | Generated: {gen_time}{filter_note}", subtitle_style))
        elements.append(Spacer(1, 8))

        # Check for simulated records in dataset
        sim_query = db.query(TelemetryRecord).filter(TelemetryRecord.data_source == "simulator")
        if node_id:
            sim_query = sim_query.filter(TelemetryRecord.node_id == node_id)
        sim_count = sim_query.count()

        tot_query = db.query(TelemetryRecord)
        if node_id:
            tot_query = tot_query.filter(TelemetryRecord.node_id == node_id)
        total_records = tot_query.count()

        if sim_count > 0:
            notice = f"[SIMULATION NOTICE]: This dataset contains {sim_count} of {total_records} synthetic observations generated by the MineGuard-AI simulator for algorithmic validation and testing."
            elements.append(Paragraph(notice, disclaimer_style))
            elements.append(Spacer(1, 8))

        # 1. Executive Summary Table
        summary = AnalyticsService.get_summary(db=db)
        summary_data = [
            ["Metric", "Value", "Metric", "Value"],
            ["Total Monitored Nodes", str(summary.total_nodes), "Active Critical Alerts", str(summary.active_critical_alerts)],
            ["Online Nodes", str(summary.online_nodes), "Active Warning Alerts", str(summary.active_warning_alerts)],
            ["Stale / Offline Nodes", f"{summary.stale_nodes} / {summary.offline_nodes}", "Active Watch Alerts", str(summary.active_watch_alerts)],
            ["Data Completeness", f"{summary.data_completeness_pct}%", "Overall Risk Level", summary.overall_risk_category],
        ]
        t = Table(summary_data, colWidths=[130, 130, 130, 130])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(Paragraph("1. Executive Monitoring Summary", h2_style))
        elements.append(t)
        elements.append(Spacer(1, 10))

        # 2. Registered Monitoring Nodes
        nodes_q = db.query(SensorNode)
        if node_id:
            nodes_q = nodes_q.filter(SensorNode.node_id == node_id)
        nodes = nodes_q.limit(15).all()

        node_rows = [["Node ID", "Name", "Coordinates", "Type", "Status", "Battery"]]
        for n in nodes:
            coords = f"{n.latitude:.4f}, {n.longitude:.4f}"
            bat = f"{n.battery_pct:.0f}%" if n.battery_pct is not None else "N/A"
            node_rows.append([n.node_id, n.name[:20], coords, n.node_type[:15], n.connectivity_status, bat])

        if len(node_rows) > 1:
            t_nodes = Table(node_rows, colWidths=[90, 130, 120, 90, 50, 40])
            t_nodes.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(Paragraph("2. Monitored Sensor Nodes", h2_style))
            elements.append(t_nodes)
            elements.append(Spacer(1, 10))

        # 3. Recent Alerts
        alerts_q = db.query(Alert)
        if node_id:
            alerts_q = alerts_q.filter(Alert.node_id == node_id)
        alerts = alerts_q.order_by(desc(Alert.created_at)).limit(10).all()

        if alerts:
            alert_rows = [["Alert ID", "Severity", "Node", "Category", "Status", "Triggering Rule"]]
            for a in alerts:
                alert_rows.append([
                    a.alert_id[:8] + "...",
                    a.severity,
                    a.node_id,
                    a.category,
                    a.status,
                    a.triggering_rule
                ])
            t_alerts = Table(alert_rows, colWidths=[70, 70, 90, 90, 70, 130])
            t_alerts.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(Paragraph("3. Recent Geohazard Alerts", h2_style))
            elements.append(t_alerts)
            elements.append(Spacer(1, 10))

        # 4. Geotechnical & Regulatory Limitations
        elements.append(Paragraph("4. Technical Limitations & Engineering Disclaimer", h2_style))
        disc_text = (
            "MineGuard-AI is an edge-first engineering software platform designed for early geohazard awareness. "
            "Alert indicators and simulated scenarios represent demonstration thresholds. "
            "Real-world operational safety determinations in active mining concessions require multi-source "
            "corroboration, statutory geotechnical review, manual extensometer verification, and regulatory "
            "compliance with Directorate General of Mines Safety (DGMS) norms."
        )
        elements.append(Paragraph(disc_text, body_style))

        doc.build(elements)
        return buffer.getvalue()
