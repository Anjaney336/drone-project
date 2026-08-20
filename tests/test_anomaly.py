import numpy as np

from aeris.autonomy.anomaly import SensorHealthMonitor
from aeris.models import StateEstimate


def test_innovation_and_packet_timing_events_are_evidence_backed():
    estimate = StateEstimate(
        2.0, np.zeros(3), np.zeros(3), np.eye(6), np.ones(3), 20.0, False, {"gnss": 0.4}
    )
    events = SensorHealthMonitor().evaluate(estimate, "gnss", packet_delay_s=0.8)
    assert {event.anomaly_type for event in events} == {"innovation_excursion", "packet_timing"}


def test_missing_sensor_is_reported_without_using_fault_labels():
    estimate = StateEstimate(2.0, np.zeros(3), np.zeros(3), np.eye(6), None, None, True, {})
    events = SensorHealthMonitor().evaluate(estimate, "gnss", sensor_available=False)
    assert events[0].anomaly_type == "sensor_unavailable"
