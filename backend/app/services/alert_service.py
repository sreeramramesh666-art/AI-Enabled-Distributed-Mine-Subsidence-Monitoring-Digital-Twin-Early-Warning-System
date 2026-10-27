import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.models import Alert, AuditEvent


class AlertService:
    @staticmethod
    def get_alert(db: Session, alert_id: str) -> Optional[Alert]:
        return db.query(Alert).filter(Alert.alert_id == alert_id).first()

    @staticmethod
    def list_alerts(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        node_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Alert], int, int, int]:
        """
        Returns (alerts, total, active_critical, active_warning).
        """
        query = db.query(Alert)
        if status:
            query = query.filter(Alert.status == status.upper())
        if severity:
            query = query.filter(Alert.severity == severity.upper())
        if node_id:
            query = query.filter(Alert.node_id == node_id)

        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

        active_crit = db.query(func.count(Alert.id)).filter(
            Alert.status == "ACTIVE", Alert.severity == "CRITICAL"
        ).scalar() or 0

        active_warn = db.query(func.count(Alert.id)).filter(
            Alert.status == "ACTIVE", Alert.severity == "WARNING"
        ).scalar() or 0

        return alerts, total, active_crit, active_warn

    @staticmethod
    def create_or_deduplicate_alert(
        db: Session,
        node_id: str,
        severity: str,
        category: str,
        title: str,
        description: str,
        triggering_rule: str,
        evidence: Dict[str, Any]
    ) -> Optional[Alert]:
        """
        Create alert if no matching ACTIVE alert exists for (node_id, triggering_rule).
        Prevents alarm storms while ensuring new distinct hazards trigger immediate alerts.
        """
        existing = db.query(Alert).filter(
            Alert.node_id == node_id,
            Alert.triggering_rule == triggering_rule,
            Alert.status == "ACTIVE"
        ).first()

        if existing:
            # Update evidence and timestamp if severity escalated
            existing.evidence = evidence
            db.commit()
            return existing

        new_alert = Alert(
            alert_id=str(uuid.uuid4()),
            node_id=node_id,
            severity=severity.upper(),
            category=category.upper(),
            status="ACTIVE",
            title=title,
            description=description,
            triggering_rule=triggering_rule,
            evidence=evidence,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_alert)

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=node_id,
            alert_id=new_alert.alert_id,
            actor="analytics_engine",
            action="CREATE_ALERT",
            outcome="SUCCESS",
            details={"severity": severity, "rule": triggering_rule}
        )
        db.add(audit)

        db.commit()
        db.refresh(new_alert)
        return new_alert

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: str, actor: str, note: Optional[str] = None) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return None

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = actor
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledgement_note = note

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=alert.node_id,
            alert_id=alert.alert_id,
            actor=actor,
            action="ACKNOWLEDGE_ALERT",
            outcome="SUCCESS",
            details={"note": note}
        )
        db.add(audit)

        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: str, actor: str, resolution_notes: str) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return None

        alert.status = "RESOLVED"
        alert.resolved_by = actor
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = resolution_notes

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=alert.node_id,
            alert_id=alert.alert_id,
            actor=actor,
            action="RESOLVE_ALERT",
            outcome="SUCCESS",
            details={"resolution_notes": resolution_notes}
        )
        db.add(audit)

        db.commit()
        db.refresh(alert)
        return alert
