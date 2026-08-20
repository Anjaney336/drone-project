from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aeris.autonomy.safety.risk import RiskWeights, combine_risk
from aeris.models import (
    AnomalyEvent,
    SafetyAction,
    SafetyDecision,
    SafetyState,
    TrajectoryPrediction,
)


@dataclass(frozen=True, slots=True)
class Geofence:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    def contains(self, point: list[float]) -> bool:
        return all(
            low <= value <= high
            for value, low, high in zip(point, self.minimum, self.maximum, strict=True)
        )


class SafetyEngine:
    """Deterministic recommendation policy with an auditable risk decomposition."""

    def __init__(self, weights: RiskWeights | None = None) -> None:
        self.weights = weights or RiskWeights()
        self._last_state = SafetyState.NORMAL
        self._healthy_steps = 0

    def decide(
        self,
        prediction: TrajectoryPrediction,
        anomalies: list[AnomalyEvent],
        covariance_trace: float,
        geofence: Geofence | None = None,
        monitored_positions: list[list[float]] | None = None,
        minimum_separation_m: float = 10.0,
        minimum_sensor_trust: float = 1.0,
        packet_delay_s: float = 0.0,
    ) -> SafetyDecision:
        minimum_distance = float("inf")
        if monitored_positions:
            minimum_distance = min(
                float(np.linalg.norm(np.asarray(own) - np.asarray(other)))
                for own, other in zip(prediction.positions, monitored_positions, strict=False)
            )
        violation = bool(
            geofence and any(not geofence.contains(point) for point in prediction.positions)
        )
        components = {
            "collision": 0.0
            if not np.isfinite(minimum_distance)
            else max(0.0, min(1.0, 1.0 - minimum_distance / minimum_separation_m)),
            "geofence": float(violation),
            "uncertainty": min(1.0, covariance_trace / 100.0),
            "sensor_degradation": 1.0 - min(1.0, max(0.0, minimum_sensor_trust)),
            "communication": min(1.0, packet_delay_s),
        }
        risk = combine_risk(components, self.weights)
        evidence = {
            "minimum_predicted_separation_m": (
                minimum_distance if np.isfinite(minimum_distance) else None
            ),
            "covariance_trace": covariance_trace,
            "minimum_sensor_trust": minimum_sensor_trust,
            "packet_delay_s": packet_delay_s,
            "anomalies": [event.anomaly_type for event in anomalies],
        }
        if components["collision"] > 0:
            return self._remember(
                SafetyDecision(
                    SafetyState.COLLISION_RISK,
                    SafetyAction.REROUTE,
                    "Predicted separation is below the configured minimum.",
                    evidence,
                    risk,
                )
            )
        if violation:
            return self._remember(
                SafetyDecision(
                    SafetyState.GEOFENCE_RISK,
                    SafetyAction.REROUTE,
                    "Predicted trajectory exits the permitted geofence.",
                    evidence,
                    risk,
                )
            )
        if anomalies:
            action = (
                SafetyAction.RETURN_HOME
                if any(event.severity == "critical" for event in anomalies)
                else SafetyAction.HOLD
            )
            return self._remember(
                SafetyDecision(
                    SafetyState.ANOMALY_DETECTED,
                    action,
                    "Sensor-health monitor reported anomalous evidence.",
                    evidence,
                    risk,
                )
            )
        if covariance_trace > 100.0 or minimum_sensor_trust < 0.25:
            return self._remember(
                SafetyDecision(
                    SafetyState.DEGRADED,
                    SafetyAction.HOLD,
                    "Navigation confidence is below the configured safety bound.",
                    evidence,
                    risk,
                )
            )
        if self._last_state not in {SafetyState.NORMAL, SafetyState.RECOVERY}:
            self._last_state = SafetyState.RECOVERY
            self._healthy_steps = 1
            return SafetyDecision(
                SafetyState.RECOVERY,
                SafetyAction.HOLD,
                "Hazard evidence cleared; stability is being confirmed.",
                evidence,
                risk,
            )
        if self._last_state is SafetyState.RECOVERY and self._healthy_steps < 5:
            self._healthy_steps += 1
            return SafetyDecision(
                SafetyState.RECOVERY,
                SafetyAction.HOLD,
                "Recovery dwell time has not yet elapsed.",
                evidence,
                risk,
            )
        self._last_state = SafetyState.NORMAL
        self._healthy_steps = 0
        return SafetyDecision(
            SafetyState.NORMAL,
            SafetyAction.CONTINUE,
            "No configured safety boundary is violated.",
            evidence,
            risk,
        )

    def _remember(self, decision: SafetyDecision) -> SafetyDecision:
        self._last_state = decision.state
        self._healthy_steps = 0
        return decision
