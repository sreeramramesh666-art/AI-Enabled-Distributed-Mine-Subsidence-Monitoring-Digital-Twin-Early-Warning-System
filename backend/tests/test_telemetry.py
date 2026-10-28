import uuid
from datetime import datetime, timezone, timedelta


def test_telemetry_ingest_and_deduplication(client):
    event_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()

    payload = {
        "event_id": event_id,
        "node_id": "TEST-NODE-01",
        "sequence_number": 100,
        "timestamp": ts,
        "displacement_mm": 5.25,
        "tilt_x_deg": 0.45,
        "tilt_y_deg": -0.22,
        "vibration_rms_ms2": 0.35,
        "temperature_c": 26.5,
        "battery_pct": 92.0
    }

    # First ingestion succeeds
    res1 = client.post("/api/v1/telemetry", json=payload)
    assert res1.status_code == 201
    data = res1.json()
    assert data["displacement_mm"] == 5.25
    assert data["vector_tilt_deg"] is not None

    # Duplicate by event_id fails with 409
    res2 = client.post("/api/v1/telemetry", json=payload)
    assert res2.status_code == 409

    # Duplicate by sequence number fails with 409
    payload_new_event = {**payload, "event_id": str(uuid.uuid4())}
    res3 = client.post("/api/v1/telemetry", json=payload_new_event)
    assert res3.status_code == 409


def test_telemetry_unknown_and_disabled_node(client):
    # Unknown node returns 404
    unknown_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "NON-EXISTENT-NODE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 1.0
    }
    assert client.post("/api/v1/telemetry", json=unknown_payload).status_code == 404

    # Disabled node returns 400
    disabled_id = f"DIS-NODE-{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/nodes", json={
        "node_id": disabled_id,
        "name": "Disabled Node",
        "latitude": 23.75,
        "longitude": 86.42,
        "is_enabled": False
    })
    dis_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": disabled_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 1.0
    }
    assert client.post("/api/v1/telemetry", json=dis_payload).status_code == 400


def test_telemetry_out_of_bounds_and_future_rejection(client):
    # Physically impossible displacement
    payload_oob = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 99999.0
    }
    res_oob = client.post("/api/v1/telemetry", json=payload_oob)
    assert res_oob.status_code == 422

    # Timestamp in far future (> 5 mins)
    future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    payload_future = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": future_time,
        "displacement_mm": 2.0
    }
    res_future = client.post("/api/v1/telemetry", json=payload_future)
    assert res_future.status_code == 422


def test_telemetry_missing_data_preservation(client):
    """Missing measurements should be accepted as null without defaulting to 0.0 mm."""
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": None,
        "tilt_x_deg": 1.2,
        "tilt_y_deg": None,
        "temperature_c": 29.0
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["displacement_mm"] is None
    assert data["tilt_y_deg"] is None
    assert data["tilt_x_deg"] == 1.2


def test_out_of_order_telemetry_kinematics_correction(client):
    """
    Test that backfilling a delayed record T2 between T1 and T3 recalculates kinematics
    for T2 relative to T1, and corrects T3 relative to T2.
    """
    node_id = f"KIN-NODE-{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/nodes", json={
        "node_id": node_id,
        "name": "Kinematics Test Node",
        "latitude": 23.75,
        "longitude": 86.42
    })

    t1 = datetime(2026, 10, 27, 8, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)  # 2 hours later
    t2 = datetime(2026, 10, 27, 9, 0, 0, tzinfo=timezone.utc)   # 1 hour after t1

    # Ingest T1 (disp = 10.0 mm)
    client.post("/api/v1/telemetry", json={
        "event_id": str(uuid.uuid4()),
        "node_id": node_id,
        "sequence_number": 1,
        "timestamp": t1.isoformat(),
        "displacement_mm": 10.0
    })

    # Ingest T3 (disp = 20.0 mm) -> dt = 2h, delta_d = 10mm -> initial v = 5.0 mm/hr
    res_t3 = client.post("/api/v1/telemetry", json={
        "event_id": str(uuid.uuid4()),
        "node_id": node_id,
        "sequence_number": 3,
        "timestamp": t3.isoformat(),
        "displacement_mm": 20.0
    })
    assert res_t3.json()["velocity_mm_hr"] == 5.0

    # Backfill T2 out of order (disp = 12.0 mm) -> dt = 1h from t1, delta_d = 2mm -> v = 2.0 mm/hr
    # T3 is 1h after T2, delta_d = 20 - 12 = 8mm -> T3 velocity should be corrected to 8.0 mm/hr!
    res_t2 = client.post("/api/v1/telemetry", json={
        "event_id": str(uuid.uuid4()),
        "node_id": node_id,
        "sequence_number": 2,
        "timestamp": t2.isoformat(),
        "displacement_mm": 12.0
    })
    assert res_t2.status_code == 201
    assert res_t2.json()["velocity_mm_hr"] == 2.0

    # Verify T3 telemetry record in database has corrected velocity of 8.0 mm/hr
    history = client.get(f"/api/v1/nodes/{node_id}/telemetry").json()
    t3_record = next(r for r in history if r["sequence_number"] == 3)
    assert t3_record["velocity_mm_hr"] == 8.0


def test_atomic_batch_rollback_on_malformed_entry(client):
    """Ensure atomic batch does not partially corrupt the database if one item fails."""
    node_id = f"BATCH-NODE-{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/nodes", json={
        "node_id": node_id,
        "name": "Batch Test Node",
        "latitude": 23.75,
        "longitude": 86.42
    })

    now = datetime.now(timezone.utc)
    batch_payload = {
        "atomic": True,
        "records": [
            {
                "event_id": str(uuid.uuid4()),
                "node_id": node_id,
                "sequence_number": 1,
                "timestamp": now.isoformat(),
                "displacement_mm": 5.0
            },
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "UNKNOWN-GHOST-NODE",  # Invalid unknown node
                "sequence_number": 2,
                "timestamp": (now + timedelta(seconds=10)).isoformat(),
                "displacement_mm": 6.0
            }
        ]
    }

    res = client.post("/api/v1/telemetry/batch", json=batch_payload)
    assert res.status_code == 422

    # Verify that the valid record was NOT persisted
    records = client.get(f"/api/v1/nodes/{node_id}/telemetry").json()
    assert len(records) == 0


def test_non_atomic_batch_partial_ingest(client):
    """When atomic=False, valid records are ingested and invalid ones are reported."""
    node_id = f"NONATOMIC-{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/nodes", json={
        "node_id": node_id,
        "name": "Non-Atomic Node",
        "latitude": 23.75,
        "longitude": 86.42
    })

    now = datetime.now(timezone.utc)
    batch_payload = {
        "atomic": False,
        "records": [
            {
                "event_id": str(uuid.uuid4()),
                "node_id": node_id,
                "sequence_number": 1,
                "timestamp": now.isoformat(),
                "displacement_mm": 3.0
            },
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "UNKNOWN-GHOST-NODE",
                "sequence_number": 2,
                "timestamp": (now + timedelta(seconds=10)).isoformat(),
                "displacement_mm": 4.0
            }
        ]
    }

    res = client.post("/api/v1/telemetry/batch", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ingested_count"] == 1
    assert len(data["errors"]) >= 1
