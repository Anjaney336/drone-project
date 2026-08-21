"""Run the trained crack-segmentation baseline over normalized NumPy RGB arrays.

This runner produces exploratory inference only. The input folder has no labels or
source documentation, so its output cannot be used as model-accuracy evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

from aeris.training.segmentation import TinyUNet

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "artifacts" / "experiments" / "crack_segmentation_tinyunet_baseline"
CHECKPOINT = RUN_DIR / "best_model.pt"
STATUS_FILE = RUN_DIR / "status.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "npy_crack_inference.json",
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--signal-area-threshold", type=float, default=0.001)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise ValueError("--batch-size must be positive")
    if not STATUS_FILE.exists() or json.loads(STATUS_FILE.read_text())["status"] != "READY":
        raise RuntimeError("Crack-segmentation model is not READY")
    if not CHECKPOINT.exists():
        raise FileNotFoundError(CHECKPOINT)

    files = sorted(args.input_dir.glob("*.npy"))
    if not files:
        raise RuntimeError(f"No .npy files found in {args.input_dir}")

    model = TinyUNet(base=16)
    model.load_state_dict(torch.load(CHECKPOINT, map_location="cpu", weights_only=True))
    model.eval()

    dataset_digest = hashlib.sha256()
    records: list[dict] = []
    groups: Counter[str] = Counter()
    started_at = datetime.now(timezone.utc)

    with torch.inference_mode():
        for offset in range(0, len(files), args.batch_size):
            batch_files = files[offset : offset + args.batch_size]
            arrays: list[np.ndarray] = []
            for path in batch_files:
                array = np.load(path, allow_pickle=False)
                if array.shape != (256, 256, 3):
                    raise ValueError(f"{path.name}: expected (256, 256, 3), got {array.shape}")
                if not np.issubdtype(array.dtype, np.floating):
                    raise ValueError(f"{path.name}: expected floating dtype, got {array.dtype}")
                if not np.isfinite(array).all() or array.min() < 0 or array.max() > 1:
                    raise ValueError(f"{path.name}: expected finite values in [0, 1]")
                dataset_digest.update(path.name.encode("utf-8"))
                dataset_digest.update(array.tobytes(order="C"))
                arrays.append(array.astype(np.float32, copy=False))
                groups[path.name.split("-")[0]] += 1

            tensor = torch.from_numpy(np.stack(arrays)).permute(0, 3, 1, 2)
            probabilities = torch.sigmoid(model(tensor))[:, 0]
            masks = probabilities > args.threshold

            for path, probability, mask in zip(batch_files, probabilities, masks, strict=True):
                affected_fraction = float(mask.float().mean().item())
                mean_signal_probability = (
                    float(probability[mask].mean().item()) if mask.any() else None
                )
                records.append(
                    {
                        "file": path.name,
                        "group": path.name.split("-")[0],
                        "result": (
                            "exploratory_possible_crack_signal"
                            if affected_fraction >= args.signal_area_threshold
                            else "no_signal_above_area_threshold"
                        ),
                        "affected_area_fraction": round(affected_fraction, 6),
                        "mean_signal_probability": (
                            round(mean_signal_probability, 6)
                            if mean_signal_probability is not None
                            else None
                        ),
                    }
                )

            completed = min(offset + args.batch_size, len(files))
            if completed % 200 < args.batch_size or completed == len(files):
                print(f"processed {completed}/{len(files)}", flush=True)

    result_counts = Counter(record["result"] for record in records)
    finished_at = datetime.now(timezone.utc)
    artifact = {
        "artifact_type": "exploratory_out_of_domain_inference",
        "warning": (
            "The source dataset has no labels, manifest, or domain documentation. "
            "These outputs are model signals only and are not defect diagnoses, "
            "accuracy evidence, or field validation."
        ),
        "input": {
            "directory": str(args.input_dir.resolve()),
            "file_count": len(files),
            "groups": dict(sorted(groups.items())),
            "shape": [256, 256, 3],
            "dataset_content_sha256": dataset_digest.hexdigest(),
        },
        "model": {
            "name": "crack_segmentation_tinyunet_baseline",
            "version": "baseline-1",
            "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
            "checkpoint_sha256": sha256_file(CHECKPOINT),
            "status": "READY",
        },
        "configuration": {
            "probability_threshold": args.threshold,
            "signal_area_threshold": args.signal_area_threshold,
            "batch_size": args.batch_size,
            "device": "cpu",
        },
        "run": {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": round((finished_at - started_at).total_seconds(), 3),
        },
        "summary": dict(sorted(result_counts.items())),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
