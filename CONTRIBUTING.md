# Contributing

Create a virtual environment, install `.[dev]`, and run `ruff check .` plus `pytest -q`. Keep sensor, estimator, API, and dashboard fields traceable. Never add UI-generated telemetry or performance claims without a reproducible artifact. Public, measured, synthetic, simulation, and synthetic-fault data require distinct provenance.

`aeris.models.DataOrigin` is the required structural vocabulary for provenance. Telemetry schemas require an origin and source; untagged telemetry must fail validation. The authoritative equal-stream report is `artifacts/benchmark.json`. `artifacts/legacy_protocol_benchmark.json` is quarantined transparency evidence and must never be read by the API, dashboard, one-pager, or headline-reporting path.

Product entities follow the same rule. Demonstration records must use `demonstration`; field
capture must use `field` or `user_uploaded`. Digital Twin `simulation`/`synthetic_fault` records
must never enter the inspection-evidence path. Do not add a model confidence unless it came from a
named, evaluated analyzer artifact. A missing confidence remains null and must be explained.

Generated runs belong under ignored `artifacts/`; raw datasets remain outside version control under `data/raw/` with a manifest in `data/manifests/`.
