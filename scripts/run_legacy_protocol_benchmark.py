"""Reproduce the retired AERIS v1 unequal-stream benchmark.

This script is deliberately isolated from ``aeris.benchmark``. It exists only to preserve the
methodological audit trail and must never be used for current performance reporting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aeris.models import utc_now


@dataclass(frozen=True)
class LegacySample:
    timestamp: float
    truth_position: np.ndarray
    truth_velocity: np.ndarray
    gnss: np.ndarray
    camera: np.ndarray


class LegacyV1Filter:
    """Frozen copy of the v1 six-state update and hard NIS-gate behavior."""

    def __init__(self, *, threshold: float, adaptive_trust: bool) -> None:
        self.x = np.zeros(6)
        self.p = np.eye(6)
        self.timestamp = 0.0
        self.threshold = threshold
        self.adaptive_trust = adaptive_trust
        self.trust: dict[str, float] = {}

    def initialize(self, position: np.ndarray, velocity: np.ndarray, timestamp: float) -> None:
        self.x[:3] = position
        self.x[3:] = velocity
        self.timestamp = timestamp

    def predict(self, timestamp: float) -> None:
        dt = max(timestamp - self.timestamp, 0.0)
        transition = np.eye(6)
        transition[:3, 3:] = np.eye(3) * dt
        control = np.vstack((np.eye(3) * 0.5 * dt**2, np.eye(3) * dt))
        self.x = transition @ self.x
        self.p = transition @ self.p @ transition.T + 0.5**2 * (control @ control.T)
        self.timestamp = timestamp

    def update(self, value: np.ndarray, covariance: np.ndarray, sensor: str) -> None:
        observation = np.zeros((3, 6))
        observation[:, :3] = np.eye(3)
        innovation = value - observation @ self.x
        residual_covariance = observation @ self.p @ observation.T + covariance
        nis = float(innovation.T @ np.linalg.solve(residual_covariance, innovation))
        accepted = nis <= self.threshold
        previous = self.trust.get(sensor, 1.0)
        trust = max(0.05, 0.8 * previous) if not accepted else min(1.0, previous + 0.05)
        self.trust[sensor] = trust
        if not accepted:
            return
        effective_covariance = covariance / trust if self.adaptive_trust else covariance
        residual_covariance = observation @ self.p @ observation.T + effective_covariance
        gain = self.p @ observation.T @ np.linalg.inv(residual_covariance)
        self.x = self.x + gain @ innovation
        identity = np.eye(6)
        self.p = (identity - gain @ observation) @ self.p @ (identity - gain @ observation).T
        self.p += gain @ effective_covariance @ gain.T


def generate_legacy_v1_stream(
    seed: int = 7, steps: int = 80, dt: float = 0.1
) -> list[LegacySample]:
    """Frozen v1 order: GNSS noise/fault draw occurs before the camera-noise draw."""
    rng = np.random.default_rng(seed)
    position = np.array([0.0, 0.0, 30.0])
    velocity = np.array([8.0, 2.0, 0.0])
    samples = []
    for step in range(steps):
        timestamp = step * dt
        position = position + velocity * dt
        gnss = position + rng.normal(0.0, 1.5, 3)
        if step >= 20:
            gnss = gnss + np.array([2.0 * (step - 19) * dt, 0.0, 0.0])
        camera = position + rng.normal(0.0, 0.8, 3)
        samples.append(LegacySample(timestamp, position.copy(), velocity.copy(), gnss, camera))
    return samples


def stream_digest(samples: list[LegacySample]) -> str:
    digest = hashlib.sha256()
    for sample in samples:
        digest.update(np.float64(sample.timestamp).tobytes())
        digest.update(sample.truth_position.astype(np.float64).tobytes())
        digest.update(sample.truth_velocity.astype(np.float64).tobytes())
        digest.update(sample.gnss.astype(np.float64).tobytes())
        digest.update(sample.camera.astype(np.float64).tobytes())
    return digest.hexdigest()


def evaluate_legacy_protocol(seed: int = 7) -> dict:
    samples = generate_legacy_v1_stream(seed)
    outputs: dict[str, float] = {}
    raw_errors = [np.linalg.norm(sample.gnss - sample.truth_position) for sample in samples]
    outputs["raw_gnss_only"] = float(np.sqrt(np.mean(np.square(raw_errors))))
    for name, threshold, adaptive, receives_camera in (
        ("fixed_ekf_gnss_only", 1e12, False, False),
        ("adaptive_camera_plus_gnss", 11.345, True, True),
    ):
        estimator = LegacyV1Filter(threshold=threshold, adaptive_trust=adaptive)
        estimator.initialize(
            samples[0].truth_position, samples[0].truth_velocity, samples[0].timestamp
        )
        errors = []
        for sample in samples:
            estimator.predict(sample.timestamp)
            if receives_camera:
                estimator.update(sample.camera, np.eye(3) * 0.64, "camera")
            estimator.update(sample.gnss, np.eye(3) * 2.25, "gnss")
            errors.append(np.linalg.norm(estimator.x[:3] - sample.truth_position))
        outputs[name] = float(np.sqrt(np.mean(np.square(errors))))
    return {
        "schema_version": "aeris-legacy-protocol-v1",
        "protocol_status": "NON_EQUAL_STREAM_RETAINED_FOR_TRANSPARENCY_ONLY",
        "reported_result": False,
        "scenario": "gnss_drift",
        "seed": seed,
        "steps": 80,
        "dt_s": 0.1,
        "sensor_access": {
            "raw_gnss_only": ["gnss"],
            "fixed_ekf_gnss_only": ["gnss"],
            "adaptive_camera_plus_gnss": ["camera", "gnss"],
        },
        "sensor_stream_sha256": stream_digest(samples),
        "reproduced_position_rmse_m": outputs,
        "historical_pitch_values_m": {
            "raw_gnss_only": 6.55,
            "fixed_ekf_gnss_only": 5.81,
            "adaptive_camera_plus_gnss": 0.49,
        },
        "generated_at": utc_now(),
        "warning": (
            "This protocol gives the adaptive method an additional camera stream. It does not "
            "measure fusion quality under equal information and must not be merged with the "
            "current benchmark."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/legacy_protocol_benchmark.json")
    )
    args = parser.parse_args()
    report = evaluate_legacy_protocol(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["reproduced_position_rmse_m"], indent=2))


if __name__ == "__main__":
    main()
