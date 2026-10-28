from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import TelemetryRecord, SensorNode
from backend.app.schemas.analytics import (
    AnalyticsSummaryResponse, TrendResponse, NodeHealthItem, SpatialCorroborationResponse
)
from backend.app.services.analytics_service import AnalyticsService
from backend.app.simulator.engine import simulator_engine
from backend.app.analytics.anomaly_detection import ml_detector

router = APIRouter(prefix="/analytics", tags=["Analytics & Decision Support"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(db: Session = Depends(get_db)):
    return AnalyticsService.get_summary(db=db, simulator_running=simulator_engine.is_running)


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    node_id: str,
    hours: float = Query(24.0, ge=0.5, le=720.0),
    db: Session = Depends(get_db)
):
    trends = AnalyticsService.get_trends(db=db, node_id=node_id, hours=hours)
    if not trends:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sensor node '{node_id}' not found")
    return trends


@router.get("/node-health", response_model=List[NodeHealthItem])
def get_node_health(db: Session = Depends(get_db)):
    return AnalyticsService.get_node_health(db=db)


@router.get("/spatial-corroboration", response_model=SpatialCorroborationResponse)
def get_spatial_corroboration(
    max_dist_m: float = Query(600.0, ge=50.0, le=5000.0, description="Maximum neighbour clustering distance in metres"),
    db: Session = Depends(get_db)
):
    """Calculate multi-node spatial corroboration to distinguish localized sensor faults from true ground movement."""
    return AnalyticsService.get_spatial_corroboration(db=db, max_cluster_dist_m=max_dist_m)


@router.get("/ml-status")
def get_ml_status():
    return ml_detector.get_status()


@router.post("/ml-train")
def train_ml_baseline(db: Session = Depends(get_db)):
    """Train or retrain unsupervised Isolation Forest on clean baseline records."""
    records = db.query(TelemetryRecord).filter(
        TelemetryRecord.data_source.in_(["simulator", "rest", "mqtt"])
    ).limit(1000).all()

    record_dicts = [
        {
            "displacement_mm": r.displacement_mm,
            "tilt_x_deg": r.tilt_x_deg,
            "tilt_y_deg": r.tilt_y_deg,
            "velocity_mm_hr": r.velocity_mm_hr,
            "vibration_rms_ms2": r.vibration_rms_ms2,
            "temperature_c": r.temperature_c
        }
        for r in records
    ]

    success = ml_detector.fit_baseline(record_dicts)
    return {
        "success": success,
        "sample_count": len(record_dicts),
        "status": ml_detector.get_status()
    }
