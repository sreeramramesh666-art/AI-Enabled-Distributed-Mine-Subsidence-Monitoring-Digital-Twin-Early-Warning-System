from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.database import get_db
from backend.app.db.models import TelemetryRecord
from backend.app.schemas.node import (
    SensorNodeCreate, SensorNodeUpdate, SensorNodeResponse, SensorNodeList,
    NodeBaselineResponse, NodeBaselineRecalculate
)
from backend.app.schemas.telemetry import TelemetryResponse
from backend.app.services.node_service import NodeService
from backend.app.core.security import parse_query_datetime

router = APIRouter(prefix="/nodes", tags=["Sensor Nodes"])


@router.get("", response_model=SensorNodeList)
def list_nodes(
    status: Optional[str] = Query(None, description="Filter by connectivity: ONLINE, STALE, OFFLINE"),
    node_type: Optional[str] = Query(None, description="Filter by node hardware type"),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    mine_panel: Optional[str] = Query(None, description="Filter by mine panel, e.g. Panel-North-01"),
    search: Optional[str] = Query(None, description="Search by node_id or name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    nodes, total = NodeService.list_nodes(
        db=db,
        status=status,
        node_type=node_type,
        is_enabled=is_enabled,
        mine_panel=mine_panel,
        search=search,
        skip=skip,
        limit=limit
    )
    return SensorNodeList(total=total, items=nodes)


@router.post("", response_model=SensorNodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(node_in: SensorNodeCreate, db: Session = Depends(get_db)):
    try:
        return NodeService.create_node(db=db, node_in=node_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{node_id}", response_model=SensorNodeResponse)
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")
    return node


@router.patch("/{node_id}", response_model=SensorNodeResponse)
def update_node(node_id: str, node_in: SensorNodeUpdate, db: Session = Depends(get_db)):
    node = NodeService.update_node(db=db, node_id=node_id, node_in=node_in)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")
    return node


@router.delete("/{node_id}", status_code=status.HTTP_200_OK)
def delete_node(
    node_id: str,
    hard_delete: bool = Query(False, description="True to permanently delete; False to disable"),
    db: Session = Depends(get_db)
):
    success = NodeService.delete_node(db=db, node_id=node_id, hard_delete=hard_delete)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")
    return {"message": f"Sensor node '{node_id}' {'permanently deleted' if hard_delete else 'disabled'} successfully."}


@router.get("/{node_id}/baseline", response_model=NodeBaselineResponse)
def get_node_baseline(node_id: str, db: Session = Depends(get_db)):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")

    baseline = NodeService.get_baseline(db=db, node_id=node_id)
    if not baseline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Baseline not initialized for node '{node_id}'")
    return baseline


@router.post("/{node_id}/baseline/recalculate", response_model=NodeBaselineResponse)
def recalculate_node_baseline(
    node_id: str,
    body: Optional[NodeBaselineRecalculate] = None,
    db: Session = Depends(get_db)
):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")

    hours = body.period_hours if body else 72.0
    baseline = NodeService.recalculate_baseline(db=db, node_id=node_id, period_hours=hours)
    return baseline


@router.get("/{node_id}/telemetry", response_model=List[TelemetryResponse])
def get_node_telemetry(
    node_id: str,
    start_time: Optional[str] = Query(None, description="Start timestamp ISO 8601"),
    end_time: Optional[str] = Query(None, description="End timestamp ISO 8601"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")

    try:
        parsed_start = parse_query_datetime(start_time)
        parsed_end = parse_query_datetime(end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be earlier than or equal to end_time")

    query = db.query(TelemetryRecord).filter(TelemetryRecord.node_id == node_id)
    if parsed_start:
        query = query.filter(TelemetryRecord.timestamp >= parsed_start)
    if parsed_end:
        query = query.filter(TelemetryRecord.timestamp <= parsed_end)

    records = query.order_by(desc(TelemetryRecord.timestamp)).offset(skip).limit(limit).all()
    return records
