# AERIS research and SIH delivery roadmap

## Research questions

1. Does continuous NIS-conditioned trust weighting reduce state error under single- and multi-sensor degradation compared with fixed-noise and hard-rejection EKFs?
2. How quickly and reliably can AERIS detect drift, dropout, bias, disagreement, latency, and packet loss at controlled severities?
3. Do uncertainty and predicted motion improve deterministic safety decisions without an unacceptable false-alarm or compute burden?

## Stage gates

| Gate | Evidence required | Status |
|---|---|---|
| G0 integrity | provenance schema, no fabricated values, repository audit | complete |
| G1 deterministic simulation | 12 scenarios, LOW–EXTREME severity, recovery, unit/integration tests | complete |
| G2 statistical simulation | paired 100-seed MC, four fair variants, ablation, CI artifacts | implemented; rerun after each method change |
| G3 public replay | Anti-UAV perception and EuRoC visual-inertial adapters with checksum/license record | adapter ready; complete datasets pending |
| G4 hardware-in-loop | synchronized PX4/ArduPilot telemetry, calibrated sensor timestamps, safety supervisor | planned |
| G5 controlled flight | approved test range, independent ground truth, abort authority, incident log | planned |
| G6 deployment study | Indian operating conditions, regulatory review, cybersecurity and human factors | planned |

## SIH demonstration sequence

Run nominal first, then GNSS drift, camera occlusion, and combined degradation with a fixed seed. Show the sensor-trust transition, NIS evidence, estimated covariance, predicted trajectory, risk decomposition, and deterministic action. State “simulation” verbally and on-screen. Report the equal-stream result; direct questions about the historical 0.49 m figure to `docs/benchmark_methodology.md` and its explicitly non-comparable legacy artifact.

## Acceptance criteria

- no algorithm reads future ground truth or fault labels;
- all variants receive identical available sensor streams;
- raw dropout remains null and is never backfilled from truth;
- each result records scenario, seed, configuration hash, data version, variant, fault configuration, software version, and UTC timestamp;
- flight claims remain blocked until G5 evidence exists.
