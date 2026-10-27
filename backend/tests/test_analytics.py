from backend.app.analytics.anomaly_detection import MultivariateAnomalyDetector


def test_analytics_endpoints(client):
    res_summary = client.get("/api/v1/analytics/summary")
    assert res_summary.status_code == 200
    assert "overall_risk_category" in res_summary.json()

    res_health = client.get("/api/v1/analytics/node-health")
    assert res_health.status_code == 200
    assert isinstance(res_health.json(), list)

    res_trends = client.get("/api/v1/analytics/trends?node_id=TEST-NODE-01&hours=24")
    assert res_trends.status_code == 200
    assert res_trends.json()["node_id"] == "TEST-NODE-01"


def test_multivariate_anomaly_detector():
    import random
    rng = random.Random(42)
    detector = MultivariateAnomalyDetector()
    # Create 35 baseline samples with realistic slight physical noise
    samples = [
        {
            "displacement_mm": 0.1 + rng.gauss(0, 0.02),
            "tilt_x_deg": 0.05 + rng.gauss(0, 0.01),
            "tilt_y_deg": -0.02 + rng.gauss(0, 0.01),
            "velocity_mm_hr": 0.01 + rng.gauss(0, 0.005),
            "vibration_rms_ms2": 0.2 + rng.gauss(0, 0.02),
            "temperature_c": 28.0 + rng.gauss(0, 0.2)
        }
        for _ in range(35)
    ]
    trained = detector.fit_baseline(samples)
    assert trained is True
    assert detector.is_trained is True

    # Test extreme outlier
    outlier = {
        "displacement_mm": 50.0,
        "tilt_x_deg": 12.0,
        "tilt_y_deg": -10.0,
        "velocity_mm_hr": 15.0,
        "vibration_rms_ms2": 25.0,
        "temperature_c": 45.0
    }
    is_anomaly, score, factor = detector.predict(outlier)
    assert is_anomaly is True
    assert factor is not None
