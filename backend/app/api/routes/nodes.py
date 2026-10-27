from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.database import get_db
from backend.app.db.models import TelemetryRecord
from backend.app.schemas.node import (
    SensorNodeCreate, SensorNodeUpdate, SensorNodeResponse, SensorNodeList
)
from backend.app.schemas.telemetry import TelemetryResponse
from backend.app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["Sensor Nodes"])


@router.get("", response_model=SensorNodeList)
def list_nodes(
    status: Optional[str] = Query(None, description="Filter by connectivity: ONLINE, STALE, OFFLINE"),
    node_type: Optional[str] = Query(None, description="Filter by node hardware type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    nodes = NodeService.list_nodes(db=db, status=status, node_type=node_type, skip=skip, limit=limit)
    total = NodeService.count_nodes(db=db)
    return SensorNodeList(total=total, items=nodes)


@router.post("", response_model=SensorNodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(node_in: SensorNodeCreate, db: Session = Depends(get_db)):
    try:
        return NodeService.create_node(db=db, node_in=node_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{node_id}", response_model=SensorNodeResponse)
def get_node(node_id: str, db: Session = Depends(get_db)):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    return node


@router.patch("/{node_id}", response_model=SensorNodeResponse)
def update_node(node_id: str, node_in: SensorNodeUpdate, db: Session = Depends(get_db)):
    node = NodeService.update_node(db=db, node_id=node_id, node_in=node_in)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")
    return node


@router.get("/{node_id}/telemetry", response_model=List[TelemetryResponse])
def get_node_telemetry(
    node_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    node = NodeService.get_node(db=db, node_id=node_id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node '{node_id}' not found")

    query = db.query(TelemetryRecord).filter(TelemetryRecord.node_id == node_id)
    if start_time:
        query = query.filter(TelemetryRecord.timestamp >= start_time)
    if end_time:
        query = query.filter(TelemetryRecord.timestamp <= end_time)

    records = query.order_by(desc(TelemetryRecord.timestamp)).limit(limit).all()
    return records
