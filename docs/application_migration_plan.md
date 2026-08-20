# Application migration plan

This plan is based on a full read of `src/aeris/app/product_service.py` (830 lines),
`product_models.py`, `api.py`, `priority.py`, `inspection_analysis.py`, `schemas.py`, `service.py`,
`dashboard.py`, the frontend (`static/app.js`, `static/sw.js`), the reusable autonomy modules
(`autonomy/fusion/ekf.py`, `autonomy/anomaly/detector.py`, `autonomy/safety/risk.py`,
`data/telemetry.py`), and `tests/test_product_layer.py` / `tests/test_api_and_integrity.py`.
**36/36 existing tests pass** (`python -m pytest tests/ -q --basetemp=<writable dir>` — the
default pytest temp dir is blocked by a pre-existing Windows permission issue unrelated to this
work, worked around with an explicit `--basetemp`). This is the baseline that must keep passing.

## What actually exists today (corrects earlier assumptions)

The FastAPI app (`api.py`) mounts **two separate systems side by side**, already cleanly
namespaced — this separation does not need to be built, only preserved:

1. **Digital Twin / simulation API** (`/missions/*`, `/benchmark`, `/artifacts/*`,
   `/synthetic-data-preview`) backed by `service.MissionStore` and `schemas.py`. This is the
   counter-drone-era simulation engine: scenario/seed-driven telemetry, EKF state snapshots, the
   four-way benchmark. It is read-only from the frontend's perspective and already gated by
   `DataOrigin.SIMULATION`/`SYNTHETIC_FAULT`.
2. **Product API** (`/api/v1/*`) backed by `product_service.ProductStore`, a SQLite database
   (`artifacts/aeris_product.db`) with six tables: `assets`, `missions`, `observations`,
   `priority_assessments`, `actions`, `inspections`. This is the infrastructure-inspection product
   a prior session built: asset registry, mission creation/ingestion, an explainable priority
   engine (`priority.py`, transparent weighted formula, never fabricates confidence), a
   government action workflow (`ActionStatus` state machine with enforced valid transitions), and
   offline field sync (`inspections` table, idempotent on `client_record_id`).

The frontend (`static/app.js`, 40 dense lines covering command/map/missions/regions/actions/field/
digital/technical routes) already calls all of the above. The offline queue is real but simpler
than the README implied: it uses **`localStorage`** (not IndexedDB) for the pending-inspection
queue (`getQueue`/`setQueue`/`syncQueue` in `app.js`), plus a minimal service worker
(`sw.js`, 6 lines) that caches the app shell for offline load. This works for a hackathon demo but
has `localStorage`'s ~5-10MB practical size ceiling — worth stating honestly in `docs/offline_sync.md`
rather than calling it IndexedDB-grade.

`dashboard.py` (563 lines, Streamlit) is a separate technical-evidence viewer that calls the
Digital Twin endpoints — this is the "Technical Intelligence" surface, not the product frontend.

`inspection_analysis.py` defines the exact integration seam needed for real models: an abstract
`InspectionAnalyzer.analyze()` contract. The only implementation today,
`StructuredObservationAdapter`, deliberately performs no inference and always sets
`confidence=None` — this is the correct place to add a model-backed analyzer, not a design flaw
to route around.

## Component classification

| Component | Classification | Plan |
|---|---|---|
| `product_service.ProductStore` (SQLite schema + CRUD) | **ADAPT** | Extend, don't replace: add columns/tables for domain (infrastructure/agriculture), drone identity, telemetry-derived reliability, AI finding provenance (model name/version/task/confidence/timestamp), and a human-review verdict distinct from the existing `ActionStatus` asset-workflow. All six existing tables and their query methods keep working as-is. |
| `product_models.py` (pydantic schemas) | **ADAPT** | Add `Domain` enum, agriculture `MissionType` values, `AIFinding`/`HumanReview`/`DroneHealthAssessment`/`MissionReliabilityAssessment` request/response models. Existing models (`AssetCreate`, `ProductMissionCreate`, `IngestObservation`, `FieldInspection`, `SyncRequest`) are unchanged in shape; new optional fields only. |
| `priority.py` (`assess_priority`) | **KEEP** | Formula and transparency pattern are sound and domain-agnostic already (severity/confidence/criticality/recurrence/trend/geographic_impact). Mission reliability will be a *new, separate* explainable score (Phase 6), not folded into this one — they answer different questions ("how urgent" vs. "how trustworthy is this data"). |
| `inspection_analysis.py` (`InspectionAnalyzer` ABC) | **KEEP the contract, ADD implementations** | This is the model registry seam (Phase 9). New `InfrastructureDetectionModel`/`CrackSegmentationModel`/`AgricultureModel` adapters implement this interface; `StructuredObservationAdapter` stays as the manual-entry path. |
| `api.py` (`/api/v1/*` routes) | **ADAPT** | Add routes for AI findings, drone health, mission reliability, review queue actions, agriculture missions. Existing routes are unchanged. `/missions/*` (Digital Twin) routes are untouched. |
| `schemas.py`, `service.py` (Digital Twin) | **KEEP, unchanged** | Out of scope for the product pivot; still needed by `dashboard.py` and the `/missions/*` routes. |
| `autonomy/fusion/ekf.py` (`ConstantVelocityEKF`) | **ADAPT** | Reused as the quantitative core of *navigation reliability*: feed a mission's GNSS/position telemetry stream through it and read `normalized_innovation_squared` (already a first-class `TelemetryRecord` field) as the consistency signal, exactly as it already does for the Digital Twin. No interception-specific logic is carried over — only the filter and its innovation statistics. |
| `autonomy/anomaly/detector.py` (`SensorHealthMonitor.evaluate`) | **ADAPT** | Directly reusable, generic threshold-based consistency checker (speed/packet-delay bounds → anomaly events). Becomes the *telemetry continuity* signal generator for Mission Reliability. |
| `autonomy/safety/risk.py` (`RiskWeights`, `combine_risk`) | **ADAPT** | This is the best direct-reuse candidate: a generic weighted-combination-with-components pattern is exactly what an explainable Mission Reliability score needs. New `ReliabilityWeights` (navigation/sensor/telemetry/battery/completeness) replaces the interception-era `RiskWeights` (collision/geofence/etc.) — same mechanism, new dimensions. |
| `data/telemetry.py` (`TelemetryRecord`) | **KEEP, reused as-is** | Already has everything Mission Reliability needs: `gnss_quality`, `satellite_count`, `hdop`/`vdop`, `camera_confidence`, `ekf_innovation_m`, `normalized_innovation_squared`, `packet_delay_s`, `packet_loss`, `sensor_health`, plus `origin`/`scenario_id`/`seed`/`injected_fault` for the real-vs-simulated distinction this schema already enforces. No new telemetry schema needs inventing. |
| `autonomy/safety/engine.py`, `perception/detector.py`, `tracking/tracker.py`, `prediction/predictor.py` | **ARCHIVE (confirmed, no change from `docs/migration_audit.md`)** | Interception decision logic, simulated-target detection/tracking/trajectory prediction. Not referenced by any product-layer plan above. |
| `dashboard.py` | **KEEP, unchanged** | Legitimate secondary technical-evidence view; not touched by the product pivot. |
| `static/app.js`, `static/sw.js`, `static/index.html` | **ADAPT** | Add new routes/pages (AI Findings, Drone Health, Review Queue, Agriculture Intelligence) inside the existing single-file SPA pattern; keep the working `localStorage` queue and service worker rather than rebuilding offline storage. |

## Net migration shape

No existing table is dropped and no existing endpoint changes its response shape — this is
additive. New tables: `drones`, `telemetry_records` (mirrors `TelemetryRecord` for
mission-attached rows), `mission_reliability_assessments`, `ai_findings`, `human_reviews`. The
`missions` table gains a nullable `domain` column (`infrastructure` default, for backward
compatibility with the seeded demo data) and a nullable `drone_id`. This keeps all 36 existing
tests passing unmodified while giving Phase 5 onward a real place to attach the new concepts.
