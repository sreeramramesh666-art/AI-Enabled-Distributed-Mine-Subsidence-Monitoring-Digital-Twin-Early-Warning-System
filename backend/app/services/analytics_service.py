from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.db.models import SensorNode, TelemetryRecord, Alert
from backend.app.services.node_service import NodeService
from backend.app.schemas.analytics import (
    AnalyticsSummaryResponse, NodeHealthItem, TrendResponse, TrendSeriesPoint
)


class AnalyticsService:
    @staticmethod
    def get_summary(db: Session, simulator_running: bool = False) -> AnalyticsSummaryResponse:
        nodes = NodeService.list_nodes(db=db)
        total_nodes = len(nodes)
        online_nodes = sum(1 for n in nodes if n.connectivity_status == "ONLINE")
        stale_nodes = sum(1 for n in nodes if n.connectivity_status == "STALE")
        offline_nodes = sum(1 for n in nodes if n.connectivity_status == "OFFLINE")

        active_crit = db.query(func.count(Alert.id)).filter(
            Alert.status == "ACTIVE", Alert.severity == "CRITICAL"
        ).scalar() or 0

        active_warn = db.query(func.count(Alert.id)).filter(
            Alert.status == "ACTIVE", Alert.severity == "WARNING"
        ).scalar() or 0

        active_watch = db.query(func.count(Alert.id)).filter(
            Alert.status == "ACTIVE", Alert.severity == "WATCH"
        ).scalar() or 0

        # Latest telemetry record
        latest = db.query(TelemetryRecord).order_by(desc(TelemetryRecord.timestamp)).first()
        last_telemetry_at = latest.timestamp if latest else None

        # Data completeness estimate (reporting nodes vs total)
        completeness = round((online_nodes / total_nodes * 100.0), 1) if total_nodes > 0 else 0.0

        # Overall mine risk status
        if active_crit > 0:
            overall_risk = "CRITICAL"
        elif active_warn > 0:
            overall_risk = "WARNING"
        elif active_watch > 0:
            overall_risk = "WATCH"
        elif total_nodes > 0 and online_nodes == 0:
            overall_risk = "DATA_UNRELIABLE"
        else:
            overall_risk = "NORMAL"

        return AnalyticsSummaryResponse(
            total_nodes=total_nodes,
            online_nodes=online_nodes,
            stale_nodes=stale_nodes,
            offline_nodes=offline_nodes,
            active_critical_alerts=active_crit,
            active_warning_alerts=active_warn,
            active_watch_alerts=active_watch,
            overall_risk_category=overall_risk,
            last_telemetry_at=last_telemetry_at,
            data_completeness_pct=completeness,
            simulator_active=simulator_running
        )

    @staticmethod
    def get_trends(
        db: Session,
        node_id: str,
        hours: float = 24.0
    ) -> TrendResponse:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == node_id,
                TelemetryRecord.timestamp >= cutoff
            )
            .order_by(TelemetryRecord.timestamp.asc())
            .limit(1000)
            .all()
        )

        series = [
            TrendSeriesPoint(
                timestamp=r.timestamp,
                displacement_mm=r.displacement_mm,
                velocity_mm_hr=r.velocity_mm_hr,
                vector_tilt_deg=r.vector_tilt_deg,
                vibration_rms_ms2=r.vibration_rms_ms2
            )
            for r in records
        ]

        velocities = [abs(r.velocity_mm_hr) for r in records if r.velocity_mm_hr is not None]
        max_rate = max(velocities) if velocities else None

        net_disp = None
        if len(records) >= 2 and records[0].displacement_mm is not None and records[-1].displacement_mm is not None:
            net_disp = round(records[-1].displacement_mm - records[0].displacement_mm, 3)

        return TrendResponse(
            node_id=node_id,
            time_window_hours=hours,
            series=series,
            max_rate_mm_hr=max_rate,
            total_net_displacement_mm=net_disp
        )

    @staticmethod
    def get_node_health(db: Session) -> List[NodeHealthItem]:
        nodes = NodeService.list_nodes(db=db)
        items = []

        for node in nodes:
            # Estimate packet loss from sequence numbers if present
            recent_seqs = (
                db.query(TelemetryRecord.sequence_number)
                .filter(
                    TelemetryRecord.node_id == node.node_id,
                    TelemetryRecord.sequence_number.isnot(None)
                )
                .order_by(desc(TelemetryRecord.timestamp))
                .limit(50)
                .all()
            )
            seq_list = [s[0] for s in recent_seqs if s[0] is not None]
            loss_pct = 0.0
            if len(seq_list) > 1:
                expected = max(seq_list) - min(seq_list) + 1
                received = len(set(seq_list))
                if expected > received:
                    loss_pct = round(((expected - received) / expected) * 100.0, 1)

            # Quality status
            quality = "NOMINAL"
            if node.connectivity_status == "OFFLINE":
                quality = "NO_SIGNAL"
            elif node.battery_pct is not None and node.battery_pct <= 20.0:
                quality = "BATTERY_LOW"
            elif loss_pct > 10.0:
                quality = "HIGH_PACKET_LOSS"

            items.append(NodeHealthItem(
                node_id=node.node_id,
                name=node.name,
                connectivity_status=node.connectivity_status,
                last_seen=node.last_seen,
                battery_pct=node.battery_pct,
                packet_loss_estimate_pct=loss_pct,
                quality_status=quality,
                drift_detected=False
            ))

        return items
