import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import func
from backend.app.db.models import Alert, AuditEvent, SensorNode


def get_recommended_action(severity: str, category: str, triggering_rule: str) -> str:
    rule_upper = triggering_rule.upper() if triggering_rule else ""
    cat_upper = category.upper() if category else ""
    sev_upper = severity.upper() if severity else ""

    if "ACCELERATION" in rule_upper or "CRITICAL_ACCELERATION" in rule_upper:
        return "Immediate safety protocol: Evacuate active bench workers within 200m radius; halt haulage traffic; dispatch geotechnical survey team to verify tertiary creep crack progression."
    elif "CRITICAL_DISPLACEMENT" in rule_upper or (sev_upper == "CRITICAL" and cat_upper == "DISPLACEMENT"):
        return "High priority: Restrict heavy vehicle movements along highwall bench; inspect tension crack depth with borehole camera; verify datum benchmark anchors."
    elif "CRITICAL_TILT" in rule_upper or (sev_upper == "CRITICAL" and cat_upper == "TILT"):
        return "Urgent geotechnical check: Physical slope angle departure exceeding critical limits; check inclinometer casing integrity; inspect toe for bulging."
    elif "VIBRATION" in cat_upper or "BLAST" in rule_upper:
        return "Blast / dynamic vibration warning: Compare vibration peak with blasting timetable; verify that ground displacement remains within normal limits."
    elif "DATA_UNRELIABLE" in sev_upper or "STALE" in rule_upper or "DRIFT" in cat_upper:
        return "Sensor diagnostic notice: Check RF antenna line-of-sight, battery rail terminal voltage, and transducer wiring harness. Do not assume slope is safe."
    elif sev_upper == "WARNING":
        return "Geotechnical advisory: Increase monitoring frequency; inspect local tension cracks; verify sensor baseline calibration."
    else:
        return "Review real-time trend graphs and inspect sensor node physical mounting."


class AlertService:
    @staticmethod
    def get_alert(db: Session, alert_id: str) -> Optional[Alert]:
        return db.query(Alert).filter(Alert.alert_id == alert_id).first()

    @staticmethod
    def list_alerts(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        node_id: Optional[str] = None,
        mine_panel: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
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
        if category:
            query = query.filter(Alert.category == category.upper())
        if node_id:
            query = query.filter(Alert.node_id == node_id)
        if mine_panel:
            query = query.filter(Alert.mine_panel == mine_panel)
        if start_time:
            query = query.filter(Alert.created_at >= start_time)
        if end_time:
            query = query.filter(Alert.created_at <= end_time)

        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

        active_crit = db.query(func.count(Alert.id)).filter(
            Alert.status.in_(["ACTIVE", "UNDER_INVESTIGATION", "REOPENED"]), Alert.severity == "CRITICAL"
        ).scalar() or 0

        active_warn = db.query(func.count(Alert.id)).filter(
            Alert.status.in_(["ACTIVE", "UNDER_INVESTIGATION", "REOPENED"]), Alert.severity == "WARNING"
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
        evidence: Dict[str, Any],
        test_run_id: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Create alert if no matching ACTIVE alert exists for (node_id, triggering_rule).
        Handles deduplication and severity escalation without alarm storms.
        """
        sev_rank = {"INFO": 1, "WATCH": 2, "WARNING": 3, "DATA_UNRELIABLE": 4, "CRITICAL": 5}
        new_sev = severity.upper()
        new_rank = sev_rank.get(new_sev, 3)

        # Lookup mine_panel from SensorNode
        node = db.query(SensorNode).filter(SensorNode.node_id == node_id).first()
        panel_name = node.mine_panel if node else None

        existing = db.query(Alert).filter(
            Alert.node_id == node_id,
            Alert.triggering_rule == triggering_rule,
            Alert.status.in_(["ACTIVE", "ACKNOWLEDGED", "UNDER_INVESTIGATION"])
        ).first()

        if not existing:
            # Check if there is an active alert in the same category that should be escalated
            existing = db.query(Alert).filter(
                Alert.node_id == node_id,
                Alert.category == category.upper(),
                Alert.status.in_(["ACTIVE", "ACKNOWLEDGED", "UNDER_INVESTIGATION"])
            ).first()

        recommended = get_recommended_action(new_sev, category, triggering_rule)
        now_utc = datetime.now(timezone.utc)

        if existing:
            old_rank = sev_rank.get(existing.severity, 3)
            if new_rank > old_rank:
                # Severity Escalation
                old_sev = existing.severity
                existing.severity = new_sev
                existing.triggering_rule = triggering_rule
                existing.title = title
                existing.description = description
                existing.evidence = evidence
                existing.recommended_action = recommended

                history = list(existing.lifecycle_history or [])
                history.append({
                    "action": "ESCALATE",
                    "from_severity": old_sev,
                    "to_severity": new_sev,
                    "rule": triggering_rule,
                    "timestamp": now_utc.isoformat()
                })
                existing.lifecycle_history = history
                flag_modified(existing, "lifecycle_history")

                audit = AuditEvent(
                    category="ALERT_LIFECYCLE",
                    node_id=node_id,
                    alert_id=existing.alert_id,
                    actor="analytics_engine",
                    action="ESCALATE_ALERT",
                    outcome="SUCCESS",
                    details={"old_severity": old_sev, "new_severity": new_sev, "from_severity": old_sev, "to_severity": new_sev, "rule": triggering_rule}
                )
                db.add(audit)
                db.flush()
            else:
                # Evidence refresh on active alert
                existing.evidence = evidence
                db.flush()
            return existing

        initial_history = [{
            "action": "CREATED",
            "severity": new_sev,
            "rule": triggering_rule,
            "timestamp": now_utc.isoformat()
        }]

        new_alert = Alert(
            alert_id=str(uuid.uuid4()),
            node_id=node_id,
            test_run_id=test_run_id,
            mine_panel=panel_name,
            sensor_type=category.upper(),
            severity=new_sev,
            category=category.upper(),
            status="ACTIVE",
            title=title,
            description=description,
            recommended_action=recommended,
            triggering_rule=triggering_rule,
            evidence=evidence,
            lifecycle_history=initial_history,
            created_at=now_utc
        )
        db.add(new_alert)

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=node_id,
            alert_id=new_alert.alert_id,
            actor="analytics_engine",
            action="CREATE_ALERT",
            outcome="SUCCESS",
            details={"severity": new_sev, "rule": triggering_rule}
        )
        db.add(audit)
        db.flush()
        return new_alert

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: str, actor: str, note: Optional[str] = None) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return None

        if alert.status == "RESOLVED":
            raise ValueError(f"Alert '{alert_id}' is already resolved and cannot be acknowledged.")

        now_utc = datetime.now(timezone.utc)
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = actor
        alert.acknowledged_at = now_utc
        alert.acknowledgement_note = note

        history = list(alert.lifecycle_history or [])
        history.append({
            "action": "ACKNOWLEDGE",
            "actor": actor,
            "note": note,
            "timestamp": now_utc.isoformat()
        })
        alert.lifecycle_history = history
        flag_modified(alert, "lifecycle_history")

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
    def investigate_alert(db: Session, alert_id: str, actor: str, notes: Optional[str] = None) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return None

        now_utc = datetime.now(timezone.utc)
        alert.status = "UNDER_INVESTIGATION"
        alert.investigated_by = actor
        alert.investigated_at = now_utc
        alert.investigation_notes = notes

        history = list(alert.lifecycle_history or [])
        history.append({
            "action": "UNDER_INVESTIGATION",
            "actor": actor,
            "notes": notes,
            "timestamp": now_utc.isoformat()
        })
        alert.lifecycle_history = history
        flag_modified(alert, "lifecycle_history")

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=alert.node_id,
            alert_id=alert.alert_id,
            actor=actor,
            action="INVESTIGATE_ALERT",
            outcome="SUCCESS",
            details={"investigation_notes": notes}
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

        now_utc = datetime.now(timezone.utc)
        alert.status = "RESOLVED"
        alert.resolved_by = actor
        alert.resolved_at = now_utc
        alert.resolution_notes = resolution_notes

        history = list(alert.lifecycle_history or [])
        history.append({
            "action": "RESOLVE",
            "actor": actor,
            "resolution_notes": resolution_notes,
            "timestamp": now_utc.isoformat()
        })
        alert.lifecycle_history = history
        flag_modified(alert, "lifecycle_history")

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

    @staticmethod
    def reopen_alert(db: Session, alert_id: str, actor: str, reason: str) -> Optional[Alert]:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            return None

        now_utc = datetime.now(timezone.utc)
        alert.status = "REOPENED"
        alert.reopened_by = actor
        alert.reopened_at = now_utc
        alert.reopen_notes = reason

        history = list(alert.lifecycle_history or [])
        history.append({
            "action": "REOPEN",
            "actor": actor,
            "reason": reason,
            "timestamp": now_utc.isoformat()
        })
        alert.lifecycle_history = history
        flag_modified(alert, "lifecycle_history")

        audit = AuditEvent(
            category="ALERT_LIFECYCLE",
            node_id=alert.node_id,
            alert_id=alert.alert_id,
            actor=actor,
            action="REOPEN_ALERT",
            outcome="SUCCESS",
            details={"reason": reason}
        )
        db.add(audit)
        db.commit()
        db.refresh(alert)
        return alert
