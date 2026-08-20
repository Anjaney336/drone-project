"""python scripts/build_agriculture_splits.py

Builds a deterministic, GROUP-AWARE train/val/test split for the UAV subset
of MH-SoyaHealthVision. Group-aware because most images are frames sampled
from a small number of drone flights (filename prefixes like
DJI_20231215154914_0105_D repeat across many frames of the same flight) -
a plain random per-image split would leak near-duplicate frames from the
same flight across splits and inflate test metrics. Every frame from one
flight/session goes entirely into one split.
"""

from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UAV_DIR = ROOT / "data" / "raw" / "agriculture" / "uav"
SEED = 20260820

CLASS_DIRS = {
    "healthy": UAV_DIR / "Healthy_Soyabean" / "Healthy_Soyabean",
    "rust": UAV_DIR / "Soyabean_Rust" / "rust",
    "mosaic": UAV_DIR / "Soyabean_Mosaic" / "Soyabean_Mosaic",
    "pest_attack": UAV_DIR
    / "Soyabean Semilooper and Caterpillar_Pest_Attack"
    / "Soyabean Semilooper_Pest_Attack",
}


def group_key(filename: str) -> str:
    """Flight/session id: strip the trailing frame-number+extension."""
    stem = Path(filename).stem
    m = re.match(r"^(DJI_[0-9]+_[0-9A-Za-z]+_D)_[0-9]+$", stem)
    if m:
        return m.group(1)
    m = re.match(r"^(DJI_[0-9]+)_[0-9]+$", stem)
    if m:
        return m.group(1)
    return stem  # e.g. "image_012" - no shared session marker, treat as its own group


def group_split(groups: list[str], train=0.7, val=0.15) -> dict[str, str]:
    rng = random.Random(SEED)
    ordered = sorted(set(groups))
    rng.shuffle(ordered)
    n = len(ordered)
    n_train = max(1, int(n * train))
    n_val = max(1, int(n * val))
    assign = {}
    for i, g in enumerate(ordered):
        if i < n_train:
            assign[g] = "train"
        elif i < n_train + n_val:
            assign[g] = "val"
        else:
            assign[g] = "test"
    return assign


def main() -> None:
    records = []
    class_counts = defaultdict(int)
    for label, class_dir in CLASS_DIRS.items():
        if not class_dir.exists():
            print(f"WARNING: {class_dir} not found, skipping class {label}")
            continue
        files = sorted(class_dir.glob("*.jpg"))
        groups = [group_key(f.name) for f in files]
        split_map = group_split(groups)
        for f, g in zip(files, groups, strict=False):
            records.append(
                {
                    "file_path": str(f.relative_to(ROOT)).replace("\\", "/"),
                    "label": label,
                    "group": g,
                    "split": split_map[g],
                }
            )
            class_counts[label] += 1

    by_split_class = defaultdict(lambda: defaultdict(int))
    for r in records:
        by_split_class[r["split"]][r["label"]] += 1

    manifest = {
        "dataset": "mh_soyahealthvision_uav_subset",
        "task": "image_classification",
        "classes": sorted(CLASS_DIRS.keys()),
        "seed": SEED,
        "split_method": "group-aware (by flight/session filename prefix), not per-image random",
        "total_images": len(records),
        "class_counts": dict(class_counts),
        "split_class_counts": {k: dict(v) for k, v in by_split_class.items()},
        "records": records,
    }
    out = ROOT / "data" / "manifests" / "agriculture_uav_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {out}")
    print("Total images:", len(records))
    for split, counts in by_split_class.items():
        print(f"  {split}: {dict(counts)} (total {sum(counts.values())})")


if __name__ == "__main__":
    main()
