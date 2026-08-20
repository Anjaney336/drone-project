from __future__ import annotations

import numpy as np

from aeris.models import StateEstimate, TrajectoryPrediction


class ConstantVelocityPredictor:
    def predict(
        self, estimate: StateEstimate, horizon_s: float = 5.0, step_s: float = 1.0
    ) -> TrajectoryPrediction:
        times = np.arange(step_s, horizon_s + 1e-9, step_s)
        positions = [list(estimate.position + estimate.velocity * dt) for dt in times]
        traces = [
            float(
                np.trace(estimate.covariance[:3, :3]) + dt * np.trace(estimate.covariance[3:, 3:])
            )
            for dt in times
        ]
        return TrajectoryPrediction("constant_velocity", list(map(float, times)), positions, traces)
