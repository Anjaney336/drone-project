from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import numpy as np


class DataOrigin(StrEnum):
    MEASURED = "measured"
    FIELD = "field"
    USER_UPLOADED = "user_uploaded"
    DEMONSTRATION = "demonstration"
    PUBLIC_BENCHMARK = "public_benchmark"
    SIMULATION = "simulation"
    SYNTHETIC = "synthetic"
    SYNTHETIC_FAULT = "synthetic_fault"


class SafetyState(StrEnum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    COLLISION_RISK = "COLLISION_RISK"
    GEOFENCE_RISK = "GEOFENCE_RISK"
    SAFE_RESPONSE = "SAFE_RESPONSE"
    RECOVERY = "RECOVERY"


class SafetyAction(StrEnum):
    CONTINUE = "CONTINUE"
    HOLD = "HOLD"
    REROUTE = "REROUTE"
    RETURN_HOME = "RETURN_HOME"
    CONTROLLED_LANDING = "CONTROLLED_LANDING"
    OPERATOR_ESCALATION = "OPERATOR_ESCALATION"


@dataclass(frozen=True, slots=True)
class Provenance:
    origin: DataOrigin
    source: str
    scenario_id: str | None = None
    fault_label: str | None = None


@dataclass(slots=True)
class Detection:
    timestamp: float
    confidence: float
    object_class: str
    bbox_xyxy: tuple[float, float, float, float]
    position: np.ndarray | None = None
    provenance: Provenance | None = None


@dataclass(slots=True)
class Track:
    track_id: str
    object_class: str
    bbox_xyxy: tuple[float, float, float, float]
    position: np.ndarray
    velocity: np.ndarray
    image_velocity_px_s: tuple[float, float]
    confidence: float
    age: int
    missed_frames: int
    timestamp: float
    history: list[np.ndarray] = field(default_factory=list)


@dataclass(slots=True)
class StateEstimate:
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    covariance: np.ndarray
    innovation: np.ndarray | None
    nis: float | None
    accepted: bool
    sensor_trust: dict[str, float]


@dataclass(frozen=True, slots=True)
class AnomalyEvent:
    anomaly_type: str
    confidence: float
    affected_sensor: str
    severity: str
    time_detected: float
    evidence: dict[str, float | str]


@dataclass(frozen=True, slots=True)
class TrajectoryPrediction:
    model: str
    times: list[float]
    positions: list[list[float]]
    covariance_trace: list[float]


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    state: SafetyState
    action: SafetyAction
    reason: str
    evidence: dict[str, Any]
    risk: dict[str, float]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
