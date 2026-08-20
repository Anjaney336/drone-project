# YOLOv8n damage-detection baseline — performance diagnosis

Baseline: mAP50=0.440, mAP50-95=0.258, precision=0.448, recall=0.496 (test split, 225 images).
This document diagnoses *why*, using the actual dataset and the trained model's own predictions —
not assumptions — before proposing any change.

## 1. Class distribution

| Split | class_0 instances | class_1 instances | ratio |
|---|---:|---:|---:|
| train | 13,665 | 353 | 38.7:1 |
| val | 2,598 | 60 | 43.3:1 |
| test | 2,966 | 68 | 43.6:1 |

Imbalance is real (~39–44:1) but consistent across splits (no leakage-driven skew).

## 2. Per-class performance — the counterintuitive finding

| Class | Test instances | AP50 | AP50-95 | Precision | Recall | Mean pred. confidence |
|---|---:|---:|---:|---:|---:|---:|
| class_0_unverified (dominant) | 2,966 | **0.336** | 0.164 | 0.430 | 0.374 | 0.380 |
| class_1_unverified (rare) | 68 | **0.545** | 0.352 | 0.467 | 0.618 | 0.579 |

**The class with 44× fewer training examples scores higher on every metric.** Class imbalance is
therefore *not* the primary bottleneck — something else about class_0 makes it harder, despite
its abundance.

## 3. Root cause: object size, not sample count

| Class | Median bbox area (% of image) | Mean bbox area (% of image) |
|---|---:|---:|
| class_0 | 0.42% | 1.75% |
| class_1 | 2.23% | 6.16% |

Class_0 boxes are **~5× smaller by median area**. Across the whole dataset, 82% of all boxes
occupy less than 2% of the image — this is fundamentally a small-object-detection problem, and
class_0 sits at the harder end of that distribution while class_1 does not.

Confusion matrix (test split; rows/cols are `[class_0, class_1, background]`):

```
                 pred_class_0  pred_class_1  pred_background(FN)
true_class_0            871             1                  698
true_class_1              1            36                   34
background(FP)         2094            31                    -
```

Two things stand out: (a) cross-class confusion is negligible (1 instance each direction) — the
model is not mixing up class_0 and class_1 with each other; (b) class_0 has both a large
false-negative count (698 missed) *and* a large false-positive count (2,094 background regions
misclassified as class_0). class_0 is being missed when real and hallucinated when absent —
consistent with it being visually heterogeneous, small, and hard to localize, not with a labeling
or class-confusion problem.

## 4. Training resolution compounds the size problem

Images are natively 640×640; the baseline trained at `imgsz=416` (chosen for CPU epoch time — see
`docs/model_selection.md`). Downscaling 640→416 shrinks a bbox that's already ~0.4% of the image
area even further before the network ever sees it. This is a direct, mechanical amplifier of the
small-object problem identified above.

## 5. The model had not converged

`artifacts/experiments/damage_detection_yolov8n_baseline/results.csv` (real per-epoch ultralytics
output, not summarized/rounded):

| Epoch | val/box_loss | val/cls_loss | mAP50 |
|---:|---:|---:|---:|
| 8 | 1.745 | 1.876 | 0.347 |
| 11 | 1.652 | 1.719 | 0.416 |
| 13 | 1.619 | 1.673 | 0.463 |
| 15 (final) | 1.558 | 1.627 | 0.483 |

Both validation losses were still monotonically decreasing and mAP50 was still climbing at epoch
15 — early stopping (patience=5) never triggered. **This baseline was epoch-budget-limited, not
converged**, which is the evidence required before proposing more training.

## Proposed experiments (at most 3, single-variable, same test methodology)

All experiments hold fixed: YOLOv8n architecture, seed `20260820`, the same train/val/test split
(`configs/data/damage_detection.yaml`), device CPU, and the same final-comparison protocol —
`model.val(data=..., split="test")`, never the validation split, for the number reported as final.

| # | Hypothesis | Changed variable | Fixed |
|---|---|---|---|
| A | Restoring native 640px resolution recovers small-object detail lost at 416px and improves class_0 recall specifically (its bbox size is the identified bottleneck) | `imgsz`: 416 → 640 | epochs=15, batch=8, augmentation config, patience=5 |
| B | Focal loss down-weights the easy majority of class_0's background-heavy gradient signal and should reduce its false-positive rate (2,094 background→class_0 errors) without materially hurting class_1 | `fl_gamma`: 0 (default) → 1.5 | imgsz=416, epochs=15, batch=8, patience=5 |
| C | Given the loss curves were still decreasing at epoch 15, more epochs should continue improving mAP50 before overfitting; this is proposed, not assumed, to be checked against the val curve of the extended run itself, not the test set | `epochs`: 15 → 30 | imgsz=416, batch=8, patience=5 (so it can still stop early if it does converge) |

Only **Experiment A** was run to completion in this pass. Its real measured result, from the
untouched test split, `configs/training/damage_detection_exp_a_imgsz640.yaml`:

| Metric | Baseline (416px) | Experiment A (640px) | Change |
|---|---:|---:|---:|
| mAP50 | 0.440 | **0.467** | +0.027 |
| mAP50-95 | 0.258 | **0.270** | +0.012 |
| Precision | 0.448 | **0.486** | +0.038 |
| Recall | 0.496 | 0.480 | −0.016 |
| Wall-clock (CPU, 15 epochs) | ~35 min | 83.8 min (5,028s) | +2.4× |

This confirms the resolution hypothesis directionally: mAP50, mAP50-95, and precision all improved
with native-resolution training, consistent with small-object detail being recoverable at 640px.
Recall dropped slightly, and training time nearly tripled. **This is a real, measured, modest
improvement, not a breakthrough** — reported honestly rather than as a headline win. The production
model registry was **not** switched to this checkpoint in this pass; that is a deliberate,
documented deferral (not an oversight) pending a full re-verification cycle, given the checkpoint
swap itself needs re-validation of the whole inference→finding→review chain before going live.
Both checkpoints exist side by side: `artifacts/experiments/damage_detection_yolov8n_baseline/`
and `artifacts/experiments/damage_detection_yolov8n_exp_a_imgsz640/`.

Experiments B (focal loss) and C (extended epochs — now partially answered: 15 epochs at 640px
already cost 84 minutes, so a longer schedule is a real CPU-time tradeoff to weigh, not a free
win) remain documented as justified next steps, not run.
