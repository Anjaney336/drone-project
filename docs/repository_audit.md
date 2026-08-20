# Repository audit and migration record

The pre-rebuild workspace contained 131,250 files. Only 351 were version-controlled; the remainder included a virtual environment, Git objects, generated outputs, caches, packaged AirSim binaries, model weights, and local dataset copies.

## Classification and disposition

| Original group | Purpose/dependencies | Class | Active reference | Disposition/replacement |
|---|---|---|---|---|
| `src/drone_interceptor/**` | coupled interception/day-numbered stack | prototype/obsolete | legacy scripts/tests | removed from active tree; replaced by `src/aeris/**` |
| patch/debug root scripts | string patching and machine-local debugging | patch/debug | none | deleted; recoverable from Git |
| `tests/test_day*`, interception/spoof tests | validate obsolete architecture | obsolete tests | old package | removed; replaced by focused AERIS tests |
| `results`, `outputs`, `runs`, `logs`, `tmp_outputs` | generated plots, CSV, videos, registries | generated artifacts | stale docs | quarantined locally; reproducible outputs now use `artifacts/` |
| `notebooks` and day notes | progression experiments | experiment/documentation | obsolete validation modules | quarantined locally |
| `Blocks` | packaged AirSim/Unreal environment | external binary artifact | incomplete AirSim adapter | quarantined; deterministic Python is primary simulator |
| `datasets/samples` and converted `data` | samples and converted copies | dataset/generated | old YOLO scripts | quarantined; raw VisDrone retained and manifest added |
| top-level VisDrone directories | public perception benchmark | external dataset | no active model runtime | retained at `data/raw/visdrone` for perception only |
| `.venv`, caches, `__pycache__` | local/generated | cache | Python tooling | ignored; caches removed after validation |
| old backend/implementation reports | unsupported production/performance claims | documentation | none | quarantined; replaced by evidence-based docs |
| `yolov10*.pt`, `models/**` | unmanifested weights/training outputs | model/generated | old detector scripts | quarantined; no trained model claim retained |

`.legacy_backup` is intentionally ignored and is not part of the active repository. It preserves assets that the execution environment would not allow to be irreversibly deleted without a separate explicit approval. `scripts/audit_repository.py` can emit a per-file CSV containing purpose/class/reference/deletion/replacement fields for the active tree and quarantine.
