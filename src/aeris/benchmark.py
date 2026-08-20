from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from aeris.autonomy.fusion import ConstantVelocityEKF
from aeris.models import utc_now
from aeris.simulation.scenarios import (
    ScenarioConfig,
    ScenarioSample,
    available_scenarios,
    generate_scenario,
)

VARIANTS = ("raw_measurements", "ekf_fixed", "ekf_hard_rejection", "aeris_adaptive")
ABLATIONS = ("full", "no_visual", "no_adaptive_trust", "no_nis", "no_prediction")


def sensor_stream_digest(samples: list[ScenarioSample]) -> str:
    """Hash the exact immutable inputs shared by every paired benchmark variant."""
    digest = hashlib.sha256()
    for sample in samples:
        for value in (
            sample.timestamp,
            sample.true_position,
            sample.true_velocity,
            sample.imu_acceleration,
            sample.barometer_altitude,
            sample.gnss.measurement,
            sample.gnss.packet_delay_s,
            sample.gnss.packet_loss,
            sample.camera_position,
            sample.camera_confidence,
        ):
            if value is None:
                digest.update(b"<NONE>")
            elif isinstance(value, np.ndarray):
                digest.update(np.asarray(value, dtype=np.float64).tobytes())
            else:
                digest.update(repr(value).encode("utf-8"))
            digest.update(b"\0")
        digest.update(json.dumps(sample.camera_frame, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def source_tree_digest() -> str:
    """Hash all active AERIS Python and configuration inputs, not only this module."""
    package_root = Path(__file__).parent
    repository_root = package_root.parents[1]
    paths = sorted(package_root.rglob("*.py"))
    paths.extend(
        path
        for path in (repository_root / "pyproject.toml", repository_root / "configs/aeris.yaml")
        if path.exists()
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(repository_root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _confusion(
    expected: list[bool], detected: list[bool], times: list[float]
) -> dict[str, float | None]:
    tp = sum(a and b for a, b in zip(expected, detected, strict=True))
    fp = sum((not a) and b for a, b in zip(expected, detected, strict=True))
    fn = sum(a and not b for a, b in zip(expected, detected, strict=True))
    tn = sum((not a) and (not b) for a, b in zip(expected, detected, strict=True))
    onset = next((t for t, e in zip(times, expected, strict=True) if e), None)
    detection = next(
        (t for t, e, d in zip(times, expected, detected, strict=True) if e and d), None
    )
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "anomaly_precision": precision,
        "anomaly_recall": recall,
        "anomaly_f1": None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall),
        "false_positive_rate": fp / max(fp + tn, 1),
        "false_negative_rate": fn / max(fn + tp, 1),
        "time_to_detect_s": None if onset is None or detection is None else detection - onset,
    }


def evaluate_variant(
    config: ScenarioConfig,
    variant: str,
    ablation: str = "full",
    samples: list[ScenarioSample] | None = None,
) -> dict[str, float | None]:
    if variant not in VARIANTS or ablation not in ABLATIONS:
        raise ValueError("Unknown variant or ablation")
    samples = samples or generate_scenario(config)
    policy = {
        "ekf_fixed": "fixed",
        "ekf_hard_rejection": "hard",
        "aeris_adaptive": "adaptive",
        "raw_measurements": "fixed",
    }[variant]
    if ablation in {"no_adaptive_trust", "no_nis"}:
        policy = "fixed"
    ekf = ConstantVelocityEKF(
        update_policy=policy, nis_threshold=1e12 if ablation == "no_nis" else 11.345
    )
    ekf.initialize(samples[0].true_position, samples[0].true_velocity, samples[0].timestamp)
    positions = []
    velocities = []
    expected = []
    detected = []
    nis_values = []
    ade = []
    fde = []
    geofence_correct = []
    previous = None
    previous_t = None
    started = time.perf_counter()
    for index, sample in enumerate(samples):
        expected.append(sample.fault_active)
        sensor_flags = []
        if variant == "raw_measurements":
            observations = []
            if sample.gnss.measurement is not None:
                observations.append((sample.gnss.measurement, 1 / 2.25))
            if sample.camera_position is not None and ablation != "no_visual":
                observations.append((sample.camera_position, 1 / 0.64))
            estimate = (
                np.average(
                    np.asarray([o[0] for o in observations]),
                    axis=0,
                    weights=[o[1] for o in observations],
                )
                if observations
                else np.full(3, np.nan)
            )
            velocity = (
                np.full(3, np.nan)
                if previous is None or not np.isfinite(estimate).all()
                else (estimate - previous) / max(sample.timestamp - previous_t, 1e-6)
            )
            if np.isfinite(estimate).all():
                previous, previous_t = estimate.copy(), sample.timestamp
        else:
            ekf.predict(sample.timestamp, sample.imu_acceleration)
            corroborated = bool(
                sample.camera_position is not None
                and sample.gnss.measurement is not None
                and np.linalg.norm(sample.camera_position - sample.gnss.measurement) < 6.0
            )
            if sample.camera_position is not None and ablation != "no_visual":
                result = ekf.update_position(
                    sample.camera_position,
                    np.eye(3) * 0.64,
                    "camera",
                    corroborated=corroborated,
                )
                if variant in {"ekf_hard_rejection", "aeris_adaptive"}:
                    sensor_flags.append(not result.accepted)
                nis_values.append(result.nis)
            elif ablation != "no_visual" and variant in {
                "ekf_hard_rejection",
                "aeris_adaptive",
            }:
                sensor_flags.append(True)
            if sample.gnss.measurement is not None:
                result = ekf.update_position(
                    sample.gnss.measurement,
                    np.eye(3) * 2.25,
                    "gnss",
                    corroborated=corroborated,
                )
                if variant in {"ekf_hard_rejection", "aeris_adaptive"}:
                    sensor_flags.append(not result.accepted)
                nis_values.append(result.nis)
            else:
                if variant in {"ekf_hard_rejection", "aeris_adaptive"}:
                    sensor_flags.append(sample.gnss.active)
            if variant in {"ekf_hard_rejection", "aeris_adaptive"}:
                sensor_flags.append(sample.gnss.packet_loss or sample.gnss.packet_delay_s > 0.5)
            estimate, velocity = ekf.x[:3].copy(), ekf.x[3:].copy()
        positions.append(estimate)
        velocities.append(velocity)
        detected.append(any(sensor_flags))
        if (
            ablation != "no_prediction"
            and np.isfinite(estimate).all()
            and np.isfinite(velocity).all()
        ):
            future = samples[index + 1 : min(index + 11, len(samples))]
            if future:
                prediction = np.asarray(
                    [estimate + velocity * (item.timestamp - sample.timestamp) for item in future]
                )
                truth = np.asarray([item.true_position for item in future])
                errors = np.linalg.norm(prediction - truth, axis=1)
                ade.append(float(np.mean(errors)))
                fde.append(float(errors[-1]))
                predicted_breach = bool(
                    np.any((prediction < [-50, -50, 0]) | (prediction > [150, 100, 120]))
                )
                truth_breach = bool(np.any((truth < [-50, -50, 0]) | (truth > [150, 100, 120])))
                geofence_correct.append(predicted_breach == truth_breach)
    elapsed = time.perf_counter() - started
    p_err = np.asarray(positions) - np.asarray([s.true_position for s in samples])
    v_err = np.asarray(velocities) - np.asarray([s.true_velocity for s in samples])
    pv = np.isfinite(p_err).all(axis=1)
    vv = np.isfinite(v_err).all(axis=1)
    position_norm = np.linalg.norm(p_err[pv], axis=1)
    velocity_norm = np.linalg.norm(v_err[vv], axis=1)
    return {
        "position_rmse_m": float(np.sqrt(np.mean(position_norm**2))) if pv.any() else None,
        "position_median_m": float(np.median(position_norm)) if pv.any() else None,
        "position_p95_m": float(np.percentile(position_norm, 95)) if pv.any() else None,
        "velocity_rmse_mps": float(np.sqrt(np.mean(velocity_norm**2))) if vv.any() else None,
        "nis_mean": float(np.mean(nis_values)) if nis_values else None,
        "nis_p95": float(np.percentile(nis_values, 95)) if nis_values else None,
        "trajectory_ade_m": float(np.mean(ade)) if ade else None,
        "trajectory_fde_m": float(np.mean(fde)) if fde else None,
        "geofence_detection_accuracy": (
            float(np.mean(geofence_correct)) if geofence_correct else None
        ),
        "collision_risk_prediction_error": None,
        "minimum_separation_m": None,
        "safe_response_selection_accuracy": None,
        **_confusion(expected, detected, [s.timestamp for s in samples]),
        "latency_ms_per_step": elapsed * 1000 / len(samples),
        "fps": len(samples) / max(elapsed, 1e-9),
    }


def _aggregate(values: list[float]) -> dict[str, float]:
    data = np.asarray(values, float)
    mean = float(np.mean(data))
    std = float(np.std(data, ddof=1)) if len(data) > 1 else 0.0
    half = 1.96 * std / max(np.sqrt(len(data)), 1)
    return {
        "mean": mean,
        "median": float(np.median(data)),
        "std": std,
        "p95": float(np.percentile(data, 95)),
        "ci95_low": max(0.0, mean - half),
        "ci95_high": mean + half,
    }


def _group_aggregate(records: list[dict], group: str, names: tuple[str, ...]) -> dict:
    output = {}
    for name in names:
        output[name] = {}
        for metric in (
            "position_rmse_m",
            "velocity_rmse_mps",
            "anomaly_f1",
            "trajectory_ade_m",
            "geofence_detection_accuracy",
            "latency_ms_per_step",
            "fps",
        ):
            values = [
                record["metrics"][metric]
                for record in records
                if record[group] == name
                and (group != "algorithm_variant" or record["ablation"] == "full")
                and record["metrics"][metric] is not None
            ]
            output[name][metric] = _aggregate(values) if values else None
    return output


def run_benchmark(seed: int = 7, trials: int = 1, include_ablation: bool = False) -> dict:
    records = []
    software = source_tree_digest()
    for trial in range(trials):
        trial_seed = seed + trial
        for scenario in available_scenarios():
            config = ScenarioConfig(scenario_id=scenario, seed=trial_seed)
            samples = generate_scenario(config)
            stream_digest = sensor_stream_digest(samples)
            for variant in VARIANTS:
                metrics = evaluate_variant(config, variant, samples=samples)
                if sensor_stream_digest(samples) != stream_digest:
                    raise RuntimeError(f"{variant} mutated the paired sensor stream")
                records.append(
                    {
                        "scenario": scenario,
                        "seed": trial_seed,
                        "config_hash": config.config_hash,
                        "dataset_version": config.dataset_version,
                        "algorithm_variant": variant,
                        "sensor_stream_sha256": stream_digest,
                        "ablation": "full",
                        "metrics": metrics,
                        "runtime": {
                            "latency_ms_per_step": metrics["latency_ms_per_step"],
                            "fps": metrics["fps"],
                        },
                        "fault_configuration": None
                        if samples[0].fault_spec is None
                        else asdict(samples[0].fault_spec),
                        "software_version": software,
                        "timestamp": utc_now(),
                    }
                )
            if include_ablation:
                for ablation in ABLATIONS[1:]:
                    metrics = evaluate_variant(config, "aeris_adaptive", ablation, samples)
                    if sensor_stream_digest(samples) != stream_digest:
                        raise RuntimeError(f"{ablation} mutated the paired sensor stream")
                    records.append(
                        {
                            "scenario": scenario,
                            "seed": trial_seed,
                            "config_hash": config.config_hash,
                            "dataset_version": config.dataset_version,
                            "algorithm_variant": "aeris_adaptive",
                            "sensor_stream_sha256": stream_digest,
                            "ablation": ablation,
                            "metrics": metrics,
                            "runtime": {
                                "latency_ms_per_step": metrics["latency_ms_per_step"],
                                "fps": metrics["fps"],
                            },
                            "fault_configuration": None
                            if samples[0].fault_spec is None
                            else asdict(samples[0].fault_spec),
                            "software_version": software,
                            "timestamp": utc_now(),
                        }
                    )
    aggregate = _group_aggregate(records, "algorithm_variant", VARIANTS)
    adaptive_records = [
        record for record in records if record["algorithm_variant"] == "aeris_adaptive"
    ]
    ablation_aggregate = _group_aggregate(adaptive_records, "ablation", ABLATIONS)
    aeris_records = [
        record
        for record in records
        if record["algorithm_variant"] == "aeris_adaptive" and record["ablation"] == "full"
    ]
    scenario_aggregate = _group_aggregate(aeris_records, "scenario", tuple(available_scenarios()))
    return {
        "schema_version": "aeris-benchmark-v2",
        "benchmark_type": "simulation",
        "generated_at": utc_now(),
        "host": platform.platform(),
        "paired_seed_start": seed,
        "trials": trials,
        "records": records,
        "aggregate": aggregate,
        "ablation_aggregate": ablation_aggregate,
        "scenario_aggregate": scenario_aggregate,
        "claim_boundary": "Simulation benchmark only; no field-performance claim.",
    }


def write_summary(report: dict, path: Path) -> None:
    rows = []
    for variant, metrics in report["aggregate"].items():
        for metric, summary in metrics.items():
            if summary:
                rows.append({"variant": variant, "metric": metric, **summary})
    for ablation, metrics in report.get("ablation_aggregate", {}).items():
        if ablation == "full":
            continue
        for metric, summary in metrics.items():
            if summary:
                rows.append({"variant": f"aeris_adaptive/{ablation}", "metric": metric, **summary})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant",
                "metric",
                "mean",
                "median",
                "std",
                "p95",
                "ci95_low",
                "ci95_high",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    md = [
        "# AERIS simulation benchmark summary",
        "",
        "> Simulation evidence only; not field performance.",
        "",
        "| Variant | Metric | Mean | 95% CI |",
        "|---|---:|---:|---:|",
    ]
    md += [
        f"| {r['variant']} | {r['metric']} | {r['mean']:.4f} | "
        f"[{r['ci95_low']:.4f}, {r['ci95_high']:.4f}] |"
        for r in rows
    ]
    path.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")


def refresh_report(path: Path) -> None:
    """Rebuild aggregate tables from measured records without rerunning experiments."""
    report = json.loads(path.read_text(encoding="utf-8"))
    report["aggregate"] = _group_aggregate(report["records"], "algorithm_variant", VARIANTS)
    adaptive_records = [
        record for record in report["records"] if record["algorithm_variant"] == "aeris_adaptive"
    ]
    report["ablation_aggregate"] = _group_aggregate(adaptive_records, "ablation", ABLATIONS)
    aeris_records = [
        record
        for record in report["records"]
        if record["algorithm_variant"] == "aeris_adaptive" and record["ablation"] == "full"
    ]
    report["scenario_aggregate"] = _group_aggregate(
        aeris_records, "scenario", tuple(available_scenarios())
    )
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_summary(report, path.with_name("benchmark_summary.csv"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    args = parser.parse_args()
    report = run_benchmark(args.seed, args.trials, args.ablation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_summary(report, args.output.with_name("benchmark_summary.csv"))
    print(f"Wrote {len(report['records'])} measured simulation records to {args.output}")


if __name__ == "__main__":
    main()
