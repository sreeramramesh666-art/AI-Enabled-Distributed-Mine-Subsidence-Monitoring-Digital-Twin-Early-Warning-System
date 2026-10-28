import uuid
from datetime import datetime, timezone, timedelta


def test_create_and_get_node(client):
    node_id = f"NODE-{uuid.uuid4().hex[:6]}"
    node_payload = {
        "node_id": node_id,
        "name": "Catch Bench Inclinometer",
        "latitude": 23.7580,
        "longitude": 86.4250,
        "elevation_m": 195.5,
        "node_type": "inclinometer",
        "installation_location": "Bench Section 3",
        "firmware_version": "v1.1.0",
        "is_enabled": True
    }
    response = client.post("/api/v1/nodes", json=node_payload)
    assert response.status_code == 201
    created = response.json()
    assert created["node_id"] == node_id
    assert created["connectivity_status"] == "OFFLINE"

    # Duplicate creation returns 409 Conflict
    dup_res = client.post("/api/v1/nodes", json=node_payload)
    assert dup_res.status_code == 409

    # Get node
    get_res = client.get(f"/api/v1/nodes/{node_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Catch Bench Inclinometer"

    # Update node
    patch_res = client.patch(f"/api/v1/nodes/{node_id}", json={"name": "Updated Bench Inclinometer", "elevation_m": 198.0})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Updated Bench Inclinometer"
    assert patch_res.json()["elevation_m"] == 198.0


def test_get_nonexistent_node_404(client):
    res = client.get("/api/v1/nodes/DOES-NOT-EXIST")
    assert res.status_code == 404


def test_update_nonexistent_node_404(client):
    res = client.patch("/api/v1/nodes/DOES-NOT-EXIST", json={"name": "Ghost"})
    assert res.status_code == 404


def test_invalid_node_id_rejected(client):
    invalid_payload = {
        "node_id": "INVALID NODE $#@!",
        "name": "Bad Node",
        "latitude": 23.0,
        "longitude": 86.0
    }
    response = client.post("/api/v1/nodes", json=invalid_payload)
    assert response.status_code == 422


def test_list_nodes_filtering_and_pagination(client):
    res = client.get("/api/v1/nodes?skip=0&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)

    # Search filter
    search_res = client.get("/api/v1/nodes?search=Highwall")
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1


def test_delete_node_lifecycle(client):
    node_id = f"DEL-NODE-{uuid.uuid4().hex[:6]}"
    client.post("/api/v1/nodes", json={
        "node_id": node_id,
        "name": "Deletable Sensor",
        "latitude": 23.75,
        "longitude": 86.42
    })

    # Soft delete (disable)
    disable_res = client.delete(f"/api/v1/nodes/{node_id}?hard_delete=false")
    assert disable_res.status_code == 200
    node_info = client.get(f"/api/v1/nodes/{node_id}").json()
    assert node_info["is_enabled"] is False

    # Hard delete (permanent)
    del_res = client.delete(f"/api/v1/nodes/{node_id}?hard_delete=true")
    assert del_res.status_code == 200

    # Nonexistent now
    assert client.get(f"/api/v1/nodes/{node_id}").status_code == 404

    # Delete nonexistent returns 404
    assert client.delete(f"/api/v1/nodes/{node_id}").status_code == 404


def test_node_baseline_endpoints(client):
    # Baseline for TEST-NODE-01 exists
    res = client.get("/api/v1/nodes/TEST-NODE-01/baseline")
    assert res.status_code == 200
    assert res.json()["node_id"] == "TEST-NODE-01"

    # Baseline for unknown node returns 404
    assert client.get("/api/v1/nodes/UNKNOWN-NODE/baseline").status_code == 404

    # Recalculate baseline
    recalc_res = client.post("/api/v1/nodes/TEST-NODE-01/baseline/recalculate", json={"period_hours": 48})
    assert recalc_res.status_code == 200
    assert recalc_res.json()["node_id"] == "TEST-NODE-01"


def test_node_telemetry_time_filtering(client):
    now = datetime.now(timezone.utc)
    t_start = (now - timedelta(hours=2)).isoformat()
    t_end = now.isoformat()

    # Valid time range query
    res = client.get(f"/api/v1/nodes/TEST-NODE-01/telemetry?start_time={t_start}&end_time={t_end}")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Invalid time range query (start > end)
    inv_res = client.get(f"/api/v1/nodes/TEST-NODE-01/telemetry?start_time={t_end}&end_time={t_start}")
    assert inv_res.status_code == 400
    assert "start_time must be earlier" in inv_res.json()["detail"]
