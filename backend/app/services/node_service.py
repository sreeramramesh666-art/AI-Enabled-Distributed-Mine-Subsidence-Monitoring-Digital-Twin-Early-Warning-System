from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.config import settings
from backend.app.db.models import SensorNode, AuditEvent, NodeBaseline
from backend.app.schemas.node import SensorNodeCreate, SensorNodeUpdate


def refresh_node_connectivity(node: SensorNode, now: Optional[datetime] = None) -> str:
    """Evaluate whether node is ONLINE, STALE, or OFFLINE based on last_seen timestamp."""
    if not node.is_enabled:
        return "OFFLINE"

    if node.last_seen is None:
        return "OFFLINE"

    if now is None:
        now = datetime.now(timezone.utc)

    # Ensure last_seen is timezone-aware
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
        return node

    @staticmethod
    def list_nodes(
        db: Session,
        status: Optional[str] = None,
        node_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SensorNode]:
        now = datetime.now(timezone.utc)
        query = db.query(SensorNode)
        if node_type:
            query = query.filter(SensorNode.node_type == node_type)

        nodes = query.offset(skip).limit(limit).all()

        # Update connectivity statuses in batch
        updated = False
        for node in nodes:
            cur_status = refresh_node_connectivity(node, now)
            if node.connectivity_status != cur_status:
                node.connectivity_status = cur_status
                updated = True

        if updated:
            db.commit()

        if status:
            return [n for n in nodes if n.connectivity_status.upper() == status.upper()]

        return nodes

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
