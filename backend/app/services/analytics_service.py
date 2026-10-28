import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.db.models import SensorNode, TelemetryRecord, Alert
from backend.app.services.node_service import NodeService
from backend.app.schemas.analytics import (
    AnalyticsSummaryResponse, NodeHealthItem, TrendResponse, TrendSeriesPoint,
    SpatialCorroborationItem, SpatialCorroborationResponse
)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in metres between two WGS84 geographic coordinates."""
    r = 6371000.0  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class AnalyticsService:
    @staticmethod
    def get_summary(db: Session, simulator_running: bool = False) -> AnalyticsSummaryResponse:
        nodes, total_nodes = NodeService.list_nodes(db=db, limit=1000)
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

        latest = db.query(TelemetryRecord).order_by(desc(TelemetryRecord.timestamp)).first()
        last_telemetry_at = latest.timestamp if latest else None

        completeness = round((online_nodes / total_nodes * 100.0), 1) if total_nodes > 0 else 0.0

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
    ) -> Optional[TrendResponse]:
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        if not node:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == node_id,
                TelemetryRecord.timestamp >= cutoff
            )
            .order_by(TelemetryRecord.timestamp.asc())
            .limit(2000)
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
        nodes, _ = NodeService.list_nodes(db=db, limit=1000)
        items = []

        for node in nodes:
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

    @staticmethod
    def get_spatial_corroboration(db: Session, max_cluster_dist_m: float = 600.0) -> SpatialCorroborationResponse:
        """
        Evaluate spatial clustering and peer corroboration across active monitoring nodes.
        If multiple neighbouring nodes within max_cluster_dist_m exhibit displacement,
        the hazard is corroborated. Single isolated displacements are flagged for sensor check.
        """
        nodes, _ = NodeService.list_nodes(db=db, limit=500)
        now = datetime.now(timezone.utc)

        # Retrieve latest displacement for each node
        latest_disp_map: Dict[str, float] = {}
        for n in nodes:
            rec = (
                db.query(TelemetryRecord.displacement_mm)
                .filter(TelemetryRecord.node_id == n.node_id, TelemetryRecord.displacement_mm.isnot(None))
                .order_by(desc(TelemetryRecord.timestamp))
                .first()
            )
            if rec and rec[0] is not None:
                latest_disp_map[n.node_id] = rec[0]

        # Simple single-linkage spatial clustering
        visited = set()
        clusters: List[SpatialCorroborationItem] = []
        cluster_idx = 1

        for i, n1 in enumerate(nodes):
            if n1.node_id in visited:
                continue

            current_group = [n1]
            visited.add(n1.node_id)

            for j, n2 in enumerate(nodes):
                if n2.node_id not in visited and i != j:
                    dist = haversine_distance_m(n1.latitude, n1.longitude, n2.latitude, n2.longitude)
                    if dist <= max_cluster_dist_m:
                        current_group.append(n2)
                        visited.add(n2.node_id)

            group_ids = [n.node_id for n in current_group]
            centroid_lat = sum(n.latitude for n in current_group) / len(current_group)
            centroid_lon = sum(n.longitude for n in current_group) / len(current_group)

            disps = [latest_disp_map[nid] for nid in group_ids if nid in latest_disp_map]
            avg_disp = round(sum(disps) / len(disps), 3) if disps else 0.0

            moving_count = sum(1 for d in disps if abs(d) >= 10.0)

            if len(current_group) > 1 and moving_count >= 2:
                status = "CORROBORATED_HAZARD"
                desc_text = f"Corroborated deformation across {len(current_group)} adjacent nodes ({', '.join(group_ids)}). Average displacement: {avg_disp:.2f} mm."
            elif moving_count == 1:
                status = "ISOLATED_EVENT"
                desc_text = f"Single isolated node displacement detected in cluster. Check physical benchmark or transducer mounting."
            else:
                status = "STABLE_CLUSTER"
                desc_text = f"Nominal stability across {len(current_group)} nodes in this sector."

            clusters.append(SpatialCorroborationItem(
                cluster_id=f"CLUSTER-SEC-{cluster_idx:02d}",
                node_ids=group_ids,
                centroid_lat=round(centroid_lat, 5),
                centroid_lon=round(centroid_lon, 5),
                average_displacement_mm=avg_disp,
                corroboration_status=status,
                description=desc_text
            ))
            cluster_idx += 1

        return SpatialCorroborationResponse(
            timestamp=now,
            active_clusters=clusters
        )
