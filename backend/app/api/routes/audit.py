from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.database import get_db
from backend.app.db.models import AuditEvent
from backend.app.schemas.audit import AuditEventList
from backend.app.core.security import parse_query_datetime

router = APIRouter(prefix="/audit-events", tags=["Audit Log"])


@router.get("", response_model=AuditEventList)
def list_audit_events(
    category: Optional[str] = Query(None, description="Filter by event category"),
    node_id: Optional[str] = None,
    alert_id: Optional[str] = None,
    actor: Optional[str] = None,
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

    query = db.query(AuditEvent)
    if category:
        query = query.filter(AuditEvent.category == category.upper())
    if node_id:
        query = query.filter(AuditEvent.node_id == node_id)
    if alert_id:
        query = query.filter(AuditEvent.alert_id == alert_id)
    if actor:
        query = query.filter(AuditEvent.actor == actor)
    if parsed_start:
        query = query.filter(AuditEvent.timestamp >= parsed_start)
    if parsed_end:
        query = query.filter(AuditEvent.timestamp <= parsed_end)

    total = query.count()
    items = query.order_by(desc(AuditEvent.timestamp)).offset(skip).limit(limit).all()
    return AuditEventList(total=total, items=items)
