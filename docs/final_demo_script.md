# Final demo script — bridge inspection mission

## One command, real data, real model, real workflow

```powershell
python -m aeris.demo.seed
python scripts/run_demo_scenario.py
```

This is not a scripted illusion — `scripts/run_demo_scenario.py` calls the exact same
`ProductStore` and `model_registry` code the live API and frontend use. It prints real output at
every step: a real mission ID, a real drone registration, a real held-out test-split image
(never seen during training — selected from `data/manifests/damage_detection_manifest.json`'s
`split: "test"` records), real YOLOv8n predictions with real confidence scores, real mission
reliability computed from real ingested telemetry, the real transparent priority formula, and a
real persisted human-review verdict.

If the model isn't `READY` (e.g., a fresh checkout before training), the script says so and stops
rather than fabricating a result — this is enforced by `ModelAdapter._require_ready()`, the same
guard that protects the API.

## Then open it live

```powershell
python -m uvicorn aeris.app.api:app --host 127.0.0.1 --port 8501
```

Open the mission URL the script prints (`http://127.0.0.1:8501/#mission/<id>`) to show the same
data rendered in the UI: the mission-story bar, reliability breakdown, the AI analysis table, and
the review verdict — all traced to the one mission ID, matching what the script just printed.

## The 12 steps, mapped to what a judge sees

| Step | Script output | UI equivalent |
|---|---|---|
| 1. Create mission | Mission ID printed | Missions page, Mission Detail header |
| 2. Assign drone | Drone ID printed | Drone Health page |
| 3. Select image | Real test-split file path printed | Mission Media panel |
| 4. Ingest telemetry | Record count printed | Drone health card on Mission Detail |
| 5. Run real AI analysis | `Model status: READY`, real prediction count | — |
| 6. Store findings | Each finding's real label/confidence/model | AI analysis table + bbox overlay |
| 7. Drone health | Per-dimension percentages | Drone health card |
| 8. Mission reliability | HIGH/MEDIUM/LOW + real reasons | Mission Reliability card |
| 9. Priority explanation | Real formula factors | Decision Center |
| 10. Send to review | Highest-confidence finding named | Human Review Queue |
| 11. Reviewer decision | Verdict persisted | Review column badge |
| 12. Decision Center updates | Live metrics | Command Center |

## Live upload variant (shows the browser-native workflow, not just the API)

From the Mission Detail page created by the script, use the **Upload inspection image** form to
upload a second real image directly from the browser — no server file path needed. This exercises
`POST /api/v1/missions/{id}/media` → `POST /api/v1/missions/{id}/analyze`, the same chain
verified via curl in `artifacts/current_project_audit.md`.

## What this demo does not claim

No agriculture (dataset still downloading, honestly excluded). No video (frame-sampling
architecture documented but not built this pass — see the final engineering report). No
real-time/live-camera inference — this is mission-based, post-capture analysis, stated plainly.
