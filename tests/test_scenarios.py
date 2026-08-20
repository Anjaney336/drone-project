import numpy as np

from aeris.simulation.fault_injection import FaultSeverity
from aeris.simulation.scenarios import ScenarioConfig, generate_scenario


def test_scenario_is_reproducible_and_fault_is_labelled():
    config = ScenarioConfig("gnss_drift", seed=42)
    left = generate_scenario(config)
    right = generate_scenario(config)
    assert np.allclose(left[-1].gnss.measurement, right[-1].gnss.measurement)
    active = [sample for sample in left if sample.gnss.active]
    assert active[0].gnss.label == "synthetic_gnss_drift_high"
    assert left[-1].gnss.label is None  # recovery phase
    assert config.config_hash == ScenarioConfig("gnss_drift", seed=42).config_hash


def test_multiple_drone_scenario_contains_second_vehicle_truth():
    sample = generate_scenario(ScenarioConfig("multiple_drones", steps=2))[-1]
    assert sample.other_position is not None
    assert sample.other_velocity is not None


def test_fault_severity_changes_drift_magnitude():
    low = generate_scenario(ScenarioConfig("gnss_drift", seed=4, severity=FaultSeverity.LOW))[50]
    extreme = generate_scenario(
        ScenarioConfig("gnss_drift", seed=4, severity=FaultSeverity.EXTREME)
    )[50]
    low_error = np.linalg.norm(low.gnss.measurement - low.true_position)
    extreme_error = np.linalg.norm(extreme.gnss.measurement - extreme.true_position)
    assert extreme_error > low_error
