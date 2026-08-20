# Benchmark methodology and protocol correction

## Reported result: equal sensor streams

The authoritative benchmark is `artifacts/benchmark.json`, schema `aeris-benchmark-v2`. For each
scenario and seed, `run_benchmark` calls `generate_scenario` exactly once and passes the same
immutable `ScenarioSample` sequence to raw fusion, fixed EKF, hard-rejection EKF and AERIS
adaptive fusion. Every record stores the same `sensor_stream_sha256` for its paired condition;
the harness recomputes the digest after each variant and fails if any variant mutates the stream.

The seed-7 command runs 100 paired trials using seeds 7–106. For GNSS drift:

| Equal-stream variant | Inputs | Mean position RMSE | 95% CI |
|---|---|---:|---:|
| Raw inverse-variance fusion | camera + GNSS | 2.231 m | [2.220, 2.242] m |
| Fixed EKF | camera + GNSS + IMU | 2.019 m | [2.005, 2.033] m |
| EKF hard rejection | camera + GNSS + IMU | 0.454 m | [0.443, 0.465] m |
| AERIS adaptive | camera + GNSS + IMU | **0.438 m** | **[0.425, 0.450] m** |

Source: `artifacts/benchmark.json`. These are simulation results, not flight performance.

## Retired result: unequal sensor streams

The v1 pitch benchmark was a single seed-7, 80-step GNSS-drift simulation. Raw and fixed-EKF
variants received GNSS only, while the adaptive variant received both camera and GNSS. The
retired NIS implementation also hard-rejected threshold excursions. The frozen reproduction is
`scripts/run_legacy_protocol_benchmark.py`; its isolated output is
`artifacts/legacy_protocol_benchmark.json`.

| Legacy variant | Inputs | Reproduced position RMSE | Historical rounded value |
|---|---|---:|---:|
| Raw measurement | GNSS only | 6.5515 m | 6.55 m |
| Fixed EKF | GNSS only | 5.8066 m | 5.81 m |
| Adaptive | camera + GNSS | 0.4944 m | 0.49 m |

**Non-equal-stream protocol — retained for transparency only, not the reported result.**

This comparison is biased because the adaptive method receives a lower-noise camera observation
that the baselines never see. The observed difference therefore combines input-quality and
sensor-availability advantages with any estimator advantage. It cannot isolate the effect of
adaptive fusion.

## Isolation controls

- `aeris.app.api` reads only `artifacts/benchmark.json`.
- The legacy runner is a standalone script outside the active benchmark package.
- The legacy artifact has `reported_result: false` and a non-equal-stream protocol status.
- Tests assert stream immutability and prevent the API reporting path from selecting the legacy
  artifact.
