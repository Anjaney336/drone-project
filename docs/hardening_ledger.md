# Hardening ledger

One row per finding. `Status` is only ever set to `FIXED` after a real verification command was
run and its output inspected.

| ID | Severity | Symptom | Root cause | Fix | Verification command | Status |
|---|---|---|---|---|---|---|
| P0-1 | Critical | `requirements.lock` had no torch/ultralytics/opencv/python-multipart despite the app depending on all four | Lock generated pre-ML, never regenerated | Rebuilt `pyproject.toml` deps + regenerated `requirements.lock` from a fresh, isolated venv with a pinned CPU-only torch extra-index-url | `python -m venv /tmp/aeris_cleanroom_venv` → `pip install --extra-index-url https://download.pytorch.org/whl/cpu -e ".[dev]"` → `pytest -q` (51/51 passed) → direct `model_registry` inference call (4 real predictions returned) → `pip install -r requirements.lock` in the same venv (no changes, confirms the lock matches) | **FIXED, verified in a clean venv** |
| P0-4 | Critical | Root `README.md` stated "does not contain an evaluated infrastructure-defect model" | Never touched during this session's ML/product work | Rewrote README with real current metrics, the actual upload→analyze workflow, and corrected install command | Manual read-through against `artifacts/experiments/*.json` | **FIXED** |
| P0-5 | High | README/Dockerfile/`.env.example` disagreed on port (8501 vs 8000) | Written at different times | Standardized on 8501 everywhere | `grep -rn "8000" README.md Dockerfile .env.example` returns nothing | **FIXED** |
| P0-6 | Medium | No `.dockerignore`; `COPY . .`; root user; no healthcheck | Dockerfile predated this session | Added `.dockerignore`, scoped `COPY` to `src/` only, non-root `USER aeris`, `HEALTHCHECK` against the real `/api/v1/health` endpoint | Manual review only — **no Docker binary available in this environment**, so the image was not build-tested. Stated as a real gap, not silently claimed fixed. | **EDITED, NOT BUILD-VERIFIED** |
| P0-7 | Medium | Light-field `Dataset/` not actually gitignored despite being documented as quarantined | `.gitignore` predated this dataset | Added `Dataset/` to `.gitignore` | `git check-ignore -v Dataset/` and `Dataset/LF-1-100img-0-colorimg.npy` both confirm ignored | **FIXED** |
| P0-3 | Medium | `yolov8n.pt` at repo root, unhashed, no manifest | Ultralytics' default download location | **Not done this pass** — deprioritized in favor of the user-workflow redirect and the higher-severity P0s | — | **NOT DONE, deferred and stated** |
| P0-2 | High (needs human decision) | MIT `LICENSE` vs AGPL-3.0 `ultralytics`/YOLOv8 weights | Never audited before this pass | **Documented, not executed** — this changes the project's legal posture and explicitly requires a human decision per the directive itself | — | **DOCUMENTED ONLY, awaiting your decision** — see note below |
| — | — | Agriculture archive reached 100% download but failed real integrity verification (`Bad magic number for file header` on read, not just central-directory check) | Corruption introduced across this session's multiple pause/resume cycles on the same partial file | Moved corrupted file aside (`.corrupt_2026-08-20` suffix, not deleted), restarted a single uninterrupted fresh download | `zipfile.ZipFile(...).open(name).read()` on the flagged entry raised `BadZipFile`; re-download in progress, untouched since restart | **IN PROGRESS** |
| — | Real, measured improvement | YOLO `imgsz=640` experiment (the one diagnosed, single-variable experiment from the prior phase) finished mid-session | — | mAP50 0.440→0.467, mAP50-95 0.258→0.270, precision 0.448→0.486, recall 0.496→0.480 (down), training time 35min→84min | `docs/yolo_baseline_diagnosis.md` comparison table | **MEASURED, checkpoint swap deliberately deferred** |

## P0-2 note (not executed — needs your decision)

MIT (`LICENSE`) contradicts AGPL-3.0 (Ultralytics/YOLOv8 + its pretrained weights, which
`configs/training/*.yaml` reference and this session's inference depends on). Three real options,
already outlined in the original directive: relicense AERIS AGPL-3.0 (simplest, fully honest,
free); replace the detector with a permissively-licensed alternative and retrain (real cost, real
schedule risk this close to hardening); or keep MIT for AERIS's own code with a precisely-defined,
separately-licensed AGPL component boundary. I did not choose for you — this is a legal/business
call the directive itself says needs a human, not an agent, to confirm.

## CI, security hardening, and remaining Phase-2–5 items from the original directive

**Not started this pass.** After the P0 fixes above, the user issued an explicit redirect: stop
extending backend/infra hardening and rebuild the primary user-facing workflow (upload → real
analysis → results) instead, since that was assessed as the higher-priority gap. That redirect was
followed — see the separate final report for what was built. GitHub Actions CI, `SECURITY.md`,
magic-byte upload sniffing, and the model-card/calibration work from the original directive's Phase
2/5 remain genuinely not done, stated here rather than silently dropped.
