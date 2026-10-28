import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.core.config import settings
from backend.app.db.models import SensorNode, AuditEvent, NodeBaseline, TelemetryRecord
from backend.app.schemas.node import SensorNodeCreate, SensorNodeUpdate


def refresh_node_connectivity(node: SensorNode, now: Optional[datetime] = None) -> str:
    """Evaluate whether node is ONLINE, STALE, or OFFLINE based on last_seen timestamp."""
    if not node.is_enabled:
        return "OFFLINE"

    if node.last_seen is None:
        return "OFFLINE"

    if now is None:
        now = datetime.now(timezone.utc)

    ls = node.last_seen
    if ls.tzinfo is None:
        ls = ls.replace(tzinfo=timezone.utc)

    elapsed_sec = (now - ls).total_seconds()
    if elapsed_sec <= settings.STALE_DATA_TIMEOUT_SEC:
        return "ONLINE"
    elif elapsed_sec <= settings.STALE_DATA_TIMEOUT_SEC * 3:
        return "STALE"
    else:
        return "OFFLINE"


class NodeService:
    @staticmethod
    def get_node(db: Session, node_id: str) -> Optional[SensorNode]:
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        if node:
            status = refresh_node_connectivity(node)
            if node.connectivity_status != status:
                node.connectivity_status = status
                db.commit()
                db.refresh(node)
        return node

    @staticmethod
    def list_nodes(
        db: Session,
        status: Optional[str] = None,
        node_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        mine_panel: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[SensorNode], int]:
        now = datetime.now(timezone.utc)
        
        # First update connectivity statuses for all enabled nodes
        all_nodes = db.query(SensorNode).all()
        updated = False
        for node in all_nodes:
            new_st = refresh_node_connectivity(node, now)
            if node.connectivity_status != new_st:
                node.connectivity_status = new_st
                updated = True
        if updated:
            db.commit()

        # Build query
        query = db.query(SensorNode)
        if status:
            query = query.filter(SensorNode.connectivity_status == status.upper())
        if node_type:
            query = query.filter(SensorNode.node_type == node_type)
        if is_enabled is not None:
            query = query.filter(SensorNode.is_enabled == is_enabled)
        if mine_panel:
            query = query.filter(SensorNode.mine_panel == mine_panel)
        if search:
            search_pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    SensorNode.node_id.ilike(search_pat),
                    SensorNode.name.ilike(search_pat),
                    SensorNode.installation_location.ilike(search_pat),
                    SensorNode.mine_panel.ilike(search_pat),
                )
            )

        total = query.count()
        items = query.order_by(SensorNode.created_at.asc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def count_nodes(db: Session) -> int:
        return db.query(func.count(SensorNode.node_id)).scalar() or 0

    @staticmethod
    def create_node(db: Session, node_in: SensorNodeCreate) -> SensorNode:
        existing = db.query(SensorNode).filter(SensorNode.node_id == node_in.node_id).first()
        if existing:
            raise ValueError(f"Sensor node '{node_in.node_id}' already registered.")

        node = SensorNode(
            node_id=node_in.node_id,
            name=node_in.name,
            latitude=node_in.latitude,
            longitude=node_in.longitude,
            elevation_m=node_in.elevation_m,
            node_type=node_in.node_type,
            installation_location=node_in.installation_location,
            mine_panel=node_in.mine_panel,
            depth_m=node_in.depth_m,
            extraction_method=node_in.extraction_method,
            geological_context=node_in.geological_context,
            sampling_interval_sec=node_in.sampling_interval_sec or 5.0,
            last_calibration_date=node_in.last_calibration_date,
            calibration_status=node_in.calibration_status or "nominal",
            firmware_version=node_in.firmware_version,
            is_enabled=node_in.is_enabled,
            connectivity_status="OFFLINE"
        )
        db.add(node)

        # Initialize empty baseline
        baseline = NodeBaseline(node_id=node.node_id, is_valid=False)
        db.add(baseline)

        # Audit event
        audit = AuditEvent(
            category="NODE_MANAGEMENT",
            node_id=node.node_id,
            actor="admin",
            action="CREATE_NODE",
            outcome="SUCCESS",
            details={"name": node.name, "type": node.node_type}
        )
        db.add(audit)

        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def update_node(db: Session, node_id: str, node_in: SensorNodeUpdate) -> Optional[SensorNode]:
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        if not node:
            return None

        update_data = node_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(node, key, val)

        node.updated_at = datetime.now(timezone.utc)

        audit = AuditEvent(
            category="NODE_MANAGEMENT",
            node_id=node_id,
            actor="admin",
            action="UPDATE_NODE",
            outcome="SUCCESS",
            details=update_data
        )
        db.add(audit)

        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def delete_node(db: Session, node_id: str, hard_delete: bool = False) -> bool:
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        if not node:
            return False

        if hard_delete:
            db.delete(node)
            action = "HARD_DELETE_NODE"
        else:
            node.is_enabled = False
            node.connectivity_status = "OFFLINE"
            node.updated_at = datetime.now(timezone.utc)
            action = "DISABLE_NODE"

        audit = AuditEvent(
            category="NODE_MANAGEMENT",
            node_id=node_id,
            actor="admin",
            action=action,
            outcome="SUCCESS",
            details={"hard_delete": hard_delete}
        )
        db.add(audit)
        db.commit()
        return True

    @staticmethod
    def get_baseline(db: Session, node_id: str) -> Optional[NodeBaseline]:
        return db.query(NodeBaseline).filter(NodeBaseline.node_id == node_id).first()

    @staticmethod
    def recalculate_baseline(db: Session, node_id: str, period_hours: float = 72.0) -> Optional[NodeBaseline]:
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        if not node:
            return None

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=period_hours)

        records = (
            db.query(TelemetryRecord)
            .filter(
                TelemetryRecord.node_id == node_id,
                TelemetryRecord.timestamp >= start_time,
                TelemetryRecord.timestamp <= now
            )
            .order_by(TelemetryRecord.timestamp.asc())
            .all()
        )

        baseline = db.query(NodeBaseline).filter(NodeBaseline.node_id == node_id).first()
        if not baseline:
            baseline = NodeBaseline(node_id=node_id)
            db.add(baseline)

        baseline.calculation_period_start = start_time
        baseline.calculation_period_end = now
        baseline.sample_count = len(records)
        baseline.updated_at = now

        if len(records) >= 5:
            disps = [r.displacement_mm for r in records if r.displacement_mm is not None]
            tilts_x = [r.tilt_x_deg for r in records if r.tilt_x_deg is not None]
            tilts_y = [r.tilt_y_deg for r in records if r.tilt_y_deg is not None]
            temps = [r.temperature_c for r in records if r.temperature_c is not None]

            def calc_mean_std(vals):
                if not vals:
                    return None, None
                mean_val = sum(vals) / len(vals)
                if len(vals) > 1:
                    variance = sum((x - mean_val) ** 2 for x in vals) / (len(vals) - 1)
                    std_val = math.sqrt(variance)
                else:
                    std_val = 0.0
                return round(mean_val, 4), round(std_val, 4)

            disp_mean, disp_std = calc_mean_std(disps)
            tx_mean, tx_std = calc_mean_std(tilts_x)
            ty_mean, ty_std = calc_mean_std(tilts_y)
            temp_mean, _ = calc_mean_std(temps)

            baseline.displacement_mean = disp_mean
            baseline.displacement_std = disp_std
            baseline.tilt_x_mean = tx_mean
            baseline.tilt_x_std = tx_std
            baseline.tilt_y_mean = ty_mean
            baseline.tilt_y_std = ty_std
            baseline.temperature_mean = temp_mean
            baseline.is_valid = True
        else:
            baseline.is_valid = False

        audit = AuditEvent(
            category="CALIBRATION",
            node_id=node_id,
            actor="system",
            action="RECALCULATE_BASELINE",
            outcome="SUCCESS" if baseline.is_valid else "INSUFFICIENT_SAMPLES",
            details={"sample_count": baseline.sample_count, "is_valid": baseline.is_valid}
        )
        db.add(audit)
        db.commit()
        db.refresh(baseline)
        return baseline
