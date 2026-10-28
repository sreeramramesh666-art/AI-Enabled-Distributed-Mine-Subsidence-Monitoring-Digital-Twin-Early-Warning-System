import uuid
from datetime import datetime, timezone, timedelta


def test_alert_lifecycle(client):
    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": ts,
        "displacement_mm": 35.0  # > 30.0 mm critical threshold
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 201

    # Verify alert exists
    alerts_res = client.get("/api/v1/alerts?status=ACTIVE&severity=CRITICAL")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert alerts_data["total"] >= 1
    alert = alerts_data["items"][0]
    alert_id = alert["alert_id"]
    assert alert["severity"] == "CRITICAL"
    assert alert["category"] == "DISPLACEMENT"

    # Get single alert by ID
    get_res = client.get(f"/api/v1/alerts/{alert_id}")
    assert get_res.status_code == 200
    assert get_res.json()["alert_id"] == alert_id

    # Acknowledge alert
    ack_res = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={
        "acknowledged_by": "Safety Officer Rao",
        "note": "Field sirens verified"
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

    # Attempting to acknowledge a resolved alert returns 400 Bad Request
    re_ack = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={
        "acknowledged_by": "Operator",
        "note": "Too late"
    })
    assert re_ack.status_code == 400

    # Reopen resolved alert
    reopen_res = client.post(f"/api/v1/alerts/{alert_id}/reopen", json={
        "reopened_by": "Geotechnical Engineer Sharma",
        "reopen_notes": "Post-stabilization crack widening detected again"
    })
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "REOPENED"
    assert reopen_res.json()["reopened_by"] == "Geotechnical Engineer Sharma"

    # Investigate reopened alert
    inv_res = client.post(f"/api/v1/alerts/{alert_id}/investigate", json={
        "investigated_by": "Inspector Patel",
        "investigation_notes": "Dispatched survey crew to install manual dial gauge"
    })
    assert inv_res.status_code == 200
    assert inv_res.json()["status"] == "UNDER_INVESTIGATION"
    assert inv_res.json()["investigated_by"] == "Inspector Patel"
    assert len(inv_res.json()["lifecycle_history"]) >= 4


def test_alert_404_cases(client):
    assert client.get("/api/v1/alerts/NON-EXISTENT-ALERT").status_code == 404
    assert client.post("/api/v1/alerts/NON-EXISTENT-ALERT/acknowledge", json={"acknowledged_by": "Admin"}).status_code == 404
    assert client.post("/api/v1/alerts/NON-EXISTENT-ALERT/resolve", json={"resolved_by": "Admin", "resolution_notes": "Done"}).status_code == 404


def test_alert_filtering_by_category_and_time(client):
    now = datetime.now(timezone.utc)
    res = client.get(
        f"/api/v1/alerts?category=DISPLACEMENT&start_time={(now - timedelta(days=1)).isoformat()}&end_time={now.isoformat()}"
    )
    assert res.status_code == 200
    assert isinstance(res.json()["items"], list)
