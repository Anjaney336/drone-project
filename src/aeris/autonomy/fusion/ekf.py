from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aeris.models import StateEstimate


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    innovation: np.ndarray
    innovation_covariance: np.ndarray
    nis: float
    accepted: bool
    applied: bool
    sensor_trust: float
    effective_noise_scale: float


class ConstantVelocityEKF:
    """Six-state position/velocity filter with NIS gating and adaptive sensor trust."""

    def __init__(
        self,
        process_accel_std: float = 0.5,
        nis_threshold: float = 11.345,
        update_policy: str = "adaptive",
        trust_smoothing: float = 0.8,
        minimum_trust: float = 0.02,
    ) -> None:
        self.x = np.zeros(6)
        self.p = np.eye(6) * 100.0
        self.process_accel_std = float(process_accel_std)
        self.nis_threshold = float(nis_threshold)
        if update_policy not in {"fixed", "hard", "adaptive"}:
            raise ValueError("update_policy must be fixed, hard, or adaptive")
        self.update_policy = update_policy
        self.trust_smoothing = float(trust_smoothing)
        self.minimum_trust = float(minimum_trust)
        self.sensor_trust: dict[str, float] = {}
        self.timestamp = 0.0
        self.last_result: MeasurementResult | None = None

    def initialize(
        self, position: np.ndarray, velocity: np.ndarray | None = None, timestamp: float = 0.0
    ) -> None:
        self.x[:3] = np.asarray(position, dtype=float)
        if velocity is not None:
            self.x[3:] = np.asarray(velocity, dtype=float)
        self.p = np.eye(6)
        self.timestamp = timestamp

    def predict(self, timestamp: float, acceleration: np.ndarray | None = None) -> StateEstimate:
        dt = max(float(timestamp) - self.timestamp, 0.0)
        f = np.eye(6)
        f[:3, 3:] = np.eye(3) * dt
        g = np.vstack((np.eye(3) * (0.5 * dt * dt), np.eye(3) * dt))
        q = (self.process_accel_std**2) * (g @ g.T)
        u = np.zeros(3) if acceleration is None else np.asarray(acceleration, dtype=float)
        self.x = f @ self.x + g @ u
        self.p = f @ self.p @ f.T + q
        self.timestamp = float(timestamp)
        return self.estimate(accepted=True)

    def update_position(
        self,
        measurement: np.ndarray,
        covariance: np.ndarray,
        sensor: str,
        corroborated: bool = False,
    ) -> MeasurementResult:
        z = np.asarray(measurement, dtype=float).reshape(3)
        r = np.asarray(covariance, dtype=float).reshape(3, 3)
        h = np.zeros((3, 6))
        h[:, :3] = np.eye(3)
        innovation = z - h @ self.x
        s = h @ self.p @ h.T + r
        nis = float(innovation.T @ np.linalg.solve(s, innovation))
        accepted = nis <= self.nis_threshold
        previous = self.sensor_trust.get(sensor, 1.0)
        normalized_nis = nis / 3.0
        instantaneous_trust = float(np.exp(-0.5 * max(0.0, normalized_nis - 1.0)))
        if corroborated:
            instantaneous_trust = max(instantaneous_trust, 0.8)
        blended_trust = (
            self.trust_smoothing * previous + (1.0 - self.trust_smoothing) * instantaneous_trust
        )
        # Contradictory evidence degrades immediately; recovery is deliberately gradual.
        trust = float(
            np.clip(
                min(blended_trust, instantaneous_trust)
                if instantaneous_trust < previous
                else blended_trust,
                self.minimum_trust,
                1.0,
            )
        )
        self.sensor_trust[sensor] = trust
        applied = self.update_policy != "hard" or accepted
        noise_scale = (
            1.0 / max(trust, self.minimum_trust) ** 2 if self.update_policy == "adaptive" else 1.0
        )
        if applied:
            effective_r = r * noise_scale
            s = h @ self.p @ h.T + effective_r
            k = self.p @ h.T @ np.linalg.inv(s)
            self.x = self.x + k @ innovation
            identity = np.eye(6)
            self.p = (identity - k @ h) @ self.p @ (identity - k @ h).T + k @ effective_r @ k.T
        self.last_result = MeasurementResult(
            innovation, s, nis, accepted, applied, trust, noise_scale
        )
        return self.last_result

    def estimate(self, accepted: bool | None = None) -> StateEstimate:
        result = self.last_result
        return StateEstimate(
            timestamp=self.timestamp,
            position=self.x[:3].copy(),
            velocity=self.x[3:].copy(),
            covariance=self.p.copy(),
            innovation=None if result is None else result.innovation.copy(),
            nis=None if result is None else result.nis,
            accepted=(result.accepted if result else True) if accepted is None else accepted,
            sensor_trust=dict(self.sensor_trust),
        )
