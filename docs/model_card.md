# Model cards

One card per checkpoint the registry knows about. Every number here is a **held-out
test-split** measurement from our own training run — not field-validated accuracy, and not
a claim about any particular deployment site.

## Checkpoint availability

Checkpoints are **not** produced by cloning this repository. `aeris.app.model_registry`
resolves each model in this order:

1. `models/<experiment_name>/` — published checkpoint, tracked in git, ships with a clone.
2. `artifacts/experiments/<experiment_name>/` — raw local training run, gitignored.

If neither exists the model reports `NOT_TRAINED`, `/api/v1/models/status` still returns
200, and the UI shows **MODEL UNAVAILABLE** with the analysis button disabled. That is the
designed behaviour: an untrained model must never fall back to a fabricated finding.

To make a model available:

```powershell
.venv\Scripts\python -m aeris.training.train --config configs/training/damage_detection.yaml
.venv\Scripts\python scripts/publish_model.py damage_detection_yolov8n_baseline
```

Then commit `models/damage_detection_yolov8n_baseline/`.

---

## `damage_detection_yolov8n_baseline`

| | |
|---|---|
| Task | Infrastructure defect detection (object detection) |
| Architecture | YOLOv8n, fine-tuned from COCO-pretrained `yolov8n.pt` |
| Training config | `configs/training/damage_detection.yaml` |
| Dataset | `damage_detection_local`, 1,500 images, 70/15/15 split, seed 20260820 |
| Input size | 416 px | 
| Epochs | 15, batch 8, CPU-only |
| Checkpoint | `weights/best.pt` |

### Test-split metrics (225 held-out images)

| Metric | Value |
|---|---|
| mAP50 | 0.440 |
| mAP50-95 | 0.258 |
| Precision | 0.448 |
| Recall | 0.496 |

### Limitations

- **Class labels are unverified.** The source folder shipped with no `classes.txt` or
  README, so class ids 0 and 1 are anonymous. Findings are surfaced as
  `class_0_unverified` / `class_1_unverified`, never as a named defect type.
- **Severe class imbalance** (~39–44:1 between the two classes, consistent across splits).
- **Upstream licence is not retained** — see `docs/dataset.md`.
- These are modest numbers for a baseline and are stated as such. An `imgsz=640` variant
  measured mAP50 0.467 / mAP50-95 0.270 but the checkpoint swap was deliberately deferred;
  the shipped baseline remains the one quoted above. See
  `docs/yolo_baseline_diagnosis.md` for the full diagnosis and
  `docs/hardening_ledger.md` for the deferral rationale.

---

## `crack_segmentation_tinyunet_baseline`

| | |
|---|---|
| Task | Binary crack segmentation |
| Architecture | TinyUNet, base width 16, trained from scratch (no pretrained encoder) |
| Training config | `configs/training/crack_segmentation.yaml` |
| Dataset | `uav_crack_segmentation_local`, 315 images, 70/15/15 split, seed 20260820 |
| Input size | 256 px |
| Epochs | 30, batch 4, CPU-only (825.2 s elapsed) |
| Checkpoint | `best_model.pt` |

### Test-split metrics (48 held-out images)

| Metric | Value |
|---|---|
| Mean IoU | 0.501 |
| Mean Dice | 0.637 |
| Mean precision | 0.807 |
| Mean recall | 0.600 |

### Limitations

- **Recall (0.600) is well below precision (0.807).** When it flags a pixel it is usually
  right, but it misses real crack pixels more often than it should — a conservative
  boundary learned from only 220 training images with no pretrained encoder.
- Two test images scored IoU 0.0 (total misses).
- **Upstream licence is not retained** — see `docs/dataset.md`.
- Full analysis: `docs/crack_segmentation_validation.md`.

---

## `agriculture_mobilenetv3_baseline`

**Status: NOT BUILT.** No model exists, no dataset has been validated, and no metric is
claimed. The MH-SoyaHealthVision download did not complete integrity verification, so no
training was attempted (`docs/agriculture_dataset_audit.md`).

The adapter is registered so that `/api/v1/models/status` reports the domain honestly and
the UI disables the agriculture option. `analyze()` raises rather than returning anything.
