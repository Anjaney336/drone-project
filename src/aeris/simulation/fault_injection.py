from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

BASE_GNSS_SIGMA_M = 1.5
GNSS_DRIFT_RATE_MPS = np.array([2.5, -0.8, 0.0])
GNSS_BIAS_M = np.array([8.0, -4.0, 2.0])
SENSOR_DISAGREEMENT_M = np.array([10.0, -6.0, 2.0])
IMU_BIAS_JUMP_MPS2 = np.array([0.8, -0.4, 0.2])
COMMUNICATION_LATENCY_BASE_S = 0.4


class FaultSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


SEVERITY_SCALE = {
    FaultSeverity.LOW: 0.5,
    FaultSeverity.MEDIUM: 1.0,
    FaultSeverity.HIGH: 1.75,
    FaultSeverity.EXTREME: 3.0,
}


@dataclass(frozen=True, slots=True)
class FaultSpec:
    fault_type: str
    severity: FaultSeverity = FaultSeverity.HIGH
    start_time_s: float = 2.0
    duration_s: float = 5.0
    affected_sensor: str = "gnss"

    def active(self, timestamp: float) -> bool:
        return self.start_time_s <= timestamp < self.start_time_s + self.duration_s


@dataclass(frozen=True, slots=True)
class FaultResult:
    measurement: np.ndarray | None
    packet_delay_s: float
    packet_loss: bool
    label: str | None
    active: bool


def inject_gnss_fault(
    position: np.ndarray,
    timestamp: float,
    spec: FaultSpec | None,
    rng: np.random.Generator,
) -> FaultResult:
    measurement = position + rng.normal(0.0, BASE_GNSS_SIGMA_M, 3)
    if spec is None or not spec.active(timestamp) or spec.affected_sensor not in {"gnss", "all"}:
        return FaultResult(measurement, 0.0, False, None, False)
    scale = SEVERITY_SCALE[spec.severity]
    elapsed = timestamp - spec.start_time_s
    label = f"synthetic_{spec.fault_type}_{spec.severity.value}"
    delay = 0.0
    lost = False
    if spec.fault_type == "gnss_drift":
        measurement += GNSS_DRIFT_RATE_MPS * scale * elapsed
    elif spec.fault_type == "gnss_bias":
        measurement += GNSS_BIAS_M * scale
    elif spec.fault_type == "gnss_dropout":
        measurement = None
    elif spec.fault_type == "packet_loss":
        lost = bool(rng.random() < min(0.15 * scale + 0.1, 0.95))
        measurement = None if lost else measurement
        label = label if lost else None
    elif spec.fault_type in {
        "communication_latency",
        "telemetry_latency",
        "timestamp_delay",
    }:
        delay = COMMUNICATION_LATENCY_BASE_S * scale
    elif spec.fault_type in {"sensor_disagreement", "combined_degradation"}:
        measurement += SENSOR_DISAGREEMENT_M * scale
        if spec.fault_type == "combined_degradation":
            delay = 0.2 * scale
            lost = bool(rng.random() < min(0.15 * scale, 0.9))
            measurement = None if lost else measurement
    return FaultResult(measurement, delay, lost, label, True)
