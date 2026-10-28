import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.db.models import SensorNode, NodeBaseline, TelemetryRecord


def test_test_run_lifecycle(client: TestClient, db_session):
    # 1. Start a test run
    start_payload = {
        "name": "Benchmark Lab Test #1",
        "scenario": "testrig_gradual",
        "test_conditions": "Controlled granular box with micrometer lead screw",
        "target_node_id": "TEST-NODE-01",
        "intended_movement_mm": 5.0,
        "notes": "Testing 5mm displacement on dial gauge"
    }
    resp = client.post("/api/v1/test-runs", json=start_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "RUNNING"
    assert data["scenario"] == "testrig_gradual"
    test_run_id = data["test_run_id"]

    # 2. Ingest telemetry associated with this test run
    t1 = {
        "node_id": "TEST-NODE-01",
        "event_id": "ev-tr-001",
        "sequence_number": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 0.05,
        "tilt_x_deg": 0.02,
        "tilt_y_deg": -0.01,
        "vibration_rms_ms2": 0.05,
        "test_run_id": test_run_id
    }
    r_t1 = client.post("/api/v1/telemetry", json=t1)
    assert r_t1.status_code == 201
    t1_data = r_t1.json()
    assert t1_data["test_run_id"] == test_run_id
    assert t1_data["sensor_quality_state"] == "valid"

    t2 = {
        "node_id": "TEST-NODE-01",
        "event_id": "ev-tr-002",
        "sequence_number": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "displacement_mm": 5.02,
        "tilt_x_deg": 0.25,
        "tilt_y_deg": 0.10,
        "vibration_rms_ms2": 0.08,
        "test_run_id": test_run_id
    }
    r_t2 = client.post("/api/v1/telemetry", json=t2)
    assert r_t2.status_code == 201

    # 3. Record independent reference movement
    ref_payload = {
        "reference_movement_mm": 5.00,
        "notes": "Micrometer barrel reading 5.00mm exactly"
    }
    resp_ref = client.post(f"/api/v1/test-runs/{test_run_id}/reference", json=ref_payload)
    assert resp_ref.status_code == 200
    assert resp_ref.json()["reference_movement_mm"] == 5.00

    # 4. Complete the test run
    comp_payload = {"notes": "Test concluded with verified micrometer movement"}
    resp_comp = client.post(f"/api/v1/test-runs/{test_run_id}/complete", json=comp_payload)
    assert resp_comp.status_code == 200
    completed = resp_comp.json()
    assert completed["status"] == "COMPLETED"
    assert completed["sensor_reported_movement_mm"] is not None
    # 5.02 - 0.05 = 4.97 mm reported movement
    assert abs(completed["sensor_reported_movement_mm"] - 4.97) < 0.01
    assert completed["measurement_error_mm"] is not None
    # error = |4.97 - 5.00| = 0.03 mm
    assert completed["measurement_error_mm"] < 0.1
    assert completed["metrics"] is not None
    assert "packet_delivery_ratio_pct" in completed["metrics"]
    assert "false_alerts_denominator" in completed["metrics"]

    # 5. List test runs
    resp_list = client.get("/api/v1/test-runs")
    assert resp_list.status_code == 200
    assert resp_list.json()["total"] >= 1

    # 6. Export CSV
    resp_csv = client.get(f"/api/v1/test-runs/{test_run_id}/export/csv")
    assert resp_csv.status_code == 200
    assert "Table 12 Format" in resp_csv.text
    assert "Telemetry Series During Test Run" in resp_csv.text

    # 7. Export PDF
    resp_pdf = client.get(f"/api/v1/test-runs/{test_run_id}/export/pdf")
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 1000

