import numpy as np

from aeris.autonomy.prediction import ConstantVelocityPredictor
from aeris.autonomy.safety import Geofence, SafetyEngine
from aeris.models import AnomalyEvent, SafetyAction, SafetyState, StateEstimate


def test_geofence_risk_produces_explainable_reroute():
    estimate = StateEstimate(
        0, np.array([9.0, 0, 1]), np.array([2.0, 0, 0]), np.eye(6), None, None, True, {}
    )
    prediction = ConstantVelocityPredictor().predict(estimate, 2, 1)
    decision = SafetyEngine().decide(prediction, [], 6.0, Geofence((-10, -10, 0), (10, 10, 10)))
    assert decision.state is SafetyState.GEOFENCE_RISK
    assert decision.action is SafetyAction.REROUTE
    assert 0 <= decision.risk["total"] <= 1


def test_state_machine_enters_recovery_after_anomaly_clears():
    estimate = StateEstimate(0, np.zeros(3), np.zeros(3), np.eye(6), None, None, True, {})
    prediction = ConstantVelocityPredictor().predict(estimate, 1, 1)
    engine = SafetyEngine()
    event = AnomalyEvent("dropout", 0.8, "gnss", "critical", 0.0, {})
    assert engine.decide(prediction, [event], 6).state is SafetyState.ANOMALY_DETECTED
    assert engine.decide(prediction, [], 6).state is SafetyState.RECOVERY
