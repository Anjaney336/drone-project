# AERIS API quick reference

The service is exposed by `src/aeris/app/api.py` and is intended for local/demo use.
Start it with the command in `docs/judge_quickstart.md`, then open `/docs` for the
interactive OpenAPI contract.

## Core endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/v1/models/status` | Model registry status, readiness, and provenance |
| `POST` | `/api/v1/inspect` | Analyze an inspection image with a selected ready model |
| `POST` | `/api/v1/telemetry/import` | Import telemetry CSV and compute explainable reliability |
| `GET` | `/api/v1/missions` | List persisted missions and findings |
| `GET` | `/demo-dataset` | Export the deterministic AERIS demonstration dataset |

The API refuses to fabricate model output when a checkpoint is unavailable. Model
readiness and data origin are returned with results so downstream clients can distinguish
measured, field, simulation, and synthetic evidence.

For request/response schemas, use the generated OpenAPI page at `http://127.0.0.1:8000/docs`
while the service is running. The web dashboard's “backend unavailable” message links
back to this document.
