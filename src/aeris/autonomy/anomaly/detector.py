from __future__ import annotations

import numpy as np

from aeris.models import AnomalyEvent, StateEstimate


class SensorHealthMonitor:
    def __init__(self, max_speed_mps: float = 60.0, max_packet_delay_s: float = 0.5) -> None:
        self.max_speed_mps = max_speed_mps
        self.max_packet_delay_s = max_packet_delay_s

    def evaluate(
        self,
        estimate: StateEstimate,
        sensor: str,
        packet_delay_s: float | None = None,
        disagreement_m: float | None = None,
        sensor_available: bool = True,
    ) -> list[AnomalyEvent]:
        events: list[AnomalyEvent] = []
        if not sensor_available:
            events.append(
                self._event(
                    "sensor_unavailable",
                    sensor,
                    estimate.timestamp,
                    1.0,
                    {"available": 0.0},
                )
            )
        if estimate.nis is not None and not estimate.accepted:
            events.append(
                self._event(
                    "innovation_excursion",
                    sensor,
                    estimate.timestamp,
                    min(1.0, estimate.nis / 25.0),
                    {"nis": estimate.nis},
                )
            )
        speed = float(np.linalg.norm(estimate.velocity))
        if speed > self.max_speed_mps:
            events.append(
                self._event(
                    "impossible_kinematics",
                    "fusion",
                    estimate.timestamp,
                    min(1.0, speed / (2 * self.max_speed_mps)),
                    {"speed_mps": speed},
                )
            )
        if packet_delay_s is not None and packet_delay_s > self.max_packet_delay_s:
            events.append(
                self._event(
                    "packet_timing",
                    "telemetry",
                    estimate.timestamp,
                    min(1.0, packet_delay_s / 2.0),
                    {"delay_s": packet_delay_s},
                )
            )
        if disagreement_m is not None and disagreement_m > 10.0:
            events.append(
                self._event(
                    "cross_sensor_disagreement",
                    sensor,
                    estimate.timestamp,
                    min(1.0, disagreement_m / 50.0),
                    {"disagreement_m": disagreement_m},
                )
            )
        return events

    @staticmethod
    def _event(
        kind: str, sensor: str, timestamp: float, confidence: float, evidence: dict[str, float]
    ) -> AnomalyEvent:
        severity = "critical" if confidence >= 0.8 else "warning"
        return AnomalyEvent(kind, confidence, sensor, severity, timestamp, evidence)
