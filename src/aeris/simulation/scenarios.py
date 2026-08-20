from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np

from aeris.simulation.fault_injection import (
    IMU_BIAS_JUMP_MPS2,
    SEVERITY_SCALE,
    FaultResult,
    FaultSeverity,
    FaultSpec,
    inject_gnss_fault,
)

SCENARIO_FAULTS: dict[str, tuple[str, str] | None] = {
    "nominal": None,
    "gnss_drift": ("gnss_drift", "gnss"),
    "gnss_dropout": ("gnss_dropout", "gnss"),
    "imu_bias": ("imu_bias", "imu"),
    "camera_degradation": ("camera_blur", "camera"),
    "camera_occlusion": ("camera_dropout", "camera"),
    "packet_loss": ("packet_loss", "gnss"),
    "communication_latency": ("communication_latency", "gnss"),
    "multiple_drones": None,
    "sensor_disagreement": ("sensor_disagreement", "gnss"),
    "geofence_breach": None,
    "combined_degradation": ("combined_degradation", "all"),
}


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    scenario_id: str = "nominal"
    seed: int = 7
    steps: int = 120
    dt: float = 0.1
    severity: FaultSeverity = FaultSeverity.HIGH
    dataset_version: str = "aeris-sim-v2"
    model_version: str = "cv-ekf-v2"

    @property
    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class ScenarioSample:
    timestamp: float
    true_position: np.ndarray
    true_velocity: np.ndarray
    imu_acceleration: np.ndarray
    barometer_altitude: float
    gnss: FaultResult
    camera_frame: dict
    camera_position: np.ndarray | None
    camera_confidence: float | None
    other_position: np.ndarray | None
    other_velocity: np.ndarray | None
    fault_spec: FaultSpec | None

    @property
    def fault_active(self) -> bool:
        return bool(self.fault_spec and self.fault_spec.active(self.timestamp))

    @property
    def fault_label(self) -> str | None:
        if not self.fault_active or self.fault_spec is None:
            return None
        return f"synthetic_{self.fault_spec.fault_type}_{self.fault_spec.severity.value}"


def available_scenarios() -> list[str]:
    return list(SCENARIO_FAULTS)


def generate_scenario(config: ScenarioConfig) -> list[ScenarioSample]:
    if config.scenario_id not in SCENARIO_FAULTS:
        raise ValueError(f"Unknown scenario: {config.scenario_id}")
    rng = np.random.default_rng(config.seed)
    position = np.array([0.0, 0.0, 30.0])
    velocity = (
        np.array([15.0, 2.0, 0.0])
        if config.scenario_id == "geofence_breach"
        else np.array([8.0, 2.0, 0.0])
    )
    mapping = SCENARIO_FAULTS[config.scenario_id]
    spec = None if mapping is None else FaultSpec(mapping[0], config.severity, 2.0, 5.0, mapping[1])
    samples: list[ScenarioSample] = []
    other_position, other_velocity = np.array([60.0, -20.0, 30.0]), np.array([-5.0, 5.0, 0.0])
    for step in range(config.steps):
        timestamp = step * config.dt
        acceleration = np.array([-2.0, 3.0, 0.2]) if step == 55 else np.zeros(3)
        velocity, position = velocity + acceleration * config.dt, position + velocity * config.dt
        if config.scenario_id == "multiple_drones":
            other_position = other_position + other_velocity * config.dt
        gnss = inject_gnss_fault(position, timestamp, spec, rng)
        scale = SEVERITY_SCALE[config.severity]
        imu = acceleration + rng.normal(0.0, 0.08, 3)
        if (
            spec
            and spec.active(timestamp)
            and spec.fault_type in {"imu_bias", "combined_degradation"}
        ):
            imu += IMU_BIAS_JUMP_MPS2 * scale
        camera_position, confidence = position + rng.normal(0.0, 0.8, 3), 0.92
        if (
            spec
            and spec.active(timestamp)
            and spec.fault_type in {"camera_noise", "camera_blur", "combined_degradation"}
        ):
            camera_position, confidence = (
                position + rng.normal(0.0, 4.0 * scale, 3),
                max(0.15, 0.65 / scale),
            )
        if spec and spec.active(timestamp) and spec.fault_type == "camera_dropout":
            camera_position, confidence = None, None
        detections: list[dict] = []
        if camera_position is not None:
            cx, cy = 320.0 + camera_position[0] * 0.4, 240.0 - camera_position[1] * 0.4
            detections.append(
                {
                    "object_class": "drone",
                    "confidence": confidence,
                    "bbox_xyxy": [cx - 12, cy - 8, cx + 12, cy + 8],
                    "position_m": camera_position.tolist(),
                }
            )
        if config.scenario_id == "multiple_drones":
            observed_other = other_position + rng.normal(0, 0.8, 3)
            cx, cy = 320.0 + observed_other[0] * 0.4, 240.0 - observed_other[1] * 0.4
            detections.append(
                {
                    "object_class": "drone",
                    "confidence": 0.9,
                    "bbox_xyxy": [cx - 12, cy - 8, cx + 12, cy + 8],
                    "position_m": observed_other.tolist(),
                }
            )
        samples.append(
            ScenarioSample(
                timestamp,
                position.copy(),
                velocity.copy(),
                imu,
                float(position[2] + rng.normal(0, 0.4)),
                gnss,
                {"origin": "simulation", "detections": detections},
                camera_position,
                confidence,
                other_position.copy() if config.scenario_id == "multiple_drones" else None,
                other_velocity.copy() if config.scenario_id == "multiple_drones" else None,
                spec,
            )
        )
    return samples
