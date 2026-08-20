# Validation scope

An audit of this repository (`README.md`, all of `docs/`, the frontend JS/HTML) for unsupported
claims found **none** — every place "validated" or similar language appears, it is already
qualified correctly (e.g. "test-split metrics — not field-validated accuracy",
"not claimed to be production-grade government offline infrastructure"). This document formalizes
that boundary explicitly so it stays true as the project grows.

## Four levels, and where AERIS actually sits

| Level | What it means | AERIS status |
|---|---|---|
| **1. Dataset validation** | Model metrics measured on a held-out test split of a specific dataset | **Done**, for both infrastructure models and the new agriculture model — see each model card |
| **2. Software validation** | The application itself works: API tests, integration tests, upload→inference→review chain exercised end to end | **Done** — 51/51 automated tests, plus manual browser-driven walkthroughs documented in prior session artifacts |
| **3. Simulation validation** | The retained Digital Twin (EKF/NIS/safety-policy engineering core) evaluated against synthetic/simulated sensor streams | **Done, clearly labelled** — `origin: simulation`/`synthetic_fault` on every such record, never mixed into product data |
| **4. Field validation** | Real-world deployment: real drone flights, real structural engineers confirming real defects, measured in operational conditions | **NOT done.** No real flight data exists in this repository. No claim of field validation appears anywhere, and this document exists specifically to keep it that way. |

## The honest framing to use going forward

- "Prototype decision-support system evaluated on available datasets." — correct.
- "AI findings require human review." — correct, and structurally enforced (see `ReviewVerdict`).
- "Not a replacement for certified structural inspection." — correct, should be stated wherever
  the product's authority is described.
- Anything implying level 4 (field-proven, deployment-ready, safe for autonomous operation) is
  **not supported by any evidence in this repository** and must not be written without real
  field data to back it.
