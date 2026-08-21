# Crack segmentation validation

Model: `TinyUNet` (base width 16), trained on the 220-image train split of the UAV crack
segmentation dataset, seed `20260820`. Training completed in the background without
interruption — 825.2s elapsed, early stopping did not trigger (best val loss recorded at the
final epoch), checkpoint at
`models/crack_segmentation_tinyunet_baseline/best_model.pt` once published (raw run: `artifacts/experiments/crack_segmentation_tinyunet_baseline/best_model.pt`).
Evaluation script: [`scripts/evaluate_crack_segmentation.py`](../scripts/evaluate_crack_segmentation.py)
— loads the saved checkpoint, does not retrain.

## Test-split metrics (48 held-out images, never seen in training)

| Metric | Value |
|---|---|
| Mean IoU | **0.501** |
| Mean Dice | **0.637** |
| Mean precision | **0.807** |
| Mean recall | **0.600** |
| Best single-image IoU | 0.908 (`slide814.png`) |
| Worst single-image IoU | 0.0 (`slide1542.png`, `slide965.png` — total misses) |

Full per-image breakdown: `artifacts/experiments/crack_segmentation_results/per_image_metrics.csv` (regenerated, not committed)
(48 rows, one per test image).

## Honest reading of these numbers

Precision (0.807) is notably higher than recall (0.600): when the model predicts a pixel is
crack, it's usually right, but it **misses real crack pixels more often than it should**. This
is a realistic pattern for a small (220-image), from-scratch, no-pretrained-encoder baseline —
it has learned a conservative decision boundary rather than an aggressive one. This is stated
here rather than only in the "limitations" section because it's the single most important thing
to know before trusting this model's output: **a "no crack detected" result from this baseline is
less reliable than a "crack detected" result.**

## Visual examples — not cherry-picked

Nine example overlays are saved to
`artifacts/experiments/crack_segmentation_results/` (regenerated, not committed)
(green = correct crack prediction, red = false positive, blue = missed crack pixel), spanning
the full quality range by design:

- **`best_*.png`** (3 images, IoU 0.79–0.91): near-complete overlap, minor edge disagreement only.
- **`median_*.png`** (3 images, IoU near the 0.50 mean): partial detection — real cracks found,
  but with noticeable gaps or extra false-positive pixels.
- **`worst_*.png`** (3 images, IoU 0.0–0.02): genuine failure cases. `slide1542.png` and
  `slide965.png` have real crack pixels in the ground truth (385 and 62 pixels respectively) that
  the model predicted zero crack pixels for — a complete miss, not a near-miss. `slide30.png`
  predicted only 48 pixels against 2,149 ground-truth pixels (recall 0.02) despite perfect
  precision on the few pixels it did predict — severe under-segmentation, not a false-positive
  problem.

## Why it fails on these three images (diagnosis, not just a number)

`slide1542.png` and `slide965.png` have comparatively **low ground-truth crack pixel counts**
(385 and 62, versus a few hundred to ~2,900 for images the model handles well) — thin or short
cracks are the weakest case for a 256×256-downsampled, no-pretrained-encoder segmentation model,
because a thin crack can shrink to a handful of pixels or disappear entirely at this resolution.
This is a resolution/capacity limitation, not a data-loading bug — the ground-truth masks
themselves were manually spot-checked and are correctly non-empty for both files.

## What was not done in this pass

- No hyperparameter search — this is a single baseline run, not a tuned model.
- No pretrained encoder — see `docs/model_selection.md`'s original justification (CPU-only,
  315-image dataset too small to justify an ImageNet-scale download for this MVP pass).
- No qualitative human (engineering) review of whether the failure cases represent a genuinely
  hard visual pattern versus a labeling inconsistency in the source dataset.

## Reproduce

```powershell
python -m aeris.training.train --config configs/training/crack_segmentation.yaml
python scripts/evaluate_crack_segmentation.py
```
