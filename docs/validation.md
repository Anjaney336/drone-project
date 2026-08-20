# Validation and benchmark design

`pytest` covers filter prediction/update and innovation, anomaly evidence, sensor trust, tracking,
prediction, safety state transitions, API schemas, scenario reproducibility, dashboard unavailable
rendering, priority scoring, demonstration reproducibility, mission ingestion, persisted action
transitions, idempotent offline synchronization, provenance separation, and an end-to-end
injected-fault run.

The benchmark runs the same twelve seeded scenarios against:

1. raw measurements;
2. fixed-noise EKF;
3. EKF with NIS rejection;
4. AERIS adaptive fusion.

It reports only values it computes: position/velocity RMSE, median and p95 position error, NIS statistics, anomaly precision/recall/F1/FPR/FNR/time-to-detect, trajectory ADE/FDE, loop latency, and FPS. Metrics requiring absent truth—such as learned-detector mAP and GPU utilization—are not displayed as measured results. Simulation metrics must not be generalized to flight performance.

The end-to-end simulator camera passes through the detector contract and tracker before fusion. It
is a labelled simulator observation, not learned detector inference. Product entities use a
persistent SQLite prototype database. Known gaps include no real infrastructure-defect dataset or
evaluated model, no real inspection deployment, no real telemetry benchmark, no complete
Anti-UAV/EuRoC local evaluation, no HIL/SIL autopilot integration, no PostGIS migration, no user
authentication/authorization, and no actuator authorization layer.

## Monte Carlo method

The authoritative run uses 100 consecutive paired seeds, 7–106. A scenario is generated once per
seed, hashed, and the immutable sample sequence is passed to every comparator. Pairing removes
between-stream randomness from method differences; independent draws per method would confound
fusion behavior with input luck. The harness records every seed and SHA-256 stream digest.

For GNSS drift, AERIS mean RMSE is 0.437848 m with sample standard deviation 0.063024 m across
100 trials. The normal-approximation 95% half-width is `1.96 × 0.063024 / √100 = 0.012353 m`,
yielding [0.425495, 0.450201] m. Thus 100 was retained because the observed half-width is small
relative to the mean and the run remains reproducible on judge hardware; this is post-run
precision justification, not a prospective power claim. Values come from `artifacts/benchmark.json`.

## Full equal-stream scenario result

Mean position RMSE in metres over seeds 7–106; all values come from the full-ablation records in
`artifacts/benchmark.json`.

| Scenario | Raw | Fixed EKF | Hard rejection | AERIS adaptive |
|---|---:|---:|---:|---:|
| nominal | 1.216 | 0.399 | 0.403 | **0.385** |
| GNSS drift | 2.231 | 2.019 | 0.454 | **0.438** |
| GNSS dropout | 1.286 | 0.418 | 0.422 | **0.411** |
| IMU bias | **1.216** | 1.289 | 14.955 | 1.594 |
| camera degradation | 6.147 | 1.891 | 0.552 | **0.542** |
| camera occlusion | 1.923 | **0.541** | 0.548 | 0.546 |
| packet loss | 1.241 | 0.408 | 0.413 | **0.398** |
| communication latency | 1.216 | 0.399 | 0.403 | **0.385** |
| multiple drones | 1.220 | 0.404 | 0.410 | **0.393** |
| sensor disagreement | 3.206 | 3.326 | 0.422 | **0.412** |
| geofence breach | 1.216 | 0.399 | 0.403 | **0.385** |
| combined degradation | 7.178 | **4.138** | 29.640 | 6.780 |

AERIS does not win every case: raw is best for the injected IMU-bias scenario, fixed EKF is
marginally best under camera occlusion, and fixed EKF materially outperforms AERIS under combined
degradation. These are visible research gaps, not omitted outliers.
