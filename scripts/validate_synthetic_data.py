from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aeris.data.synthetic import PARAMETER_LINEAGE, G


def validate(path: Path) -> dict:
    data = np.load(path)
    dt = float(np.median(np.diff(data["timestamp_s"])))
    accel_noise = data["imu_accel_mps2"] - data["acceleration_mps2"] - data["imu_bias_mps2"]
    clean_imu = ~data["imu_bias_jump_active"]
    clean_pairs = clean_imu[:-1] & clean_imu[1:]
    allan = np.sqrt(0.5 * np.mean(np.diff(accel_noise, axis=0)[clean_pairs] ** 2))
    allan_target = 175e-6 * G * np.sqrt(1 / (2 * dt))
    bias = data["imu_bias_mps2"]
    bias_x, bias_y = bias[:-1].reshape(-1), bias[1:].reshape(-1)
    estimated_phi = float(np.dot(bias_x, bias_y) / np.dot(bias_x, bias_x))
    estimated_tau = float(-dt / np.log(estimated_phi))
    gm_innovation = bias_y - estimated_phi * bias_x
    estimated_bias_sigma = float(np.std(gm_innovation) / np.sqrt(1 - estimated_phi**2))
    valid = ~data["gnss_outage"] & ~data["urban_multipath"] & ~data["gnss_drift_active"]
    normalized = data["gnss_error_m"][valid, 0] / data["hdop"][valid]
    low = valid & (data["hdop"] < np.median(data["hdop"])) & ~data["urban_multipath"]
    high = valid & (data["hdop"] >= np.median(data["hdop"])) & ~data["urban_multipath"]
    low_sigma = float(np.std(data["gnss_error_m"][low, 0]))
    high_sigma = float(np.std(data["gnss_error_m"][high, 0]))
    clear = data["vision_clear"]
    recall = float(np.mean(data["vision_detected"][clear]))
    tp, fp = int(data["vision_detected"].sum()), int(data["vision_false_positive"].sum())
    precision = tp / (tp + fp)
    checks = {
        "imu_allan_relative_error_below_10pct": bool(abs(allan / allan_target - 1) < 0.10),
        "imu_gauss_markov_parameters_within_30pct": bool(
            abs(estimated_tau / 100.0 - 1) < 0.30 and abs(estimated_bias_sigma / 0.003 - 1) < 0.30
        ),
        "gnss_dop_scaling_present": bool(high_sigma > low_sigma and 0.4 < np.std(normalized) < 0.6),
        "vision_clear_recall_within_5_points": bool(abs(recall - 0.420) < 0.05),
        "vision_precision_within_5_points": bool(abs(precision - 0.534) < 0.05),
        "provenance_complete": bool(
            np.all(np.isin(data["origin"], ["synthetic", "synthetic_fault"]))
        ),
    }
    return {
        "dataset": path.as_posix(),
        "checks": checks,
        "passed": all(checks.values()),
        "observed": {
            "imu_allan_deviation_tau_dt_mps2": float(allan),
            "imu_allan_target_mps2": float(allan_target),
            "imu_bias_correlation_time_s": estimated_tau,
            "imu_bias_stationary_sigma_mps2": estimated_bias_sigma,
            "gnss_low_hdop_sigma_m": low_sigma,
            "gnss_high_hdop_sigma_m": high_sigma,
            "gnss_normalized_sigma_m": float(np.std(normalized)),
            "vision_clear_recall": recall,
            "vision_precision": precision,
        },
        "targets": {
            "vision_precision": PARAMETER_LINEAGE["vision_precision"]["value"],
            "vision_recall": PARAMETER_LINEAGE["vision_recall"]["value"],
        },
    }


def main() -> None:
    reports = [
        validate(Path("data/processed/synthetic/tuning.npz")),
        validate(Path("data/processed/synthetic/held_out.npz")),
    ]
    output = {
        "schema_version": "aeris-synthetic-validation-v1",
        "reports": reports,
        "passed": all(r["passed"] for r in reports),
    }
    target = Path("artifacts/synthetic_data_validation.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    if not output["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
