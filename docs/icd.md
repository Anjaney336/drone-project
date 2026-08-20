# AERIS API interface control document

API version is `1.0.0`; JSON fields are additive within a minor version. Breaking schema or unit
changes require a major API version. Product records persist in SQLite; Digital Twin runs remain
in-process and disappear on restart.

## Product API (`/api/v1`)

| Method/path | Purpose |
|---|---|
| `GET /executive-summary` | Backend-derived asset, inspection, priority, mission and finding totals |
| `GET/POST /assets` | Filter or create provenance-tagged infrastructure assets |
| `GET /assets/{asset_id}` | Asset, observations, missions, evidence, priority and condition history |
| `GET/POST /missions` | Product mission register and creation |
| `GET /missions/{mission_id}` | Mission details and generated observations |
| `POST /missions/{mission_id}/ingest` | Structured observation ingestion; simulation origins rejected |
| `GET /priority-queue` | Ranked, explainable authority action queue |
| `POST /actions` | Create a provenance-tagged action |
| `PATCH /actions/{action_id}` | Persist a validated authority workflow transition |
| `GET /regions/analytics` | District coverage, priority concentration and recurring observations |
| `POST /sync` | Idempotently synchronize locally queued field observations |
| `GET /demo-dataset` | Export the exact AERIS demonstration dataset |

All create schemas forbid unknown fields and require an enum-backed origin plus non-empty source.
Field synchronization accepts only `field` or `user_uploaded`. Product mission ingestion rejects
`simulation` and `synthetic_fault` so Digital Twin output cannot masquerade as field evidence.

## Digital Twin and research API

| Method/path | Request | Response and units | Errors / unavailable behavior |
|---|---|---|---|
| `POST /missions` | `{scenario_id: string="nominal", seed: integer=7}`; unknown fields rejected | 201 `MissionSummary` with UUID, status, scenario and seed | 422 invalid/unknown field or scenario validation failure |
| `GET /missions/{id}` | UUID path | `MissionSummary` | 404 unknown mission |
| `GET /missions/{id}/state` | UUID path | latest telemetry and estimator snapshot; position m, velocity m/s, covariance SI-state units, NIS dimensionless | 404 unknown mission; `data_status="DATA UNAVAILABLE"` and null records when absent |
| `GET /missions/{id}/metrics` | UUID path | simulation metrics: position RMSE m, velocity RMSE m/s, latency ms/step, FPS Hz, rates dimensionless | 404 unknown mission; unavailable metrics remain JSON null |
| `GET /missions/{id}/events` | UUID path | timestamp seconds, anomaly type, source | 404 unknown mission; empty list means no reported event |
| `GET /missions/{id}/telemetry` | UUID path | complete telemetry records and state snapshots with provenance | 404 unknown mission |
| `GET /missions/{id}/artifacts` | UUID path | artifact path list (currently empty) | 404 unknown mission |
| `GET /benchmark` | none | authoritative simulation type, paired trial count, claim boundary and aggregate | if `artifacts/benchmark.json` is absent: `data_status="DATA UNAVAILABLE"`; legacy artifact is never read |
| `GET /artifacts/benchmark` | none | complete authoritative equal-stream JSON artifact | 404 if absent; never falls back to the legacy artifact |
| `GET /artifacts/synthetic-validation` | none | complete synthetic statistical-validation JSON | 404 if absent |
| `GET /synthetic-data-preview` | none | 30 held-out display samples: time s, IMU x m/s², GNSS x error m, HDOP and record origin | `DATA UNAVAILABLE` with empty records if generated file is absent |

The service does not execute hardware commands. OpenAPI schema is served at `/docs` while the
API is running.
