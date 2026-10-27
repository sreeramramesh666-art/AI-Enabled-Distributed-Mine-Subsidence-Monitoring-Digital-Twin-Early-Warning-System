def test_create_and_get_node(client):
    node_payload = {
        "node_id": "NODE-BENCH-99",
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
    assert created["node_id"] == "NODE-BENCH-99"
    assert created["connectivity_status"] == "OFFLINE"

    # Get node
    get_res = client.get("/api/v1/nodes/NODE-BENCH-99")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Catch Bench Inclinometer"

    # Update node
    patch_res = client.patch("/api/v1/nodes/NODE-BENCH-99", json={"name": "Updated Bench Inclinometer"})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Updated Bench Inclinometer"


def test_invalid_node_id_rejected(client):
    invalid_payload = {
        "node_id": "INVALID NODE $#@!",
        "name": "Bad Node",
        "latitude": 23.0,
        "longitude": 86.0
    }
    response = client.post("/api/v1/nodes", json=invalid_payload)
    assert response.status_code == 422
