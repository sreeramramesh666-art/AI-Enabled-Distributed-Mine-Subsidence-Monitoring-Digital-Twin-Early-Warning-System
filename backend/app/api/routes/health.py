import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.database import get_db
from backend.app.simulator.engine import simulator_engine
from backend.app.ingestion.mqtt_client import mqtt_gateway
from backend.app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health & Probes"])


@router.get("", status_code=status.HTTP_200_OK)
def check_health(response: Response, db: Session = Depends(get_db)):
    db_status = "connected"
    is_healthy = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        is_healthy = False

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulator_running": simulator_engine.is_running,
        "mqtt_status": "connected" if mqtt_gateway.is_connected else ("disabled" if not settings.MQTT_ENABLED else "disconnected")
    }


@router.get("/liveness", status_code=status.HTTP_200_OK)
def check_liveness():
    """Liveness probe: verifies the process is executing."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/readiness", status_code=status.HTTP_200_OK)
def check_readiness(response: Response, db: Session = Depends(get_db)):
    """Readiness probe: verifies the database connection is responsive."""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True, "database": "connected"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "database": str(e)}


@router.get("/mqtt", status_code=status.HTTP_200_OK)
def check_mqtt_health():
    """Detailed diagnostic status of the MQTT communications gateway client."""
    return mqtt_gateway.get_status()
