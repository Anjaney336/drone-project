# AERIS — AI-Enabled Drone Mission Intelligence

Drones can collect thousands of images, videos and telemetry records, but authorities still need
humans to manually determine what matters. AERIS transforms drone mission data into AI-assisted
findings, evaluates the reliability of the mission data, prioritizes assets requiring attention,
and routes evidence to human reviewers.

It answers four questions per mission: **what did the drone see**, **can the mission data be
trusted**, **how urgent is it**, and **what should a human do next**.

## The workflow

Open the app, click **New Mission**, pick a domain, fill in mission info, attach your own inspection
image(s) and (optionally) a telemetry CSV/JSON, and click **Create & Analyze Mission**. AERIS then:

1. stores your upload (`POST /api/v1/missions/{id}/media`, no server file path required), validated
   against real JPEG/PNG signatures rather than a declared content type;
2. runs a trained model on it — YOLOv8n for defect detection, TinyUNet for crack segmentation —
   returning real bounding boxes and confidence scores. If no checkpoint is published the model
   reports `NOT_TRAINED` and analysis is disabled; it never substitutes a fabricated finding.
   See [Checkpoints are not produced by cloning](#checkpoints-are-not-produced-by-cloning);
3. scores mission reliability from whatever telemetry you actually provided. A dimension with no
   supporting telemetry is reported `NOT AVAILABLE` and **excluded from the score**, with the
   remaining weights renormalised — a file carrying only timestamps returns `UNKNOWN`, not a
   middling number that looks like a measurement;
4. shows a one-screen Mission Analysis Report (status, findings, drone health, reliability,
   priority, recommended action) before the detailed breakdown;
5. routes the finding to Human Review. AI never marks anything "Confirmed" — only a reviewer does,
   `CONFIRMED` and `REJECTED` are terminal, and every verdict is appended to an audit trail.

Seeded demonstration records (10 assets, 4 missions, seed 2026) ship for the Government Decision
Center. They carry `origin: demonstration` and are never relabelled as yours; once you add your own
data the aggregate views report the provenance mix (`mixed`, with a per-origin breakdown) rather
than describing everything as demonstration data.

## Active models (real, measured, not placeholders)

| Model | Task | Test-split metrics | Trained? |
|---|---|---|---|
| YOLOv8n (`damage_detection_yolov8n_baseline`) | Infrastructure defect detection | mAP50 0.440, mAP50-95 0.258, precision 0.448, recall 0.496 | Yes |
| TinyUNet (`crack_segmentation_tinyunet_baseline`) | Binary crack segmentation | Mean IoU 0.501, mean Dice 0.637, precision 0.807, recall 0.600 | Yes |
| Agriculture (MH-SoyaHealthVision) | Crop-health classification | — | **No** — dataset integrity verification incomplete, no model trained |

### Checkpoints are not produced by cloning

A model is `READY` only when its checkpoint is present on disk. The registry looks in
`models/<experiment_name>/` (tracked in git, ships with a clone) and then in
`artifacts/experiments/<experiment_name>/` (raw local training run, gitignored).

**If `models/` is empty, all three models report `NOT_TRAINED`**, `/api/v1/models/status`
still returns 200, and the UI shows *MODEL UNAVAILABLE* with the analysis button disabled.
That is designed behaviour — AERIS never substitutes a fabricated finding for a missing
model — but it does mean a bare clone has no inference until a checkpoint is published:

```powershell
.venv\Scripts\python -m aeris.training.train --config configs/training/damage_detection.yaml
.venv\Scripts\python scripts/publish_model.py damage_detection_yolov8n_baseline
```

Then commit `models/damage_detection_yolov8n_baseline/`. See `models/README.md`.

Full diagnosis, limitations, and reproduction commands:
[`docs/model_card.md`](docs/model_card.md) (per checkpoint),
[`docs/yolo_baseline_diagnosis.md`](docs/yolo_baseline_diagnosis.md),
[`docs/crack_segmentation_validation.md`](docs/crack_segmentation_validation.md). These are
held-out **test-split** metrics — not field-validated accuracy, stated explicitly everywhere
they appear.

## Run in three commands

**Python 3.10, 3.11 or 3.12 is required.** The pinned `torch==2.5.1` publishes no wheels
for 3.13 or newer, so a newer interpreter fails at install time. Check with
`python --version`; if it is 3.13+, install 3.12 and create the virtualenv with
`py -3.12 -m venv .venv`.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m uvicorn aeris.app.api:app --host 127.0.0.1 --port 8501
```

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m uvicorn aeris.app.api:app --host 127.0.0.1 --port 8501
```

Open <http://127.0.0.1:8501/>. OpenAPI documentation is at
<http://127.0.0.1:8501/docs>.

For an editable install, run
`.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e .` first.
`requirements.lock` carries its own `--extra-index-url` for CPU-only torch/torchvision wheels, so
installing it never pulls a multi-gigabyte CUDA build. 8501 is the one canonical port — README,
Dockerfile, `.env.example`, both console scripts and every demo script agree on it.

## Reproduce the evidence

```powershell
.venv\Scripts\python scripts/export_demo_dataset.py --check
.venv\Scripts\python -m aeris.benchmark --seed 7 --trials 100 --ablation --output artifacts/benchmark.json
.venv\Scripts\python scripts/run_demo_scenario.py
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m pytest -q
```

The seeded product dataset is committed at
[`data/demo/aeris_demo_seed_2026.json`](data/demo/aeris_demo_seed_2026.json). Its origin, source,
timestamp, and seed are explicit on every collection, and its SHA-256 is pinned in
[`docs/dataset.md`](docs/dataset.md). `--check` regenerates it and fails if the committed bytes
drift; CI runs that on every push, so the integrity claim is enforced rather than asserted. `scripts/run_demo_scenario.py` runs the full
mission→inference→reliability→review workflow against a real held-out test image in one command.

## Validated engineering core

The original autonomy work remains as a backend engineering component: pluggable perception,
tracking, six-state EKF, uncertainty, NIS anomaly evidence, adaptive sensor trust, trajectory
prediction, deterministic safety policy, seeded fault injection, and a four-way paired benchmark.
It appears under **Digital Twin** and **Technical Intelligence**, not as the product homepage.

On the equal-stream GNSS-drift simulation benchmark (seeds 7–106), measured position RMSE is
2.231 m raw, 2.019 m fixed EKF, 0.454 m hard rejection, and 0.438 m AERIS adaptive (95% CI
[0.425, 0.450] m). These are **simulation benchmark results, not field performance**. The
authoritative artifact is `artifacts/benchmark.json`, which is regenerated rather than
committed — reproduce it with the `aeris-benchmark` command under
[Reproduce the evidence](#reproduce-the-evidence). Method:
[`docs/benchmark_methodology.md`](docs/benchmark_methodology.md).

## Evidence boundaries

- Every persisted product, telemetry, and synchronization record requires `origin` and `source`.
- Demonstration, field, user-uploaded, measured, public-benchmark, simulation, synthetic, and
  synthetic-fault origins are structurally distinct.
- Digital Twin telemetry cannot be submitted through the field-ingestion schema.
- The UI computes presentation geometry only; operational values come from API records.
- AERIS recommends actions but does not issue drone, vehicle, or maintenance hardware commands.
- A review verdict is an accountability record: CONFIRMED and REJECTED are terminal and
  cannot be silently overwritten. The reviewer name is **self-asserted, not
  authenticated** — the prototype has no login, so the audit trail records who claimed to
  review, not who provably did.
- State-changing requests can be guarded with a shared secret (`AERIS_API_TOKEN`);
  `GET /api/v1/health` reports `write_protection` so an unguarded deployment is visibly
  unguarded. Reads are always open.

Architecture, API, demo, data, and validation details are in
[`docs/architecture.md`](docs/architecture.md), [`docs/icd.md`](docs/icd.md),
[`docs/demo.md`](docs/demo.md), [`docs/dataset.md`](docs/dataset.md), and
[`docs/validation.md`](docs/validation.md).
