def test_audit_events_endpoint(client):
    res = client.get("/api/v1/audit-events?skip=0&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)

    # Filter by category
    cat_res = client.get("/api/v1/audit-events?category=NODE_MANAGEMENT")
    assert cat_res.status_code == 200
    assert cat_res.json()["total"] >= 0

