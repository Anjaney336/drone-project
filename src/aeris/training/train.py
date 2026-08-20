"""Config-driven training CLI: python -m aeris.training.train --config <path>.

Supports object_detection (Ultralytics YOLO) task configs today. Fails loudly on
unsupported task types rather than silently doing nothing.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]


def _write_status(run_dir: Path, status: str, **extra) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat(), **extra}
    (run_dir / "status.json").write_text(json.dumps(payload, indent=2))


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def run_object_detection(cfg: dict, run_dir: Path) -> dict:
    from ultralytics import YOLO

    set_seed(cfg["seed"])
    model = YOLO(cfg["model"]["pretrained_weights"])
    data_yaml = str(ROOT / cfg["data_config"])
    t = cfg["training"]
    results = model.train(
        data=data_yaml,
        epochs=t["epochs"],
        batch=t["batch_size"],
        imgsz=cfg["model"]["input_size"],
        device=t["device"],
        seed=cfg["seed"],
        patience=t["early_stopping_patience"],
        project=str(run_dir.parent),
        name=run_dir.name,
        exist_ok=True,
        verbose=True,
    )
    metrics = model.val(data=data_yaml, split="test")
    return {
        "task_type": "object_detection",
        "final_metrics": {
            "mAP50": float(metrics.box.map50) if metrics.box is not None else None,
            "mAP50_95": float(metrics.box.map) if metrics.box is not None else None,
            "precision": float(metrics.box.mp) if metrics.box is not None else None,
            "recall": float(metrics.box.mr) if metrics.box is not None else None,
        },
        "checkpoint_path": str(run_dir / "weights" / "best.pt"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text())
    run_dir = ROOT / cfg["output"]["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_status(run_dir, "TRAINING", experiment_name=cfg["experiment_name"])
    started = time.monotonic()
    try:
        if cfg["task_type"] == "object_detection":
            result = run_object_detection(cfg, run_dir)
        elif cfg["task_type"] == "semantic_segmentation_binary":
            from aeris.training.segmentation import run_segmentation

            result = run_segmentation(cfg, run_dir)
        else:
            raise SystemExit(f"Unsupported task_type: {cfg['task_type']}")
    except Exception as exc:  # noqa: BLE001 - deliberately broad: this is a top-level CLI status gate
        _write_status(run_dir, "UNAVAILABLE", experiment_name=cfg["experiment_name"], error=str(exc))
        raise
    elapsed_s = round(time.monotonic() - started, 1)

    experiment_record = {
        "experiment_name": cfg["experiment_name"],
        "config_path": str(cfg_path),
        "dataset": cfg["data_config"],
        "seed": cfg["seed"],
        "hyperparameters": cfg["training"],
        "hardware": "CPU (no CUDA device detected in this environment)",
        "elapsed_seconds": elapsed_s,
        **result,
    }
    out = ROOT / "artifacts" / "experiments" / f"{cfg['experiment_name']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(experiment_record, indent=2))
    _write_status(
        run_dir,
        "READY",
        experiment_name=cfg["experiment_name"],
        checkpoint_path=result.get("checkpoint_path"),
        elapsed_seconds=elapsed_s,
    )
    print(json.dumps(experiment_record, indent=2))


if __name__ == "__main__":
    main()
