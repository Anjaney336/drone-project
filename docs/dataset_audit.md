# Dataset audit — newly added infrastructure imagery

Generated 2026-08-20 by `scripts/dataset_audit.py` (see `artifacts/dataset_audit.json` /
`artifacts/dataset_audit.csv` for machine-readable output). This audit covers the three raw
folders added to the repository root just before this pivot. Datasets already catalogued
(AERIS demonstration set, VisDrone candidate, Anti-UAV300 candidate, EuRoC candidate, AERIS
synthetic sensor/fault data) remain documented in [`docs/dataset.md`](dataset.md) and are not
repeated here.

## 1. Damage Detection (concrete/structural defects)

| Field | Value |
|---|---|
| Directory | `Damage Detection/` |
| Domain | Infrastructure |
| Images | 1,500 (`.jpg`) |
| Annotations | 1,500 YOLO `.txt` + 1,500 Pascal-VOC-style `.json` (same boxes, two formats) |
| Format | Bounding box |
| Classes | Two anonymous ids, **0** and **1** — no `classes.txt`/README ships with the data, so semantic names (e.g. "crack" vs "spall") are **not assumed** |
| Class distribution | id `0`: 17,889 instances; id `1`: 325 instances → ~55:1 imbalance |
| Image dimensions | 640×640 uniform |
| Missing annotations | 0 |
| Corrupted files | 0 |
| Existing split | **None** — flat directory |
| Leakage risk | N/A until a split is created |
| Disk usage | ~192 MB |

**Action required before training:** class names must be verified by a human (dataset likely
originates from a public Kaggle "bridge/concrete damage" release, but provenance metadata was not
retained on download) and a train/val/test split must be created with a fixed seed, grouped so no
duplicate/near-duplicate frame leaks across splits.

## 2. UAV-based crack dataset (segmentation)

| Field | Value |
|---|---|
| Directory | `UAV-based crack dataset used for segmentation/` |
| Domain | Infrastructure |
| Images | 315 (`.png`, DJI drone filenames) |
| Annotations | 315 binary pixel masks (`.png`, filename-matched) |
| Format | Segmentation mask |
| Classes | Binary: crack pixel vs background |
| Missing masks | 0 |
| Corrupted files | 0 |
| Existing split | **None** — flat directory |
| Disk usage | ~19 MB |

DJI filenames indicate genuine UAV-captured pavement/structure imagery, which fits the "concrete"
inspection use case directly. Pixel-level class balance was sampled (first 50 masks) rather than
fully scanned, for time; a full scan should precede final model training.

## 3. `Dataset/` — unlabeled light-field imagery

**Status: UNLABELED / NOT CURRENTLY USED.** The active infrastructure MVP has **two** validated
supervised datasets (Damage Detection, UAV crack segmentation), not three. This folder is not
counted as a third dataset and does not contribute to any trained model or reported metric.

| Field | Value |
|---|---|
| Directory | `Dataset/` |
| Files | 2,902 `.npy` arrays, shape `(256,256,3)` float64, values in `[0,1]` |
| Annotations | None |
| Documentation | None — no README, manifest, or class file |
| Disk usage | ~4.4 GB |

Filename prefixes (`LF-`, `TL-`) and the `colorimg` suffix suggest light-field/plenoptic camera
captures, but nothing in the folder indicates whether this is infrastructure or agriculture data,
or what task it supports. Per the instruction not to force unrelated data into a fabricated task,
**this dataset is excluded from the active AERIS pipeline.** It is left in place, untouched,
pending the user clarifying its source and intended use — it is not deleted because its origin is
unknown and deletion would be irreversible.

## Audit limitations

- Near-duplicate detection (perceptual hashing) was not run — only exact-content hash prefixes —
  because a full perceptual-hash pass over 1,500+ images was judged not worth the CPU time for
  this audit pass; flat SHA-256-prefix duplicates were checked and none were found in Damage
  Detection.
- Pixel-level class balance for the crack segmentation masks was sampled, not exhaustive.
- Class semantics for Damage Detection ids `0`/`1` are unverified and must not be treated as
  ground truth defect names until a human confirms them against the original source.
