import uuid
from datetime import datetime, timezone


def test_telemetry_ingest_and_deduplication(client):
    event_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()

    payload = {
        "event_id": event_id,
        "node_id": "TEST-NODE-01",
        "sequence_number": 1,
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

    # Duplicate ingestion fails with 409
    res2 = client.post("/api/v1/telemetry", json=payload)
    assert res2.status_code == 409


def test_telemetry_out_of_bounds_rejection(client):
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 99999.0  # Physically impossible value
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code in [422, 400]


def test_telemetry_batch_replay(client):
    batch_payload = {
        "records": [
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "TEST-NODE-01",
                "sequence_number": 10,
                "timestamp": "2026-10-27T10:00:00Z",
                "displacement_mm": 1.0
            },
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "TEST-NODE-01",
                "sequence_number": 11,
                "timestamp": "2026-10-27T10:01:00Z",
                "displacement_mm": 1.2
            }
        ]
    }
    res = client.post("/api/v1/telemetry/batch", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ingested_count"] == 2
    assert data["duplicates_skipped"] == 0
