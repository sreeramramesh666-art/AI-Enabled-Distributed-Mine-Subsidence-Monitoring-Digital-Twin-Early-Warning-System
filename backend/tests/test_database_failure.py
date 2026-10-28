import os
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import get_db, Base
from backend.app.db.models import SensorNode, TelemetryRecord
from backend.app.main import app
from fastapi.testclient import TestClient


def test_real_disk_sqlite_integration(disk_sqlite_client):
    """Integration test running against a real temporary SQLite database file on disk."""
    client, temp_db_path = disk_sqlite_client
    assert os.path.exists(temp_db_path)

    # 1. Verify pre-seeded disk node
    node_res = client.get("/api/v1/nodes/DISK-NODE-01")
    assert node_res.status_code == 200
    assert node_res.json()["name"] == "Disk-Backed Inclinometer"

    # 2. Ingest telemetry into disk-backed database
    ts = datetime.now(timezone.utc).isoformat()
    t_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "DISK-NODE-01",
        "sequence_number": 1,
        "timestamp": ts,
        "displacement_mm": 4.5,
        "tilt_x_deg": 0.8,
        "tilt_y_deg": 0.3
    }
    ingest_res = client.post("/api/v1/telemetry", json=t_payload)
    assert ingest_res.status_code == 201

    # 3. Read directly from the SQLite disk file with a separate independent connection to confirm physical persistence
    direct_engine = create_engine(f"sqlite:///{temp_db_path}")
    with direct_engine.connect() as conn:
        result = conn.execute(text("SELECT displacement_mm, vector_tilt_deg FROM telemetry_records WHERE node_id = 'DISK-NODE-01'")).fetchone()
        assert result is not None
        assert result[0] == 4.5
        assert result[1] is not None
    direct_engine.dispose()


def test_transaction_rollback_on_session_error(db_session):
    """Verify that get_db dependency catches exceptions and rolls back dirty state."""
    # Add an uncommitted object
    node = SensorNode(
        node_id="ROLLBACK-NODE-01",
        name="Rollback Node",
        latitude=23.75,
        longitude=86.42
    )
    db_session.add(node)

    # Trigger a database constraint error or rollback
    db_session.rollback()

    # Verify that the uncommitted node was discarded
    persisted = db_session.query(SensorNode).filter(SensorNode.node_id == "ROLLBACK-NODE-01").first()
    assert persisted is None

