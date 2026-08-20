"""Create deterministic, leakage-free train/val/test splits and manifests for the
concrete-domain infrastructure datasets. Grouping is by image stem so the paired
YOLO/VOC label formats for Damage Detection never separate, and no image appears
in more than one split.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 20260820
random.seed(SEED)

ROOT = Path(__file__).resolve().parents[1]


def split_ids(ids: list[str], train=0.7, val=0.15) -> dict[str, list[str]]:
    ids = sorted(ids)
    rng = random.Random(SEED)
    rng.shuffle(ids)
    n = len(ids)
    n_train = int(n * train)
    n_val = int(n * val)
    return {
        "train": sorted(ids[:n_train]),
        "val": sorted(ids[n_train:n_train + n_val]),
        "test": sorted(ids[n_train + n_val:]),
    }


def build_damage_detection_manifest() -> dict:
    base = ROOT / "data" / "raw" / "concrete" / "damage_detection"
    imgs = sorted((base / "Images").glob("*.jpg"))
    stems = [p.stem for p in imgs]
    splits = split_ids(stems)
    stem_to_split = {s: k for k, v in splits.items() for s in v}
    records = []
    for im in imgs:
        lbl = base / "Labels" / "Yolo" / f"{im.stem}.txt"
        records.append({
            "source_dataset": "damage_detection_local",
            "domain": "infrastructure",
            "task_type": "object_detection",
            "file_path": str(im.relative_to(ROOT)).replace("\\", "/"),
            "label_path": str(lbl.relative_to(ROOT)).replace("\\", "/") if lbl.exists() else None,
            "split": stem_to_split[im.stem],
            "provenance": {
                "origin": "public_dataset_unverified_source",
                "note": "Downloaded raw folder with no accompanying README/classes.txt; upstream source and exact license not retained. Class ids 0/1 are anonymous pending verification.",
            },
        })
    return {"dataset": "damage_detection_local", "seed": SEED, "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15}, "count": len(records), "records": records}


def build_crack_segmentation_manifest() -> dict:
    base = ROOT / "data" / "raw" / "concrete" / "uav_crack_segmentation"
    imgs = sorted((base / "image").glob("*.png"))
    stems = [p.stem for p in imgs]
    splits = split_ids(stems)
    stem_to_split = {s: k for k, v in splits.items() for s in v}
    records = []
    for im in imgs:
        mask = base / "masks" / im.name
        records.append({
            "source_dataset": "uav_crack_segmentation_local",
            "domain": "infrastructure",
            "task_type": "semantic_segmentation_binary",
            "file_path": str(im.relative_to(ROOT)).replace("\\", "/"),
            "label_path": str(mask.relative_to(ROOT)).replace("\\", "/") if mask.exists() else None,
            "split": stem_to_split[im.stem],
            "provenance": {
                "origin": "public_dataset_unverified_source",
                "note": "DJI-filename UAV pavement/crack imagery with binary masks; upstream source and exact license not retained with the raw folder.",
            },
        })
    return {"dataset": "uav_crack_segmentation_local", "seed": SEED, "split_ratio": {"train": 0.7, "val": 0.15, "test": 0.15}, "count": len(records), "records": records}


if __name__ == "__main__":
    out_dir = ROOT / "data" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    dd = build_damage_detection_manifest()
    cs = build_crack_segmentation_manifest()
    (out_dir / "damage_detection_manifest.json").write_text(json.dumps(dd, indent=2))
    (out_dir / "uav_crack_segmentation_manifest.json").write_text(json.dumps(cs, indent=2))
    for name, m in (("damage_detection", dd), ("uav_crack_segmentation", cs)):
        for split in ("train", "val", "test"):
            n = sum(1 for r in m["records"] if r["split"] == split)
            print(f"{name} {split}: {n}")
