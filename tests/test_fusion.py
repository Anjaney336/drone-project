import numpy as np

from aeris.autonomy.fusion import ConstantVelocityEKF


def test_prediction_and_update_expose_innovation_and_nis():
    ekf = ConstantVelocityEKF()
    ekf.initialize(np.zeros(3), np.array([1.0, 0.0, 0.0]))
    predicted = ekf.predict(1.0)
    assert np.allclose(predicted.position, [1.0, 0.0, 0.0])
    result = ekf.update_position(np.array([1.1, 0.0, 0.0]), np.eye(3), "gnss")
    assert result.accepted
    assert result.nis >= 0
    assert result.innovation.shape == (3,)


def test_outlier_is_soft_weighted_and_reduces_trust():
    ekf = ConstantVelocityEKF()
    ekf.initialize(np.zeros(3))
    ekf.predict(1.0)
    result = ekf.update_position(np.full(3, 1000.0), np.eye(3), "gnss")
    assert not result.accepted
    assert result.applied
    assert result.effective_noise_scale > 1.0
    assert result.sensor_trust < 1.0


def test_hard_rejection_is_a_distinct_comparator():
    ekf = ConstantVelocityEKF(update_policy="hard")
    ekf.initialize(np.zeros(3))
    before = ekf.x.copy()
    result = ekf.update_position(np.full(3, 1000.0), np.eye(3), "gnss")
    assert not result.applied
    assert np.allclose(ekf.x, before)
