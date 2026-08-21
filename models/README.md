# Published model checkpoints

This directory is **tracked in git**. It holds the checkpoints that ship with a clone, so
that `git clone` + install is enough to run real inference.

```
models/
  <experiment_name>/
    status.json            required — the registry reads this to decide READY vs NOT_TRAINED
    weights/best.pt        YOLO detection checkpoint
    best_model.pt          segmentation checkpoint
```

Do not hand-copy files here. Train, then publish:

```powershell
.venv\Scripts\python -m aeris.training.train --config configs/training/damage_detection.yaml
.venv\Scripts\python scripts/publish_model.py damage_detection_yolov8n_baseline
```

`scripts/publish_model.py` refuses to publish a run whose `status.json` is not `READY`, so a
half-finished or failed run cannot be mistaken for a shippable model.

Raw training output — logs, plots, per-epoch checkpoints — stays under `artifacts/`, which is
gitignored. Only the status file and the final checkpoint are promoted here.

If this directory is empty, every model reports `NOT_TRAINED`, `/api/v1/models/status` still
returns 200, and the UI shows **MODEL UNAVAILABLE** with analysis disabled. That is correct
behaviour, not a bug: AERIS never substitutes a fabricated finding for a missing model.
