# Available datasets — governed inventory

This is the repository's authoritative dataset register. It records what is available
locally, what is safe to publish, what contributes to a reported model, and how to
reproduce the associated checks. The register is deliberately conservative: an
unverified source or license is never treated as redistributable.

## Status vocabulary

| Status | Meaning |
|---|---|
| `ACTIVE` | Used by a current training/evaluation path and backed by a manifest. |
| `SAMPLE_ONLY` | Only a small, deterministic sample is committed for demos/tests. |
| `DOWNLOAD_ONLY` | Reproducible acquisition is documented, but the full data is too large for GitHub. |
| `CANDIDATE` | Considered for future adapters; excluded from current metrics. |
| `QUARANTINED` | Present locally but provenance, labels, or licensing are insufficient for use or publication. |

## Repository data policy

- Raw datasets are excluded by `.gitignore`; manifests, checksums, scripts, and small
  samples are the reviewable source of truth.
- Every active dataset has a machine-readable manifest under `data/manifests/` and a
  deterministic preparation/verification command.
- Reported metrics are split-aware and must not be inferred from the samples committed
  in `data/samples/`.
- Dataset origin and license are separate fields. “Publicly found” does not mean
  “redistributable.”

## A. Damage Detection (infrastructure)

**Status: `ACTIVE` + `SAMPLE_ONLY`**

| Field | Value |
|---|---|
| Local path | `data/raw/concrete/damage_detection/` |
| Files | 3,000 (1,500 images + 1,500 YOLO labels; a duplicate Pascal-VOC-JSON copy also exists on disk) |
| Images | 1,500, uniform 640×640 JPEG |
| Annotation | YOLO bbox `.txt` |
| Task | Object detection |
| Domain | Infrastructure (concrete defects) |
| Size | 118 MB |
| Source | **Unverified** — acquired as a raw folder with no README/classes.txt/LICENSE |
| License | **UNCONFIRMED** |
| Redistribution allowed | **Unknown — do not assume yes** |
| Suitable for GitHub | Small enough by size, but blocked on license confirmation for the full set; a 15-image deterministic sample is included instead (`data/samples/damage_detection/`) |
| Currently used | Yes — trains `damage_detection_yolov8n_baseline` (READY) |
| Preprocessing | Deterministic 70/15/15 split by `scripts/build_infrastructure_splits.py`, seed 20260820 |
| Manifests | `data/manifests/damage_detection_manifest.json` (per-file splits) + `damage_detection_manifest_v2.json` (fingerprint/status) |
| Integrity | Verified this session — file counts match, 25-file checksum spot-check passed, no cross-split leakage |

## B. UAV crack segmentation (infrastructure)

**Status: `ACTIVE` + `SAMPLE_ONLY`**

| Field | Value |
|---|---|
| Local path | `data/raw/concrete/uav_crack_segmentation/` |
| Files | 630 (315 images + 315 masks) |
| Images | 315 PNG, DJI-filenamed (real UAV capture) |
| Annotation | Binary pixel mask |
| Task | Semantic segmentation |
| Domain | Infrastructure (pavement/structure cracks) |
| Size | 80 MB |
| Source | **Unverified** — same acquisition gap as above |
| License | **UNCONFIRMED** |
| Redistribution allowed | **Unknown — do not assume yes** |
| Suitable for GitHub | Same as above — 15-file sample included, full set not committed |
| Currently used | Yes — trains `crack_segmentation_tinyunet_baseline` (READY) |
| Preprocessing | Deterministic 70/15/15 split, seed 20260820 |
| Manifests | `data/manifests/uav_crack_segmentation_manifest.json` + `_v2.json` |
| Integrity | Verified this session — same checks, all passed |

## C. MH-SoyaHealthVision (agriculture)

**Status: `ACTIVE` + `DOWNLOAD_ONLY`**

| Field | Value |
|---|---|
| Local path | `data/raw/agriculture/mh_soyahealthvision.zip` (archive) + `data/raw/agriculture/uav/` (extracted UAV subset) |
| Files | 5,624 total in archive (2,782 leaf + 2,842 UAV); **only the UAV subset extracted and used** |
| Task | Image classification |
| Domain | Agriculture (soybean crop health) |
| Size | ~9.75 GB archive |
| Source | Mendeley Data, DOI `10.17632/hkbgh5s3b7.1` — **verified** |
| License | **CC BY 4.0 — confirmed** |
| Redistribution allowed | Yes, with attribution |
| Suitable for GitHub | Full archive: no (too large). A manifest + automated download script is the correct strategy; extraction/training outputs stay local |
| Currently used | Yes — trains `agriculture_uav_mobilenetv3_baseline` (see `docs/agriculture_model_selection.md`) |
| Preprocessing | Group-aware split by flight session (`scripts/build_agriculture_splits.py`), seed 20260820 |
| Manifests | `data/manifests/agriculture_uav_manifest.json` + `agriculture_manifest_v2.json` |
| Integrity | **Verified this session** — full CRC check via `zipfile.testzip()` on all 10 nested archives, `None` (no bad entries) |

## D. Light-field `.npy` files (unlabeled, quarantined)

**Status: `QUARANTINED`**

| Field | Value |
|---|---|
| Local path | `Dataset/` (repo root) |
| Files | 2,902 `.npy` arrays |
| Shape/dtype | `(256, 256, 3)`, float64, values in `[0,1]` |
| Annotation | None |
| Task | Unknown |
| Domain | Unknown |
| Size | ~4.4 GB |
| Source | **Unknown** — no README, manifest, or metadata found anywhere in or near the folder |
| License | Unknown |
| Redistribution allowed | No — origin unconfirmed |
| Suitable for GitHub | No |
| Currently used | **No** — explicitly excluded from every training pipeline |
| Status | **QUARANTINED.** `.gitignore`-excluded. Re-investigated this session (filename prefixes `LF-`, `TL-`, `XS-`; still no metadata found anywhere). Not deleted — kept pending someone confirming its origin. |

## E. Additional datasets found on the filesystem (not active)

| Path | Size | Status |
|---|---:|---|
| `data/raw/visdrone/` | 2.0 GB | Present locally; public perception-benchmark candidate per `docs/dataset.md`, not wired into any active AERIS training pipeline |
| `data/raw/anti_uav/`, `data/raw/euroc/` | negligible (README only) | Candidate datasets for the Digital Twin's perception/visual-inertial adapters, not downloaded — only placeholder READMEs present |
| `.legacy_backup/` | 14 GB | Quarantined pre-rebuild snapshot from the counter-drone-era project, git-ignored, untouched |
| `data/raw/agriculture/mh_soyahealthvision.zip.corrupt_2026-08-20` | 10.7 GB | The first, corrupted download attempt — kept for reference rather than silently deleted; safe to remove once the current good copy is confirmed stable |

## Reproduction and review checklist

From the repository root:

```powershell
.venv\Scripts\python.exe scripts\verify_datasets.py
.venv\Scripts\python.exe scripts\dataset_audit.py
```

The first command checks expected counts, checksum spot checks, split leakage, archive
integrity, and model checkpoints. The second emits an audit of locally discovered raw
folders. Before publishing any new raw data, add its source URL/DOI, license evidence,
file-count manifest, SHA-256 record, and an explicit disposition to this document.

## GitHub contents

The GitHub repository contains the manifests, preparation and verification scripts,
documentation, and deterministic samples. It intentionally does **not** contain the
118 MB/80 MB unverified infrastructure corpora, the ~9.75 GB agriculture archive, the
4.4 GB unlabeled `.npy` collection, generated checkpoints under `artifacts/`, or the
legacy backup. Those exclusions are safety and licensing controls, not missing files.
