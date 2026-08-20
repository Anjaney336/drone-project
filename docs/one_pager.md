# AERIS one-page technical brief

## Problem

Autonomous drones can lose trustworthy navigation when GNSS, vision, inertial sensing or
communications become noisy, delayed, unavailable or mutually inconsistent.

## Gap

Fixed-confidence fusion cannot distinguish a healthy measurement from one that contradicts the
predicted state. Hard rejection can also discard useful partial information.

## Solution

AERIS combines detector output, multi-object tracking, GNSS, IMU-assisted state prediction,
NIS-based consistency evidence, continuous sensor trust, short-horizon prediction and a
deterministic safety policy.

## Innovation

The proposed estimator converts innovation consistency into continuous per-sensor trust and
inflates measurement uncertainty instead of treating every input as fully trusted or fully
discarded. Every safety recommendation includes reason, evidence and a risk decomposition.

## Demonstrated result

| Simulation scenario | Raw fusion | Fixed EKF | Hard rejection | AERIS adaptive |
|---|---:|---:|---:|---:|
| GNSS drift, 100 paired seeds | 2.231 m | 2.019 m | 0.454 m | **0.438 m** |

Source: `artifacts/benchmark.json`; AERIS 95% CI [0.425, 0.450] m. Simulation benchmark
performance only—not field performance.

An internal benchmark audit found that the original comparison gave methods unequal sensor
access. We corrected the protocol and report the equal-stream result here, with the exact
legacy reproduction retained separately for transparency. See `docs/benchmark_methodology.md`.

## Technology readiness

**TRL 3–4:** analytical and experimental proof of concept validated in deterministic simulation;
not validated in a relevant or operational environment.

## Path to the next TRL

Complete verified Anti-UAV and EuRoC replay, collect synchronized real sensor data, perform
hardware-in-the-loop testing, then conduct controlled flight tests with independent ground truth
and an authorized abort process.
