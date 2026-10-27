from backend.app.simulator.scenarios import ScenarioGenerator


def test_deterministic_scenario_generator():
    gen1 = ScenarioGenerator(seed=42)
    obs1 = [gen1.next_observation(0, 4, "accelerating_subsidence") for _ in range(5)]

    gen2 = ScenarioGenerator(seed=42)
    obs2 = [gen2.next_observation(0, 4, "accelerating_subsidence") for _ in range(5)]

    # Exactly identical due to fixed seed
    for o1, o2 in zip(obs1, obs2):
        assert o1["displacement_mm"] == o2["displacement_mm"]
        assert o1["temperature_c"] == o2["temperature_c"]


def test_simulator_api_controls(client):
    status_res = client.get("/api/v1/simulator/status")
    assert status_res.status_code == 200
    assert "is_running" in status_res.json()

    # Start
    start_res = client.post("/api/v1/simulator/start", json={
        "scenario": "baseline",
        "interval_sec": 1.0,
        "node_count": 2,
        "seed": 100
    })
    assert start_res.status_code == 200
    assert start_res.json()["is_running"] is True

    # Stop
    stop_res = client.post("/api/v1/simulator/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["is_running"] is False
