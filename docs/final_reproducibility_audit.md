# Final reproducibility audit

Real filesystem/git inspection, 2026-08-21. Every number below was measured this session, not
carried over from memory.

## A. Git repository

- Remote: `https://github.com/Anjaney336/drone-project.git`
- **Ownership anomaly found and flagged (not fixed via global config, per operating constraints):**
  `.git` is owned by Windows account `CodexSandboxOffline`, current user is `hp` — every git
  command fails with "dubious ownership" unless run with a transient
  `-c safe.directory=<path>` override. **You should resolve this properly** (either
  `git config --global --add safe.directory <path>` yourself, or `takeown`/`icacls` on the
  directory) — global git config is intentionally left untouched by this audit.
- One commit: `cc64271 "Initial AERIS drone project"`, 2026-08-21 01:23:59 +0530, author
  `Anjaney336 <anjaneymalhotra@gmail.com>` — 138 files.
- Working tree had one drift item this session (`scratch_pptx/`, an accidental artifact from an
  earlier unrelated task) — removed, not part of AERIS.

## B–C. Tracked vs. untracked

138 files tracked. Notably: `yolov8n.pt` (6.5 MB pretrained base weights) **is tracked**, unhashed,
no manifest entry until this pass (see Phase 13 gap below). `data/raw/**`, `artifacts/**`,
`Dataset/` are correctly git-ignored.

## D. Dataset directories (measured `du -sh`)

| Path | Size | Classification |
|---|---:|---|
| `data/raw/concrete/` (damage_detection + uav_crack) | 198 MB | TRACKED-CANDIDATE, LICENSE_RESTRICTED (unconfirmed) |
| `data/raw/agriculture/` | ~18 GB (incl. one corrupted attempt kept for reference) | DOWNLOAD_REQUIRED → now READY, TOO_LARGE_FOR_NORMAL_GIT |
| `Dataset/` | 4.3 GB | NOT_READY, quarantined, IGNORED |
| `.legacy_backup/` | 14 GB | IGNORED, quarantined (prior session) |
| `data/raw/visdrone/` | 2.0 GB | NOT_TRACKED, not wired into any active pipeline |

## E. Model checkpoints

| Checkpoint | Size | Git status |
|---|---:|---|
| `damage_detection_yolov8n_baseline/weights/best.pt` | 6.0 MB | NOT_TRACKED (under `artifacts/`, ignored) |
| `damage_detection_yolov8n_exp_a_imgsz640/weights/best.pt` | 6.0 MB | NOT_TRACKED |
| `crack_segmentation_tinyunet_baseline/best_model.pt` | 1.9 MB | NOT_TRACKED |
| `agriculture_uav_mobilenetv3_baseline/best_model.pt` | pending (training in progress as of this audit) | NOT_TRACKED |

All are small enough (< 10 MB) that Git LFS is not strictly required by size, but none currently
has a manifest entry recording its provenance (dataset version, config, seed) independent of the
experiment JSON — addressed in `data/manifests/models.json` (see Phase 13 note).

## F–G. Generated artifacts / experiment outputs

`artifacts/` totals 2.1 GB, dominated by Ultralytics' per-run training visualizations
(`train_batch*.jpg`, `val_batch*.jpg`, PR/F1 curve PNGs) for the two YOLO runs plus the SQLite
product database. All correctly git-ignored; none of it should be committed.

## H–J. Agriculture download / extraction

- Downloaded: **complete**, 10.47 GB final size (larger than the Mendeley page's rounded "~9.75 GB"
  — stated as observed, not corrected to match the marketing figure).
- Integrity: **verified this session** via `zipfile.testzip()` across all 10 nested archives —
  `None` returned (no bad entries). This is a genuine pass, not the false-positive "100% but
  corrupt" state seen earlier in the project.
- Extraction: outer archive extracted; **UAV subset (4 of 10 nested zips) extracted**, leaf subset
  left as nested zips (not needed — see `docs/agriculture_dataset_final_audit.md` for why).
- 2,842 UAV images across 4 classes, 0 corrupt files (Pillow-verified).

## K–L. Agriculture model code / training runs

Did not exist before this session. Now: `src/aeris/training/agriculture.py`
(MobileNetV3-Small classifier), `configs/training/agriculture_uav.yaml`,
`scripts/build_agriculture_splits.py`. A real training run was launched this session — see the
final response for its status at time of writing (do not assume it finished; check
`artifacts/experiments/agriculture_uav_mobilenetv3_baseline/status.json`).

## M. Lint

Before this pass: 107 `ruff check` errors (all in this session's own new code — line length,
import order, one unused import, one unused variable). **After: 0 errors** (`ruff check .` →
"All checks passed!"). Fixed via `ruff check --fix`, `ruff format`, `ruff check --fix --unsafe-fixes`,
and manual line-wrapping for long string literals the formatter can't safely rewrap. No directories
excluded, no rules disabled, no `noqa` added to hide anything.

## N. Test status

51/51 passing (`python -m pytest tests/ -q --basetemp=<writable dir>` — the platform's default
temp dir has a pre-existing Windows permission issue unrelated to this project, worked around with
an explicit `--basetemp`).

## O–P. Dataset licenses / provenance

See `docs/datasets/available_datasets.md` for the full per-dataset table. Summary: agriculture
license **confirmed** (CC BY 4.0, Mendeley DOI); both infrastructure datasets' licenses remain
**unconfirmed** — this is stated everywhere they're referenced, and neither is committed to git in
full because of it.
