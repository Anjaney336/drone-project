# AERIS validation report

This report describes artifacts regenerated on 2026-08-20. Performance evidence is deterministic
Python **simulation benchmark performance, not field performance**.

## Evidence boundary

The active path is labelled simulator observation → detector contract → tracker → EKF → anomaly
monitor → trajectory predictor → deterministic safety policy → typed API → read-only dashboard.
There is no flight-controller command path. There is no flight test, hardware-in-the-loop test,
real GNSS/IMU capture, learned-detector run, or operational-environment validation.

VisDrone is not present or wired into the active runtime. Anti-UAV and EuRoC remain candidate
public datasets and contribute no reported metric. Generated supporting sensor records are
explicitly `synthetic` or `synthetic_fault`; the benchmark scenario records are `simulation` or
`synthetic_fault`.

## Authoritative equal-stream benchmark

`artifacts/benchmark.json` contains 12 scenarios × 100 paired seeds × four full comparators plus
four AERIS ablations. Every record includes scenario, seed, configuration hash, generator version,
algorithm/ablation, fault configuration, timestamp, software version, and sensor-stream SHA-256.
For each scenario/seed, all variants carry the same digest.

Across all full scenarios, mean position RMSE was 2.441377 m raw, 1.302545 m fixed EKF,
4.085313 m hard-rejection EKF, and 1.055891 m AERIS. AERIS aggregate 95% CI was
[0.955794, 1.155989] m; the broad interval reflects difficult mixed scenarios. Mean velocity
RMSE was 0.672451 m/s, anomaly F1 0.843012, and trajectory ADE 1.048015 m for AERIS.

The primary GNSS-drift result is 2.231073 m raw, 2.019222 m fixed EKF, 0.453888 m hard
rejection, and 0.437848 m AERIS, with AERIS 95% CI [0.425495, 0.450201] m. The complete
scenario table, including cases where AERIS does not win, is in `docs/validation.md`.

## Ablation evidence

Mean position RMSE was 1.055891 m full AERIS, 1.977775 m without visual input, and 1.302545 m
without adaptive trust or without NIS. Removing prediction leaves estimation RMSE unchanged by
design but makes ADE unavailable. These values trace to `artifacts/benchmark.json`.

## Legacy protocol quarantine

`artifacts/legacy_protocol_benchmark.json` exactly reproduces the historical 6.5515 m raw,
5.8066 m fixed EKF, and 0.4944 m adaptive figures. It is marked `reported_result: false` because
raw/fixed received GNSS only while adaptive received GNSS plus camera. The API and dashboard read
only `artifacts/benchmark.json`; `docs/benchmark_methodology.md` explains the discrepancy.

## Synthetic-data validation

`artifacts/synthetic_data_validation.json` records passing checks for tuning seed 20261 and
held-out seed 20262: short-interval IMU Allan deviation, open-sky GNSS DOP scaling, detector-output
precision/recall tolerance, and complete provenance. Numerical parameter origins and explicit
engineering estimates are in each `data/manifests/synthetic_*.json` and
`docs/synthetic_data.md`. No raw imagery is fabricated.

## Reproducibility commands

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
ruff check .
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m aeris.benchmark --seed 7 --trials 100 --ablation --output artifacts/benchmark.json
.venv\Scripts\python.exe scripts/run_legacy_protocol_benchmark.py --seed 7 --output artifacts/legacy_protocol_benchmark.json
.venv\Scripts\python.exe scripts/generate_synthetic_data.py
.venv\Scripts\python.exe scripts/validate_synthetic_data.py
```

## Remaining research risks

- combined degradation is the largest estimation weakness;
- IMU-bias and camera-occlusion cases show comparator underperformance rather than universal wins;
- stochastic fault magnitudes are primarily labelled engineering estimates, not calibrated data;
- detector outputs do not establish real-image perception performance;
- collision response lacks independent truth and the motion model omits wind and full dynamics;
- CI calculations are normal approximations and are not certification evidence.
