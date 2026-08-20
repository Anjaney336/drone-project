# Mission Reliability Engine

Answers "can we trust this mission's data?" — separately from "what did the drone find?" and "how
urgent is it?" (that's `priority.py`, unchanged). Implementation:
[`src/aeris/app/mission_reliability.py`](../src/aeris/app/mission_reliability.py).

## Why this exists, and what it reuses

Per [`docs/migration_audit.md`](migration_audit.md) and
[`docs/application_migration_plan.md`](application_migration_plan.md), the counter-drone-era
`aeris.autonomy.safety.risk.combine_risk`/`RiskWeights` pattern — a generic weighted decomposition
with named components, each independently inspectable — is directly reused as `_combine` in the
reliability module. The dimensions themselves are new (navigation/sensor/telemetry/battery/
completeness replace collision/geofence/uncertainty/sensor-degradation/communication), because
mission reliability and interception risk are different questions answered with the same
mechanism.

`aeris.autonomy.anomaly.detector.SensorHealthMonitor`'s NIS-excursion threshold (dividing by 25.0)
and packet-delay threshold (0.5s) are reused as constants (`NIS_EXCURSION_DIVISOR`,
`MAX_PACKET_DELAY_S`) so a mission that was run through the Digital Twin's EKF produces reliability
numbers on the same scale as its Digital Twin anomaly evidence. **The EKF itself is not re-run**
against product telemetry in this pass — `TelemetryIngest.normalized_innovation_squared` is
consumed as a value the caller supplies (from the Digital Twin when a mission is simulated, or
absent for a real field mission without an onboard estimator yet). This is a stated limitation, not
a hidden one.

## Dimensions and formula

```
score = 100 × (0.30×navigation + 0.20×sensor_consistency + 0.20×telemetry_continuity
             + 0.15×battery_power + 0.15×data_completeness)

HIGH:   score ≥ 75
MEDIUM: 50 ≤ score < 75
LOW:    score < 50
UNKNOWN: no telemetry recorded, or no substantive dimension assessable
```

## Missing data is NOT AVAILABLE, never a stand-in value

A dimension with no telemetry behind it is reported in `unavailable_components` with the
reason it could not be assessed, and is **excluded from the score**. The remaining weights
are renormalised to sum to 1.0 and returned as `weights_used`, so a mission assessed on two
dimensions is scored out of those two rather than being credited or penalised for telemetry
it never carried.

No dimension is ever given a neutral or optimistic stand-in, because a score computed from
invented inputs is indistinguishable from one computed from real measurements.

| Dimension | Signal used | When data is missing |
|---|---|---|
| Navigation | Mean NIS (`normalized_innovation_squared`) if present, else mean `gnss_quality` | NOT AVAILABLE — excluded from the score |
| Sensor consistency | Mean `camera_confidence` | NOT AVAILABLE — excluded from the score |
| Telemetry continuity | Fraction of *reporting* records showing `packet_loss` or delay over 0.5s | NOT AVAILABLE — the absence of a `packet_loss` column is not evidence of an unbroken stream, so it must not score as one |
| Battery/power | Minimum `battery_percent` observed during the mission (worst case, not average) | NOT AVAILABLE — excluded from the score |
| Data completeness | Fraction of the four tracked fields actually present across all records | Always computable, but never scored alone — see below |

`data_completeness` describes how much telemetry arrived, not whether the flight was sound.
It cannot by itself justify a reliability verdict, so at least one of navigation, sensor
consistency, telemetry continuity or battery must be assessable before any score is
produced. A file carrying only timestamps therefore returns **UNKNOWN with a null score**,
listing all five dimensions as NOT AVAILABLE — not a middling number that looks like a
measurement.

Every assessment returns a `reasons` list — the literal sentences shown in the UI — not just the
numeric components, matching the requirement that the system always explain **why**, e.g.:

```
MISSION RELIABILITY: LOW (39.0)
⚠ GNSS/navigation consistency degraded (1 innovation excursion detected)
✓ Camera data complete
⚠ 2 of 40 reporting record(s) showed packet loss or delay above 0.5s
✓ Battery remained within expected operating range
Data completeness: 88% of tracked telemetry fields present across 2 record(s)
```
(This is real output from `python -c "..."` exercising `ProductStore.ingest_telemetry` against two
hand-constructed telemetry rows — see the smoke test in
`artifacts/product_validation_report.md` (regenerated, not committed) — not a
mocked example.)

## Real vs. simulated telemetry

Every persisted `telemetry_records` row carries its `origin` (`DataOrigin.FIELD`/`MEASURED` for
real data, `SIMULATION`/`SYNTHETIC_FAULT` for Digital Twin output). `assess_mission_reliability`
sets `is_simulation=True` on the returned assessment if **any** contributing row came from a
simulated/synthetic-fault origin, and this flag is persisted alongside the score
(`mission_reliability_assessments.is_simulation`) and must be surfaced in the UI wherever a
reliability rating is shown, so a demo mission's reliability is never mistaken for a real-flight
measurement.

## Known limitations

- No live EKF re-run on product telemetry yet (see above) — NIS is consumed, not computed, in this
  MVP pass.
- Weights (`ReliabilityWeights`) are engineering estimates carried over from the same class of
  decision the original `RiskWeights` represented — not independently calibrated against real
  incident data, because none exists yet for this product.
- `battery_power` and `sensor_consistency` currently use single proxy signals
  (`battery_percent` minimum, `camera_confidence` mean) rather than a fuller sensor-health model;
  extending this to more `TelemetryRecord` fields (`hdop`, `vdop`, `sensor_health` dict,
  `magnetometer_ut`) is future work.
