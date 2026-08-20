# AERIS product architecture

The primary product converts inspection inputs into authority decisions:

```text
FIELD / USER-UPLOADED DATA                 AERIS DIGITAL TWIN
            │                         simulation + synthetic fault
            └──────────────┬──────────────────────┘
                           ↓
             PROVENANCE-GATED INGESTION
                           ↓
       STRUCTURED OBSERVATION / ANALYZER ADAPTER
                           ↓
                ASSET CONDITION RECORD
                           ↓
       EXPLAINABLE PRIORITY ASSESSMENT + HISTORY
                           ↓
          DISTRICT AGGREGATION + ACTION QUEUE
                           ↓
          AUTHORIZED HUMAN WORKFLOW DECISION
```

## Product layer

- `product_models.py`: strict entities and origin-gated request schemas.
- `product_service.py`: SQLite repository, deterministic seed, aggregation, synchronization,
  mission workflow, and persisted actions.
- `priority.py`: published weighted score and human-readable contributing factors.
- `inspection_analysis.py`: pluggable analyzer contract. The current structured adapter performs no
  image inference and emits no confidence.
- `static/`: responsive dependency-free web client and service-worker-backed field interface.
- `api.py`: OpenAPI product endpoints plus the existing Digital Twin endpoints.

SQLite is the prototype persistence layer. SQL tables and repository boundaries are intentionally
portable to PostgreSQL/PostGIS; latitude/longitude become a geometry column in that migration.

## Engineering core

The Digital Twin retains the validated one-way lineage:

`seeded simulator → detector contract → tracker → EKF → anomaly monitor → predictor →`
`deterministic safety policy → typed API`

The product schema rejects simulation and synthetic-fault origins as field observations. Digital
Twin output is technical evidence and never silently becomes infrastructure evidence.

## Data contract

Every database table includes `origin`, `source`, and `timestamp`. `DataOrigin` distinguishes
demonstration, field, user-uploaded, measured, public-benchmark, simulation, synthetic, and
synthetic-fault records. Missing confidence remains JSON `null`; the priority engine applies its
documented neutral confidence component and explains that choice.

The web client creates only layout, filtering, and map projection. Asset values, counts, findings,
priorities, explanations, mission state, and action status come from API records. Field records are
stored locally before explicit idempotent synchronization.
