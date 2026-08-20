# Migration audit — counter-drone research core → mission-intelligence product

This audit classifies every major module in `src/aeris/**` before any further code changes, per
the pivot direction confirmed 2026-08-20: retire the counter-drone/interception framing, keep the
product-facing infrastructure-inspection layer that a prior session already built (see
`docs/architecture.md`, `README.md`), and extend it with agriculture, drone-health/mission
reliability, and real trained perception models.

Classification legend: **KEEP** (used as-is), **ADAPT** (code is reused but repurposed/renamed/
reframed), **ARCHIVE** (preserved, not deleted, but not part of the active product path),
**REMOVE** (safe to delete — none identified this pass; nothing is deleted without a separate
explicit pass).

## Product layer — `src/aeris/app/`

| Module | Classification | Rationale |
|---|---|---|
| `product_models.py`, `product_service.py`, `priority.py` | **KEEP, then ADAPT** | Origin-gated schema, SQLite repository, explainable priority engine are exactly the mission-intelligence data model the spec asks for. Must be **extended**, not replaced: add an agriculture `MissionType`/domain field, a `MissionReliability` entity, and human-review verdicts (`CONFIRMED`/`REJECTED`/`NEEDS_REINSPECTION`/`ESCALATED`) alongside the existing `ActionStatus` workflow. |
| `inspection_analysis.py` | **ADAPT** | Currently a pluggable adapter contract that performs no image inference ("emits no confidence" by design). This is the correct integration seam for the trained infrastructure/agriculture models — wire real inference in here rather than replacing the contract. |
| `api.py`, `schemas.py`, `service.py` | **KEEP, then ADAPT** | REST surface is sound; needs new endpoints for agriculture missions, drone health, and the review queue. |
| `static/` (PWA client, service worker, offline queue) | **KEEP** | Already implements the offline-first field-capture workflow (section 9 of the spec: ONLINE/OFFLINE/SYNC PENDING/SYNCED). Extend UI screens, don't rebuild the sync mechanism. |
| `dashboard.py` | **ADAPT** | Needs review to confirm it's the Streamlit engineering view referenced by the old `scripts/run_dashboard_streamlit.py` lineage vs. the new FastAPI product UI; keep only if it serves a distinct engineering-debug purpose, otherwise fold into Digital Twin panel. |

## Autonomy / sensor-fusion core — `src/aeris/autonomy/`

| Module | Classification | Rationale |
|---|---|---|
| `fusion/ekf.py` | **ADAPT** | Six-state EKF with NIS-based adaptive trust is directly reusable as the quantitative engine behind **GNSS/navigation reliability** in the new Mission Reliability Engine (section 8). Reframe its output (trust weight, NIS statistic) as a reliability signal, not an interception state estimate. |
| `anomaly/detector.py` | **ADAPT** | NIS-consistency anomaly monitor becomes the **sensor/telemetry consistency** component of mission reliability scoring. |
| `safety/risk.py` | **ADAPT** | Weighted risk decomposition (collision/geofence/uncertainty/sensor-degradation/communication) is structurally the same pattern the spec asks for in the reliability score (navigation + sensor + telemetry + completeness). Reuse the weighted-sum-with-explanations pattern; replace collision/geofence-specific weights with mission-reliability weights. |
| `safety/engine.py` | **ARCHIVE** | Deterministic safety *policy* (evasive/engagement-style action selection) is specific to interception decision-making, which the product does not perform (AERIS "recommends actions but does not issue drone... commands" — already stated in README). Not part of the product path; retained under Digital Twin as technical evidence only, not exposed as a product feature. |
| `perception/detector.py` | **ARCHIVE** | This is the Digital-Twin's simulated-target detector contract (feeds the tracker in the deterministic simulation), not a trained image-inference model. The real infrastructure/agriculture CV models are a new, separate component wired through `inspection_analysis.py`. |
| `tracking/tracker.py` | **ARCHIVE** | Multi-target tracking for the simulated digital-twin scene only; no product use case tracks multiple airborne targets. |
| `prediction/predictor.py` | **ARCHIVE** | Trajectory prediction for the simulated intercept geometry; not applicable to inspection missions, which don't require predicting another drone's flight path. Kept as Digital Twin technical evidence, not surfaced in the product. |

## Simulation — `src/aeris/simulation/`

| Module | Classification | Rationale |
|---|---|---|
| `runner.py`, `scenarios.py`, `fault_injection.py` | **ADAPT** | Per the pivot instruction, this may remain **only** as a clearly labelled digital twin / controlled telemetry fault-testing environment (drift, dropout, bias, latency, packet loss) — genuinely useful for demonstrating drone-health degradation scenarios in the demo. Must never be presented as flight validation or product evidence; already gated by `DataOrigin.SIMULATION`/`SYNTHETIC_FAULT` in the data contract, which is correct and should stay. |

## Data — `src/aeris/data/`

| Module | Classification | Rationale |
|---|---|---|
| `ingestion.py`, `telemetry.py` | **KEEP** | Origin-gated ingestion and telemetry schemas are domain-agnostic infrastructure the product needs regardless of pivot. |
| `synthetic.py` | **ADAPT** | Synthetic sensor/fault generation stays as Digital Twin supporting data only, per data-contract rules already in place. |
| `visdrone.py` | **ARCHIVE** | VisDrone adapter targets aerial small-object detection (pedestrians/vehicles), not infrastructure defects or crops. Not deleted (dataset itself is a candidate perception benchmark per `docs/dataset.md`), but not part of the active product training path. |

## Top level

| Module | Classification | Rationale |
|---|---|---|
| `benchmark.py` | **ARCHIVE** | Four-way paired EKF benchmark (raw/fixed/hard-rejection/adaptive) is real, honest simulation evidence for the *sensor-fusion research* claim, not for the mission-intelligence product. Keep as Digital Twin technical evidence (already positioned this way in README); do not present its RMSE figures as product-facing evidence, and do not carry its terminology ("interception", "target") into product docs. |
| `models.py` | **KEEP** | `DataOrigin` and shared typed primitives are used across both layers. |
| `.legacy_backup/` | **ARCHIVE (unchanged)** | Already quarantined by the prior session per `docs/repository_audit.md`; left untouched. |

## Net effect

Nothing above is deleted in this pass. The **ADAPT** items in `autonomy/fusion`, `autonomy/anomaly`,
and `autonomy/safety/risk.py` are the concrete reuse path for the new Mission Reliability Engine —
they give it a real quantitative basis (NIS statistics, adaptive trust weights, weighted risk
decomposition) instead of an unexplained black-box score, satisfying the "show WHY" requirement.
The **ARCHIVE** items stay reachable under the existing Digital Twin / Technical Intelligence
panel, correctly separated from field-reported product data, but are not extended further and are
not referenced by any new agriculture or infrastructure-defect feature.
