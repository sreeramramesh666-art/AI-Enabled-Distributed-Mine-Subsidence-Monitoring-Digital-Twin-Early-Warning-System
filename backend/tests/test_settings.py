def test_get_and_update_settings(client):
    # GET settings
    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    data = res.json()
    assert "displacement_warning_mm" in data
    assert "displacement_critical_mm" in data

    # Valid PATCH update
    update_payload = {
        "DISPLACEMENT_WARNING_MM": 16.0,
        "DISPLACEMENT_CRITICAL_MM": 32.0,
        "TILT_WARNING_DEG": 2.5,
        "TILT_CRITICAL_DEG": 5.5
    }
    patch_res = client.patch("/api/v1/settings", json=update_payload)
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["displacement_warning_mm"] == 16.0
    assert updated_data["displacement_critical_mm"] == 32.0


def test_invalid_settings_hierarchy_rejected(client):
    # Warning >= Critical should be rejected by Pydantic model validator with 422
    bad_payload = {
        "DISPLACEMENT_WARNING_MM": 50.0,
        "DISPLACEMENT_CRITICAL_MM": 20.0
    }
    res = client.patch("/api/v1/settings", json=bad_payload)
    assert res.status_code == 422

    bad_tilt = {
        "TILT_WARNING_DEG": 10.0,
        "TILT_CRITICAL_DEG": 5.0
    }
    assert client.patch("/api/v1/settings", json=bad_tilt).status_code == 422

