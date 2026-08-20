from aeris.benchmark import evaluate_variant
from aeris.simulation.runner import run_scenario
from aeris.simulation.scenarios import ScenarioConfig


def test_end_to_end_fault_scenario_has_provenance_and_measured_metrics():
    result = run_scenario(ScenarioConfig("gnss_drift", seed=4, steps=30))
    assert result["manifest"]["seed"] == 4
    assert result["manifest"]["config_hash"]
    assert any(row["origin"] == "synthetic_fault" for row in result["telemetry"])
    assert all(row["seed"] == 4 for row in result["telemetry"])
    assert result["state_snapshots"][0]["tracks"]
    assert "risk" in result["state_snapshots"][-1]["safety_decision"]
    assert result["state_snapshots"][0]["true_position_m"]
    assert result["metrics"]["position_rmse_m"] >= 0
    baseline = evaluate_variant(ScenarioConfig("nominal", seed=4, steps=30), "raw_measurements")
    assert baseline["position_rmse_m"] >= 0
