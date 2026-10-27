from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.database import get_db
from backend.app.simulator.engine import simulator_engine
from backend.app.ingestion.mqtt_client import mqtt_gateway

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def check_health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulator_running": simulator_engine.is_running,
        "mqtt_status": "connected" if mqtt_gateway.is_connected else "disconnected"
    }
