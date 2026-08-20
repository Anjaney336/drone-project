"""Publish a finished training run so a clone of this repository can use it.

`python -m aeris.training.train` writes to `artifacts/experiments/<name>/`, which is
gitignored because it also fills up with logs, plots and intermediate epochs. That is
the right home for a raw run, but it means a fresh clone has no checkpoint at all and
every model reports NOT_TRAINED.

This script copies the two things that actually matter — the status file and the
checkpoint — into `models/<name>/`, which IS tracked. Commit that directory and the
model works for anyone who clones the repository.

    python scripts/publish_model.py damage_detection_yolov8n_baseline
    python scripts/publish_model.py crack_segmentation_tinyunet_baseline
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINING_RUNS_ROOT = ROOT / "artifacts" / "experiments"
MODELS_ROOT = ROOT / "models"

# Relative to the run directory. The first one that exists is the checkpoint.
CHECKPOINT_CANDIDATES = (Path("weights") / "best.pt", Path("best_model.pt"))


def publish(experiment_name: str) -> Path:
    run_dir = TRAINING_RUNS_ROOT / experiment_name
    status_file = run_dir / "status.json"
    if not status_file.exists():
        raise SystemExit(
            f"No training run found at {run_dir}. Train the model first:\n"
            f"  python -m aeris.training.train --config configs/training/<config>.yaml"
        )

    status = json.loads(status_file.read_text(encoding="utf-8"))
    if status.get("status") != "READY":
        raise SystemExit(
            f"Refusing to publish {experiment_name}: its status is "
            f"{status.get('status')!r}, not READY. Only a completed run is publishable."
        )

    checkpoint = next((run_dir / c for c in CHECKPOINT_CANDIDATES if (run_dir / c).exists()), None)
    if checkpoint is None:
        tried = ", ".join(str(c) for c in CHECKPOINT_CANDIDATES)
        raise SystemExit(f"Run {experiment_name} is READY but has no checkpoint (tried: {tried}).")

    destination = MODELS_ROOT / experiment_name
    destination.mkdir(parents=True, exist_ok=True)
    relative = checkpoint.relative_to(run_dir)
    (destination / relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint, destination / relative)
    shutil.copy2(status_file, destination / "status.json")

    size_mb = checkpoint.stat().st_size / (1024 * 1024)
    print(f"Published {experiment_name} -> {destination.relative_to(ROOT)}")
    print(f"  checkpoint: {relative} ({size_mb:.1f} MB)")
    print(f"  status:     {status.get('status')}")
    print("\nCommit this directory so the model ships with the repository:")
    print(f"  git add {destination.relative_to(ROOT)} && git commit")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiment_name", help="Experiment name from the training config")
    publish(parser.parse_args().experiment_name)


if __name__ == "__main__":
    main()
