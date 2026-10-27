import uuid
from datetime import datetime, timezone


def test_alert_lifecycle(client):
    # Submit telemetry that breaches critical displacement threshold
    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": ts,
        "displacement_mm": 35.0  # > 30.0 mm
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 201

    # Verify alert was generated
    alerts_res = client.get("/api/v1/alerts?status=ACTIVE")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert alerts_data["total"] >= 1
    alert = alerts_data["items"][0]
    alert_id = alert["alert_id"]
    assert alert["severity"] in ["CRITICAL", "WARNING"]

    # Acknowledge alert
    ack_res = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={
        "acknowledged_by": "Safety Officer Rao",
        "note": "Field team alerted"
    })
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"
    assert ack_res.json()["acknowledged_by"] == "Safety Officer Rao"

    # Resolve alert
    resolve_res = client.post(f"/api/v1/alerts/{alert_id}/resolve", json={
        "resolved_by": "Safety Officer Rao",
        "resolution_notes": "Slope stabilized with rock bolts"
    })
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"
