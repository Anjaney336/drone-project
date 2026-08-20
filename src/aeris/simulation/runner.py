from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from aeris.autonomy.anomaly import SensorHealthMonitor
from aeris.autonomy.fusion import ConstantVelocityEKF
from aeris.autonomy.perception import SimulationObservationDetector
from aeris.autonomy.prediction import ConstantVelocityPredictor
from aeris.autonomy.safety import Geofence, SafetyEngine
from aeris.autonomy.tracking import MultiObjectTracker
from aeris.data import TelemetryRecord
from aeris.models import DataOrigin, utc_now
from aeris.simulation.scenarios import ScenarioConfig, generate_scenario


def run_scenario(config: ScenarioConfig) -> dict:
    samples = generate_scenario(config)
    ekf = ConstantVelocityEKF(update_policy="adaptive")
    ekf.initialize(samples[0].true_position, samples[0].true_velocity, samples[0].timestamp)
    monitor, predictor, safety = SensorHealthMonitor(), ConstantVelocityPredictor(), SafetyEngine()
    detector, tracker = SimulationObservationDetector(), MultiObjectTracker()
    telemetry: list[dict] = []
    snapshots: list[dict] = []
    position_errors: list[float] = []
    velocity_errors: list[float] = []
    detected, expected = [], []
    started = time.perf_counter()
    for sample in samples:
        ekf.predict(sample.timestamp, sample.imu_acceleration)
        detections = detector.detect(sample.camera_frame, sample.timestamp)
        tracks = tracker.update(detections, sample.timestamp)
        primary = (
            min(tracks, key=lambda track: np.linalg.norm(track.position - ekf.x[:3]))
            if tracks
            else None
        )
        corroborated = bool(
            primary is not None
            and sample.gnss.measurement is not None
            and np.linalg.norm(primary.position - sample.gnss.measurement) < 6.0
        )
        camera_result = None
        if primary is not None and primary.missed_frames == 0:
            camera_result = ekf.update_position(
                primary.position,
                np.eye(3) * 0.64,
                "camera",
                corroborated=corroborated,
            )
        camera_estimate = ekf.estimate(
            accepted=True if camera_result is None else camera_result.accepted
        )
        result = None
        if sample.gnss.measurement is not None:
            result = ekf.update_position(
                sample.gnss.measurement,
                np.eye(3) * 2.25,
                "gnss",
                corroborated=corroborated,
            )
        estimate = ekf.estimate(accepted=True if result is None else result.accepted)
        disagreement = (
            None
            if sample.gnss.measurement is None or primary is None
            else float(np.linalg.norm(sample.gnss.measurement - primary.position))
        )
        camera_events = monitor.evaluate(
            camera_estimate,
            "camera",
            disagreement_m=disagreement,
            sensor_available=bool(detections),
        )
        events = camera_events + monitor.evaluate(
            estimate,
            "gnss",
            sample.gnss.packet_delay_s,
            disagreement_m=disagreement,
            sensor_available=sample.gnss.measurement is not None,
        )
        prediction = predictor.predict(estimate)
        secondary = [
            track for track in tracks if primary is None or track.track_id != primary.track_id
        ]
        monitored = None
        if secondary:
            other = secondary[0]
            monitored = [(other.position + other.velocity * t).tolist() for t in prediction.times]
        decision = safety.decide(
            prediction,
            events,
            float(np.trace(estimate.covariance)),
            Geofence((-50, -50, 0), (150, 100, 120)),
            monitored_positions=monitored,
            minimum_sensor_trust=min(estimate.sensor_trust.values(), default=1.0),
            packet_delay_s=sample.gnss.packet_delay_s,
        )
        position_errors.append(float(np.linalg.norm(estimate.position - sample.true_position)))
        velocity_errors.append(float(np.linalg.norm(estimate.velocity - sample.true_velocity)))
        expected.append(sample.fault_active)
        detected.append(bool(events))
        telemetry.append(
            TelemetryRecord(
                timestamp=sample.timestamp,
                position_m=tuple(map(float, estimate.position)),
                velocity_mps=tuple(map(float, estimate.velocity)),
                gnss_quality=None if sample.gnss.measurement is None else 1.0,
                camera_confidence=sample.camera_confidence,
                ekf_innovation_m=None
                if estimate.innovation is None
                else tuple(map(float, estimate.innovation)),
                normalized_innovation_squared=estimate.nis,
                packet_delay_s=sample.gnss.packet_delay_s,
                packet_loss=sample.gnss.packet_loss,
                sensor_health=estimate.sensor_trust,
                mission_mode="simulation",
                anomaly_label=events[0].anomaly_type if events else None,
                safety_state=decision.state,
                origin=DataOrigin.SYNTHETIC_FAULT if sample.fault_active else DataOrigin.SIMULATION,
                source="aeris.simulation.scenarios",
                scenario_id=config.scenario_id,
                seed=config.seed,
                injected_fault=sample.fault_label,
                fault_configuration=(
                    None if sample.fault_spec is None else asdict(sample.fault_spec)
                ),
                generator_version=config.dataset_version,
                configuration_hash=config.config_hash,
            ).model_dump(mode="json")
        )
        snapshots.append(
            {
                "timestamp": sample.timestamp,
                "observation_label": "SIMULATED",
                "true_position_m": sample.true_position.tolist(),
                "gnss_position_m": (
                    None if sample.gnss.measurement is None else sample.gnss.measurement.tolist()
                ),
                "camera_position_m": (
                    None if sample.camera_position is None else sample.camera_position.tolist()
                ),
                "detections": len(detections),
                "tracks": [
                    {
                        "track_id": t.track_id,
                        "class": t.object_class,
                        "bbox_xyxy": t.bbox_xyxy,
                        "velocity_mps": t.velocity.tolist(),
                        "image_velocity_px_s": t.image_velocity_px_s,
                        "confidence": t.confidence,
                    }
                    for t in tracks
                ],
                "covariance": estimate.covariance.tolist(),
                "prediction": asdict(prediction),
                "anomalies": [asdict(event) for event in events],
                "safety_decision": asdict(decision),
            }
        )
    elapsed = time.perf_counter() - started
    tp = sum(a and b for a, b in zip(expected, detected, strict=True))
    fp = sum((not a) and b for a, b in zip(expected, detected, strict=True))
    fn = sum(a and not b for a, b in zip(expected, detected, strict=True))
    return {
        "manifest": {**asdict(config), "config_hash": config.config_hash, "timestamp": utc_now()},
        "metrics": {
            "position_rmse_m": float(np.sqrt(np.mean(np.square(position_errors)))),
            "velocity_rmse_mps": float(np.sqrt(np.mean(np.square(velocity_errors)))),
            "anomaly_precision": tp / (tp + fp) if tp + fp else None,
            "anomaly_recall": tp / (tp + fn) if tp + fn else None,
            "latency_ms_per_step": elapsed * 1000 / len(samples),
            "fps": len(samples) / max(elapsed, 1e-9),
        },
        "telemetry": telemetry,
        "state_snapshots": snapshots,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="nominal")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("artifacts/simulation_run.json"))
    args = parser.parse_args()
    payload = run_scenario(ScenarioConfig(scenario_id=args.scenario, seed=args.seed))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["metrics"], indent=2))


if __name__ == "__main__":
    main()
