# Judge quickstart

## HOW DOES A JUDGE RUN THIS IN 5–10 MINUTES?

```powershell
git clone https://github.com/Anjaney336/drone-project.git
cd drone-project
python -m venv .venv
.venv\Scripts\python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock
.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e .
.venv\Scripts\python -m aeris.demo.seed
.venv\Scripts\python -m uvicorn aeris.app.api:app --host 127.0.0.1 --port 8501
```

Open <http://127.0.0.1:8501/>. That's it — no dataset download required to see the product work,
because `data/samples/` ships in the repository with real held-out infrastructure images.

## Try it with zero setup beyond the above

1. Click **New Mission**.
2. Pick **Infrastructure**, fill in a name and asset.
3. Upload an image from `data/samples/damage_detection/images/` (or your own JPEG/PNG).
4. Click **Create & Analyze Mission** — this runs the actual trained YOLOv8n checkpoint, not a
   placeholder.
5. Watch the Mission Analysis Report: real findings, real bounding boxes, a reliability score
   (HIGH/MEDIUM/LOW with reasons), and a review-queue-ready finding.

Or run the fully scripted version of the same thing:

```powershell
.venv\Scripts\python scripts/run_demo_scenario.py
```

## Verify everything yourself, independently

```powershell
.venv\Scripts\python -m pytest -q                    # 51/51
.venv\Scripts\python -m ruff check .                  # 0 errors
.venv\Scripts\python scripts/verify_datasets.py       # dataset integrity, checksums, split leakage
```

## What's real vs. what's a work in progress

See `docs/final_validation.md` for the exact test-by-test breakdown and
`docs/validation_scope.md` for what "validated" does and does not mean here. In short:
infrastructure inspection is fully working end to end with two real trained models; agriculture
has a real, license-confirmed, integrity-verified dataset and a training run in progress —
check `GET /api/v1/models/status` for its current, honest state before assuming it's ready.
