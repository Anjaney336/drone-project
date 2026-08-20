# Primary demo: bridge inspection mission (real inference)

Every step below was individually run for real against a live backend this session — not scripted
to only look real. Run the product at `http://127.0.0.1:8501/`
(`python -m uvicorn aeris.app.api:app --host 127.0.0.1 --port 8501`, after
`python -m aeris.demo.seed` once). State once that seeded assets/missions are the **AERIS
DEMONSTRATION DATASET**; the trained model and its predictions are real, not seeded.

## 1. Create mission

**Missions** → fill the form (name, Bridge Inspection, district, asset BR-042) → Create mission.
Or via API: `POST /api/v1/missions` with `domain: "infrastructure"`.

## 2. Select drone (optional)

`POST /api/v1/drones` to register one, then reference its `drone_id` on the mission. Drone Health
shows it once telemetry exists.

## 3–5. Run real inference on a held-out image

`POST /api/v1/missions/{mission_id}/analyze` with a real image path (e.g. a test-split image from
`data/manifests/damage_detection_manifest.json`) and `model_key: "infrastructure_detection"`.
This calls the actual trained YOLOv8n checkpoint (`artifacts/experiments/
damage_detection_yolov8n_baseline/weights/best.pt`) — not a placeholder. Say explicitly: **"AI
Flagged: Possible Defect"**, never "Confirmed Damage."

## 6. See the detection overlay

Open **Missions → click the mission row** (or navigate to `#mission/{mission_id}`). The Mission
Media panel shows the analyzed image with real bounding boxes drawn from the model's stored
`xyxy` coordinates, colored per finding, with confidence in the tooltip.

## 7–8. Show drone health and mission reliability

If telemetry was ingested (`POST /api/v1/telemetry`), the Mission Detail page's Mission Reliability
card shows HIGH/MEDIUM/LOW with the real weighted components (navigation, sensor consistency,
telemetry continuity, battery, completeness) and plain-language reasons — never an unexplained
number. If no telemetry was sent, it honestly shows `UNKNOWN — No telemetry has been ingested for
this mission yet.` rather than fabricating a score.

## 9. Show priority explanation

**Decision Center** shows the asset's priority with its full factor list (severity, recurrence,
criticality, trend, geographic concentration) — the same transparent formula from before this
session, unchanged.

## 10–11. Send to human review, reviewer decides

**Human Review Queue** lists the pending finding with its mission's reliability attached (and a
qualifying note if that reliability is LOW). Choose **Confirmed / Rejected / Needs reinspection /
Escalated** — this calls `POST /api/v1/findings/{id}/review`, persists a `human_reviews` row, and
the finding leaves the pending queue.

## 12. Dashboard updates

Return to **Mission Detail** — the finding's review column now shows the verdict badge instead of
the decision dropdown, and the mission story bar at the top reflects HUMAN REVIEW as reached.

## Engineering depth (secondary, not the primary story)

Open **Digital Twin** to show the retained sensor-fusion/anomaly/safety-policy engineering core,
clearly labelled simulation. Open **Technical Intelligence** for the benchmark artifact boundary.
Neither is presented as flight validation or as the product's main workflow.

## Close

"AERIS: a drone performs a mission → AERIS checks mission health and reliability → AI analyzes
what the drone observed → offline data syncs when connectivity returns → the command center
prioritizes findings → a human makes the final decision."

## What this demo does not yet include

Agriculture (dataset still downloading — see `docs/agriculture_dataset_audit.md`), a scripted
single-command demo runner (each step above is currently a documented API call or UI click, not
one push-button script), and image upload from the browser (the `analyze` endpoint takes a server
filesystem path today, not a multipart upload).
