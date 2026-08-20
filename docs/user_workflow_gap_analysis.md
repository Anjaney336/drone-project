# User workflow gap analysis

Audited directly against the running system, 2026-08-20 23:40 IST.

## 1–2. Trained models / READY checkpoints

| Model | Status | Evidence |
|---|---|---|
| YOLOv8n damage detection | **READY** | `artifacts/experiments/damage_detection_yolov8n_baseline/weights/best.pt`, real test-split metrics |
| TinyUNet crack segmentation | **READY** | `artifacts/experiments/crack_segmentation_tinyunet_baseline/best_model.pt`, real test-split metrics |
| Agriculture model | **NOT_TRAINED** | No config, no checkpoint exists |

## 3. Can YOLO run inference on an uploaded image? **YES**, already wired: `POST
/api/v1/missions/{id}/media` → `POST /api/v1/missions/{id}/analyze`, verified end-to-end this
session (curl + a passing integration test).

## 4. Can TinyUNet run inference on an uploaded image? **Backend: yes** (`CrackSegmentationModel`
in the registry, READY). **Not wired to the analyze endpoint's default path** — `analyze()`
defaults to `model_key: "infrastructure_detection"`; a caller must explicitly pass
`model_key: "crack_segmentation"` to reach it. No UI control exists to choose it. **Gap.**

## 5–7. Agriculture dataset

Download just reached 100% of expected bytes **and then failed real integrity verification**
(`Bad magic number for file header` on the first nested zip when actually read, not just a
central-directory check) — likely corrupted across this session's multiple pause/resume cycles. A
fresh, uninterrupted download was restarted in the background. **Not extracted, not audited, no
model exists.** Full detail in `docs/agriculture_dataset_audit.md`.

## 8. Image upload API — **EXISTS**, real, tested (`POST /api/v1/missions/{id}/media`).

## 9. Video upload — **DOES NOT EXIST.** No endpoint, no frame-sampling code, no UI.

## 10. Telemetry upload — **DOES NOT EXIST as a file upload.** `POST /api/v1/telemetry` accepts a
JSON array of `TelemetryIngest` objects, not a CSV/JSON file. A user cannot hand AERIS a telemetry
log file today — they would need to hand-construct a JSON request body.

## 11. Fabricated/demo values in the frontend — **none found**, confirmed again this pass; every
seeded record carries `origin: "demonstration"` and is tagged as such in the UI.

## The actual gap: workflow, not capability

Everything technically needed for "upload data → real AI analysis" exists at the API level and has
been individually verified. **What does not exist is the product experience that makes this the
obvious first thing a user does.** Specifically:

| Required | Current state |
|---|---|
| A landing screen that says "upload your data, get an analysis" | Landing page is Command Center — an executive dashboard of seeded demonstration metrics. A first-time user sees charts about districts, not an invitation to analyze their own mission. |
| A guided mission-creation flow (domain → info → upload → analyze) | `missionsPage()` is a single flat form (name/type/district/asset) with no upload step and no explicit "Analyze" action — upload only exists deep inside Mission Detail, reachable only after already knowing a mission ID exists. |
| A single "Analyze Mission" action | Exists as two separate manual actions (upload, then trigger analyze) buried in Mission Detail's media card, not a guided step. |
| A results page a non-ML person can read in seconds | Mission Detail is close (it has all the right data: reliability, findings, review) but is laid out as an engineering detail page, not a "MISSION ANALYSIS REPORT" summary-first view. |
| Telemetry file upload | Missing entirely (see #10). |
| Video upload/analysis | Missing entirely (see #9). |
| Navigation hierarchy (primary workflow vs. secondary government dashboard) | Flat — Command Center, Missions, Regions, Decision Center, Review, Drone Health, Field, Digital Twin, Technical Intelligence all sit at the same nav level with no visual distinction between "do this first" and "authority views this later." |

This document is the basis for the redesign that follows: reuse everything in the left column,
build the right column.
