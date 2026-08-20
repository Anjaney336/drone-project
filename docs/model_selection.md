# Model selection

Model choice follows annotation format, not novelty. Each dataset's label type determines the
task formulation before any architecture is picked (see `docs/dataset_audit.md` and
`docs/dataset.md` for the underlying audits).

## 1. Damage Detection (concrete/structural) → object detection

- **Annotation format found:** image + bounding box (YOLO `.txt`, duplicated as Pascal-VOC-style
  JSON) → this is an object detection problem, not classification or segmentation.
- **Candidates considered:** YOLOv8n/s, YOLOv10n, Faster R-CNN (ResNet backbone).
- **Selected baseline:** **YOLOv8n** (nano), via the already-installed `ultralytics` package.
  Faster R-CNN was rejected for this prototype: it is materially slower to train on CPU (no GPU
  is available in this environment — `torch.cuda.is_available()` returns `False`) for a dataset
  this size, and a nano single-stage detector is a defensible, fast baseline for a hackathon
  prototype rather than an accuracy ceiling.
- **Input size:** 416×416 (reduced from YOLO's typical 640 to keep CPU epoch time tractable).
- **Augmentation:** horizontal flip, HSV jitter, mosaic — training split only, disabled for
  val/test (`configs/training/damage_detection.yaml`).
- **Loss:** Ultralytics' default detection loss (box + classification + DFL).
- **Metrics:** mAP50, mAP50-95, precision, recall, computed on the held-out test split.
- **Known limitations:** class ids `0`/`1` are **anonymous** — no `classes.txt` or README shipped
  with the raw folder, so semantic names (e.g. "crack" vs. "spall") are not asserted anywhere in
  code or docs. Severe class imbalance (~55:1) is not corrected in this baseline (no
  oversampling/focal loss) and is recorded as a limitation, not silently ignored.

## 2. UAV-based crack dataset → binary semantic segmentation

- **Annotation format found:** image + pixel mask (binary) → segmentation, not detection or
  classification. Converting this to a classification problem (image-level "has crack" label)
  would discard the localization signal the masks provide, so it was not done.
- **Candidates considered:** U-Net, DeepLabV3+, SegFormer.
- **Selected baseline:** a **small custom U-Net** (`src/aeris/training/segmentation.py`,
  `TinyUNet`, base width 16 channels, 3 encoder/decoder stages). DeepLabV3+/SegFormer were
  rejected for this pass: they are heavier to train from scratch on CPU with only 315 total
  images (220 train), and pretrained-backbone variants would need an ImageNet-scale download this
  environment cannot justify for a single-class 315-image baseline.
- **Input size:** downsampled to 256×256 to keep CPU epoch time tractable.
- **Augmentation:** horizontal flip only, training split only.
- **Loss:** binary cross-entropy on logits.
- **Metrics:** mean IoU, mean Dice, on the held-out test split; training/validation loss curve
  logged per epoch for early-stopping evidence.
- **Known limitations:** 315 images is a small dataset for segmentation from scratch; no
  pretrained encoder is used, so results should be read as a baseline reference point, not a
  production-grade crack detector. Class balance was only sampled, not exhaustively verified
  (see `docs/dataset_audit.md`).

## 3. Agriculture (MH-SoyaHealthVision) → image classification

- **Annotation format:** folder-per-class (no bounding boxes or masks — each image's label is
  implicit in its parent directory: e.g. `healthy/`, `rust/`, `mosaic_virus/`, `pest_attack/` for
  the UAV split, plus four additional disease folders for the ground-level leaf split) → this is
  an image classification problem.
- **Candidates considered:** EfficientNet-B0, MobileNetV3, ResNet18.
- **Selected baseline:** **MobileNetV3-Small** (ImageNet-pretrained, fine-tuned), chosen over
  EfficientNet-B0 for lower CPU inference/training cost at prototype scale, and over ResNet18 for
  a smaller parameter count given no GPU is available. This decision is provisional pending full
  inspection of the extracted folder structure once the 9.75 GB download completes — see
  `docs/dataset.md` for the acquisition record and any structural corrections.
- **Input size / augmentation / loss / metrics:** to be finalized against the actual class list
  once extracted; will follow the same pattern as the infrastructure baselines (train-only
  augmentation, accuracy/precision/recall/F1/per-class + confusion matrix, fixed seed 20260820).

## Cross-cutting decisions

- **No shared multi-domain model.** Per the audit, infrastructure defects (concrete cracks/damage)
  and crop disease/pest patterns are not the same visual or semantic problem; they are trained as
  separate models with separate heads, not forced into one classifier.
- **Fixed seed 20260820** (the pivot date) is used across all dataset splits and training runs for
  reproducibility.
- **CPU-only hardware** (`torch==2.5.1+cpu`, no CUDA device) is the binding constraint on epoch
  count, image resolution, and architecture size across all three baselines. This is stated
  explicitly rather than silently producing a slow or incomplete run.
