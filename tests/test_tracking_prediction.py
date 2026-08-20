import numpy as np

from aeris.autonomy.prediction import ConstantVelocityPredictor
from aeris.autonomy.tracking import MultiObjectTracker
from aeris.models import Detection, StateEstimate


def test_tracking_velocity_and_prediction():
    tracker = MultiObjectTracker()
    first = Detection(0.0, 0.9, "drone", (0, 0, 1, 1), np.zeros(3))
    second = Detection(1.0, 0.8, "drone", (1, 0, 2, 1), np.array([2.0, 0.0, 0.0]))
    tracker.update([first], 0.0)
    track = tracker.update([second], 1.0)[0]
    assert np.allclose(track.velocity, [2.0, 0.0, 0.0])
    estimate = StateEstimate(1.0, track.position, track.velocity, np.eye(6), None, None, True, {})
    prediction = ConstantVelocityPredictor().predict(estimate, horizon_s=2, step_s=1)
    assert prediction.positions[-1] == [6.0, 0.0, 0.0]
