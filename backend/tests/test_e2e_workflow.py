import uuid
from datetime import datetime, timezone, timedelta


def test_full_e2e_mine_monitoring_cycle(client):
    """
    End-to-End integration test covering the complete geotechnical monitoring lifecycle:
    Registration -> Ingestion -> Kinematics -> Alert Trigger -> Acknowledgement -> Resolution -> Reporting.
    """
    # 1. Verify health
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] in ["healthy", "degraded"]

    # 2. Register a new bench node
    node_id = f"NODE-HIGHWALL-{uuid.uuid4().hex[:6]}"
    reg_res = client.post("/api/v1/nodes", json={
        "node_id": node_id,
        "name": "Highwall Bench Sector C",
        "latitude": 23.7545,
        "longitude": 86.4220,
        "elevation_m": 182.0,
        "node_type": "extensometer",
        "installation_location": "Colliery Sector 4"
    })
    assert reg_res.status_code == 201

    # 3. Submit initial baseline observation
    t0 = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    res_t0 = client.post("/api/v1/telemetry", json={
        "event_id": str(uuid.uuid4()),
        "node_id": node_id,
        "sequence_number": 1,
        "timestamp": t0.isoformat(),
        "displacement_mm": 2.0,
        "tilt_x_deg": 0.2,
        "tilt_y_deg": 0.1,
        "vibration_rms_ms2": 0.3,
        "temperature_c": 27.5,
        "battery_pct": 98.0
    })
    assert res_t0.status_code == 201
    assert res_t0.json()["displacement_mm"] == 2.0

    # 4. Submit rapid accelerating displacement 1 hour later
    # Moves from 2.0mm to 20.0mm in 1 hr -> velocity = 18.0 mm/hr (> 5.0 mm/hr critical threshold)
    t1 = t0 + timedelta(hours=1)
    res_t1 = client.post("/api/v1/telemetry", json={
        "event_id": str(uuid.uuid4()),
        "node_id": node_id,
        "sequence_number": 2,
        "timestamp": t1.isoformat(),
        "displacement_mm": 20.0,
        "tilt_x_deg": 2.5,
        "tilt_y_deg": 1.5,
        "vibration_rms_ms2": 1.2,
        "temperature_c": 28.0,
        "battery_pct": 97.0
    })
    assert res_t1.status_code == 201
    rec1 = res_t1.json()
    assert rec1["velocity_mm_hr"] == 18.0

    # 5. Verify alert generated for this node
    alerts_res = client.get(f"/api/v1/alerts?node_id={node_id}&status=ACTIVE")
    assert alerts_res.status_code == 200
    alert_items = alerts_res.json()["items"]
    assert len(alert_items) >= 1
    target_alert = alert_items[0]
    alert_id = target_alert["alert_id"]
    assert target_alert["severity"] in ["CRITICAL", "WARNING"]

    # 6. Acknowledge alert
    ack_res = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={
        "acknowledged_by": "Safety Engineer Banerjee",
        "note": "Field sirens triggered; mining machinery cleared from bench toe"
    })
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # 7. Resolve alert
    resolve_res = client.post(f"/api/v1/alerts/{alert_id}/resolve", json={
        "resolved_by": "Senior Geotechnical Officer Banerjee",
        "resolution_notes": "Tension crack backfilled and berm re-profiled. Slope movement arrested."
    })
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"

    # 8. Verify PDF Dossier and CSV reports export
    csv_res = client.get(f"/api/v1/reports/export?format=csv&node_id={node_id}")
    assert csv_res.status_code == 200
    assert "20.000" in csv_res.text

    pdf_res = client.get("/api/v1/reports/export?format=pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.content.startswith(b"%PDF")
