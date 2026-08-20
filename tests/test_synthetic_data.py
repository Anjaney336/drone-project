import numpy as np

from aeris.data.synthetic import SyntheticConfig, generate


def test_synthetic_generator_is_reproducible_and_provenance_is_complete():
    config = SyntheticConfig(seed=4, split="held_out", duration_s=10)
    first, second = generate(config), generate(config)
    assert np.array_equal(first["imu_accel_mps2"], second["imu_accel_mps2"])
    assert set(first["origin"]) <= {"synthetic", "synthetic_fault"}


def test_synthetic_trajectory_respects_documented_speed_limit():
    data = generate(SyntheticConfig(seed=5, split="tuning", duration_s=30))
    assert np.max(np.linalg.norm(data["velocity_mps"][:, :2], axis=1)) <= 16.0 + 1e-9
