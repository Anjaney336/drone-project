# Agriculture model selection

Selected only after the real audit in `docs/agriculture_dataset_final_audit.md` — not before.

## Dataset task, input, output

- **Task:** image classification (determined from the actual annotation structure —
  folder-per-class, no bounding boxes or masks).
- **Input:** a single UAV-captured RGB image.
- **Output:** one of 4 classes — `healthy`, `rust`, `mosaic`, `pest_attack` — with a confidence
  score.

## Architecture

**MobileNetV3-Small**, ImageNet-pretrained, fine-tuned end to end, final classifier layer replaced
for 4 classes.

**Why this fits:** same CPU-only constraint as the infrastructure models (no CUDA device in this
environment). MobileNetV3-Small is one of the smallest well-validated ImageNet backbones
(~2.5M params), making CPU fine-tuning on ~1,650 training images tractable in a hackathon
timeframe. A larger backbone (ResNet50, EfficientNet-B3+) was rejected for the same reason the
infrastructure models avoided heavier architectures: no evidence this dataset's difficulty
justifies the extra compute, and CPU training time scales directly against it.

## Baseline configuration

| Setting | Value |
|---|---|
| Input size | 224×224 (resized from native 3840×2160) |
| Batch size | 16 |
| Optimizer | Adam, lr 0.0005 |
| Epochs | up to 10, early stopping patience 4 |
| Seed | 20260820 |

## Augmentation

Horizontal flip only, **train split exclusively** — no augmentation applied to validation or test
data, consistent with every other training pipeline in this repository.

## Split methodology (leakage prevention)

**Group-aware split by flight session**, not per-image random — see
`docs/agriculture_dataset_final_audit.md` for why: consecutive video frames from one drone flight
are near-duplicates, so a naive random split would leak them across train/val/test and inflate
test accuracy. `scripts/build_agriculture_splits.py` assigns entire flight sessions
(9–13 per class) to exactly one split. Split ratios target 70/15/15 at the *session* level, so the
resulting per-image counts are not exactly 70/15/15 (session sizes vary) — this is expected and
correct; forcing exact per-image ratios would require breaking a session across splits, which is
the leak this method exists to prevent.

## Evaluation metrics

Per-class precision, recall, F1, and a full confusion matrix on the **untouched test split**,
plus overall accuracy. Validation split is used only for model selection (best-checkpoint-by-val-loss
and early stopping) — never for the reported final numbers.

## Known limitations, stated in advance

- Real class imbalance (rust 1,000 vs. healthy 280 images) is not corrected in this baseline —
  no class weighting, no oversampling. Per-class recall for the minority class should be read with
  this in mind.
- The `healthy` class's filenames (`image_NNN.jpg`) lack the flight-session marker the other three
  classes have, so its "sessions" are treated as individual frames — a more conservative (safer)
  grouping than assuming they share sessions, but it does mean healthy images were split more
  granularly than the other classes.
- Single train/test run (no k-fold cross-validation) — appropriate for a hackathon-timeframe
  baseline, not a claim of statistically robust generalization.
- 224px input from 4K source images discards significant detail; this is a deliberate CPU-time
  tradeoff, documented rather than hidden.

## Reproduce

```powershell
python scripts/build_agriculture_splits.py
python -m aeris.training.train --config configs/training/agriculture_uav.yaml
```
