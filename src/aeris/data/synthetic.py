"""Traceable detector-output and navigation-sensor synthetic data.

This module never creates imagery. Parameters without a direct published numerical basis are
tagged ``engineering_estimate`` in :data:`PARAMETER_LINEAGE` and the generated manifest.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from aeris.models import DataOrigin
from aeris.simulation.fault_injection import (
    COMMUNICATION_LATENCY_BASE_S,
    GNSS_DRIFT_RATE_MPS,
    IMU_BIAS_JUMP_MPS2,
    SEVERITY_SCALE,
    FaultSeverity,
)

G = 9.80665
GENERATOR_VERSION = "aeris-synthetic-v1"
CITATIONS = {
    "airframe": "https://www.dji.com/mini-4-pro/specs",
    "imu": "https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088/",
    "gnss_standard": "https://www.gps.gov/technical/ps/2020-SPS-performance-standard.pdf",
    "urban_multipath": "https://doi.org/10.3390/s18041149",
    "vision": "https://doi.org/10.3390/rs18091394",
    "visdrone": "https://arxiv.org/abs/1804.07437",
}
PARAMETER_LINEAGE = {
    "max_horizontal_speed_mps": {"value": 16.0, "origin": "DJI specification"},
    "max_vertical_speed_mps": {"value": 5.0, "origin": "DJI specification"},
    "accel_noise_density_ug_sqrt_hz": {"value": 175.0, "origin": "BMI088 specification"},
    "gyro_noise_density_dps_sqrt_hz": {"value": 0.014, "origin": "BMI088 specification"},
    "imu_bias_stationary_sigma_mps2": {"value": 0.003, "origin": "engineering_estimate"},
    "imu_bias_correlation_s": {"value": 100.0, "origin": "engineering_estimate"},
    "gnss_base_sigma_m": {
        "value": 0.5,
        "origin": "engineering_estimate anchored to DJI ±0.5 m GNSS hovering accuracy",
    },
    "hdop_range": {"value": [0.8, 2.5], "origin": "engineering_estimate"},
    "vdop_ratio": {"value": 1.5, "origin": "engineering_estimate"},
    "urban_multipath_bias_m": {
        "value": 6.0,
        "origin": (
            "engineering_estimate; distinct biased heavy-tail regime supported "
            "qualitatively by cited study"
        ),
    },
    "outage_duration_s": {"value": [1.0, 3.0], "origin": "engineering_estimate"},
    "vision_precision": {"value": 0.534, "origin": "published YOLOv8-M VisDrone result"},
    "vision_recall": {"value": 0.420, "origin": "published YOLOv8-M VisDrone result"},
    "vision_range_midpoint_m": {"value": 80.0, "origin": "engineering_estimate"},
}


@dataclass(frozen=True)
class SyntheticConfig:
    seed: int
    split: str
    duration_s: float = 3600.0
    rate_hz: float = 50.0


def _trajectory(t: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Five deterministic kinematic segments: straight, waypoint, loiter, evasive, landing."""
    p = np.zeros((len(t), 3))
    p[0, 2] = 30.0
    v = np.zeros_like(p)
    yaw = np.zeros(len(t))
    segment = np.minimum((t / (t[-1] + 1e-9) * 5).astype(int), 4)
    dt = t[1] - t[0]
    for i in range(1, len(t)):
        s = segment[i]
        if s == 0:
            desired = np.array([10.0, 0.0, 0.0])
        elif s == 1:
            desired = np.array([8.0, 5.0, 0.5])
        elif s == 2:
            phase = (t[i] - 0.4 * t[-1]) * 0.35
            desired = np.array([-6.0 * np.sin(phase), 6.0 * np.cos(phase), 0.0])
        elif s == 3:
            desired = np.array([12.0, 4.0 * np.sin(0.9 * t[i]), 0.0])
        else:
            desired = np.array([4.0, 0.0, -2.0])
        speed = np.linalg.norm(desired[:2])
        if speed > 16.0:
            desired[:2] *= 16.0 / speed
        desired[2] = np.clip(desired[2], -5.0, 5.0)
        acceleration = np.clip((desired - v[i - 1]) / dt, -4.0, 4.0)
        v[i] = v[i - 1] + acceleration * dt
        p[i] = p[i - 1] + v[i] * dt
        p[i, 2] = max(0.0, p[i, 2])
        yaw[i] = np.arctan2(v[i, 1], v[i, 0])
    a = np.gradient(v, dt, axis=0)
    return p, v, a, np.column_stack((np.zeros(len(t)), np.zeros(len(t)), yaw))


def generate(config: SyntheticConfig) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(config.seed)
    dt = 1.0 / config.rate_hz
    t = np.arange(0.0, config.duration_s, dt)
    position, velocity, acceleration, attitude = _trajectory(t)

    # BMI088 BST-BMI088-DS001: 175 µg/√Hz accelerometer and 0.014 °/s/√Hz gyro.
    accel_sigma = 175e-6 * G * np.sqrt(config.rate_hz / 2.0)
    gyro_sigma = np.deg2rad(0.014) * np.sqrt(config.rate_hz / 2.0)
    tau, bias_sigma = 100.0, 0.003  # engineering estimates; datasheet has no correlation time
    phi = np.exp(-dt / tau)
    bias = np.zeros_like(acceleration)
    for i in range(1, len(t)):
        bias[i] = phi * bias[i - 1] + bias_sigma * np.sqrt(1 - phi**2) * rng.normal(size=3)
    imu_accel = acceleration + bias + rng.normal(0.0, accel_sigma, acceleration.shape)
    imu_bias_jump = (t >= 300) & (t < 305)
    imu_accel[imu_bias_jump] += IMU_BIAS_JUMP_MPS2 * SEVERITY_SCALE[FaultSeverity.HIGH]
    yaw_rate = np.gradient(attitude[:, 2], dt)
    imu_gyro = np.column_stack((np.zeros(len(t)), np.zeros(len(t)), yaw_rate))
    imu_gyro += rng.normal(0.0, gyro_sigma, imu_gyro.shape)

    phase = rng.uniform(0, 2 * np.pi)
    hdop = np.clip(1.4 + 0.6 * np.sin(t / 17 + phase), 0.8, 2.5)
    vdop = 1.5 * hdop
    gnss_error = rng.normal(size=(len(t), 3)) * np.column_stack((hdop, hdop, vdop)) * 0.5
    drift = (t >= 200) & (t < 205)
    drift_elapsed = np.maximum(0.0, t - 200)
    gnss_error[drift] += (
        GNSS_DRIFT_RATE_MPS * SEVERITY_SCALE[FaultSeverity.HIGH] * drift_elapsed[drift, None]
    )
    urban = (t >= 400) & (t < 420)
    # Urban errors are biased and heavy-tailed, not merely enlarged Gaussian noise.
    gnss_error[urban, :2] += rng.standard_t(3, size=(urban.sum(), 2)) * 2.0 + 6.0
    outage = (t >= 500) & (t < 502)  # explicitly documented engineering-estimate duration
    communication_delay = np.where(
        (t >= 600) & (t < 605),
        COMMUNICATION_LATENCY_BASE_S * SEVERITY_SCALE[FaultSeverity.HIGH],
        0.0,
    )
    gnss = position + gnss_error
    gnss[outage] = np.nan

    distance = np.linalg.norm(position, axis=1)
    occlusion = np.where((t >= 700) & (t < 720), 0.8, 0.0)
    range_logit = np.clip((distance - 80.0) / 20.0, -60.0, 60.0)
    range_factor = 1.0 / (1.0 + np.exp(range_logit))
    clear = (distance < 50) & (occlusion == 0)
    p_detect = 0.420 * np.where(clear, 1.0, range_factor * (1 - occlusion))
    detected = rng.random(len(t)) < p_detect
    confidence = np.where(detected, rng.beta(8, 3, len(t)), np.nan)
    # Precision target sets the expected FP count relative to true positives.
    fp_probability = np.clip(p_detect * (1 / 0.534 - 1), 0, 1)
    false_positive = rng.random(len(t)) < fp_probability

    fault_active = (
        drift | urban | outage | imu_bias_jump | (communication_delay > 0) | (occlusion > 0)
    )
    origin = np.where(
        fault_active,
        DataOrigin.SYNTHETIC_FAULT.value,
        DataOrigin.SYNTHETIC.value,
    )
    return {
        "timestamp_s": t,
        "position_m": position,
        "velocity_mps": velocity,
        "acceleration_mps2": acceleration,
        "attitude_rad": attitude,
        "imu_accel_mps2": imu_accel,
        "imu_gyro_radps": imu_gyro,
        "imu_bias_mps2": bias,
        "hdop": hdop,
        "vdop": vdop,
        "gnss_position_m": gnss,
        "gnss_error_m": gnss_error,
        "urban_multipath": urban,
        "gnss_drift_active": drift,
        "gnss_outage": outage,
        "imu_bias_jump_active": imu_bias_jump,
        "communication_delay_s": communication_delay,
        "vision_clear": clear,
        "vision_detected": detected,
        "vision_false_positive": false_positive,
        "vision_confidence": confidence,
        "vision_p_detect": p_detect,
        "occlusion_fraction": occlusion,
        "origin": origin,
    }


def write_dataset(config: SyntheticConfig, output: Path, manifest_path: Path) -> dict:
    arrays = generate(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    entry = {
        "schema_version": "aeris-data-manifest-v1",
        "generator": "scripts/generate_synthetic_data.py",
        "generator_version": GENERATOR_VERSION,
        "file": output.as_posix(),
        "sha256": digest,
        "config": asdict(config),
        "provenance": [DataOrigin.SYNTHETIC.value, DataOrigin.SYNTHETIC_FAULT.value],
        "parameters": PARAMETER_LINEAGE,
        "citations": CITATIONS,
        "raw_imagery": False,
        "tuning_allowed": config.split == "tuning",
        "reported_benchmark_allowed": config.split == "held_out",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return entry
