from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.alert import (
    AlertResponse, AlertListResponse, AlertAcknowledge, AlertResolve
)
from backend.app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alert Lifecycle"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    status: Optional[str] = Query(None, description="ACTIVE, ACKNOWLEDGED, RESOLVED"),
    severity: Optional[str] = Query(None, description="CRITICAL, WARNING, WATCH, DATA_UNRELIABLE"),
    node_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    alerts, total, active_crit, active_warn = AlertService.list_alerts(
        db=db, status=status, severity=severity, node_id=node_id, skip=skip, limit=limit
    )
    return AlertListResponse(
        total=total,
        active_critical=active_crit,
        active_warning=active_warn,
        items=alerts
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = AlertService.get_alert(db=db, alert_id=alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: str, body: AlertAcknowledge, db: Session = Depends(get_db)):
    alert = AlertService.acknowledge_alert(
        db=db, alert_id=alert_id, actor=body.acknowledged_by, note=body.note
    )
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: str, body: AlertResolve, db: Session = Depends(get_db)):
    alert = AlertService.resolve_alert(
        db=db, alert_id=alert_id, actor=body.resolved_by, resolution_notes=body.resolution_notes
    )
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert
