from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.alert import (
    AlertResponse, AlertListResponse, AlertAcknowledge, AlertInvestigate, AlertResolve, AlertReopen
)
from backend.app.services.alert_service import AlertService
from backend.app.core.security import parse_query_datetime

router = APIRouter(prefix="/alerts", tags=["Alert Lifecycle"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    status: Optional[str] = Query(None, description="ACTIVE, ACKNOWLEDGED, UNDER_INVESTIGATION, RESOLVED, REOPENED"),
    severity: Optional[str] = Query(None, description="CRITICAL, WARNING, WATCH, DATA_UNRELIABLE"),
    category: Optional[str] = Query(None, description="DISPLACEMENT, VELOCITY, ACCELERATION, TILT, VIBRATION, BATTERY, SENSOR_DRIFT"),
    node_id: Optional[str] = None,
    mine_panel: Optional[str] = Query(None, description="Filter by mine panel"),
    start_time: Optional[str] = Query(None, description="Start timestamp ISO 8601"),
    end_time: Optional[str] = Query(None, description="End timestamp ISO 8601"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    try:
        parsed_start = parse_query_datetime(start_time)
        parsed_end = parse_query_datetime(end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be earlier than or equal to end_time")

    alerts, total, active_crit, active_warn = AlertService.list_alerts(
        db=db,
        status=status,
        severity=severity,
        category=category,
        node_id=node_id,
        mine_panel=mine_panel,
        start_time=parsed_start,
        end_time=parsed_end,
        skip=skip,
        limit=limit
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
    try:
        alert = AlertService.acknowledge_alert(
            db=db, alert_id=alert_id, actor=body.acknowledged_by, note=body.note
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert


@router.post("/{alert_id}/investigate", response_model=AlertResponse)
def investigate_alert(alert_id: str, body: AlertInvestigate, db: Session = Depends(get_db)):
    alert = AlertService.investigate_alert(
        db=db, alert_id=alert_id, actor=body.investigated_by, notes=body.investigation_notes
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


@router.post("/{alert_id}/reopen", response_model=AlertResponse)
def reopen_alert(alert_id: str, body: AlertReopen, db: Session = Depends(get_db)):
    alert = AlertService.reopen_alert(
        db=db, alert_id=alert_id, actor=body.reopened_by, reason=body.reopen_notes
    )
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found")
    return alert
