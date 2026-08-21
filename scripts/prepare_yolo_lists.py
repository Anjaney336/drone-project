"""Turn the damage_detection manifest into Ultralytics-compatible split lists."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    manifest = json.loads(
        (ROOT / "data" / "manifests" / "damage_detection_manifest.json").read_text()
    )
    out_dir = ROOT / "data" / "processed" / "infrastructure" / "concrete" / "damage_detection"
    out_dir.mkdir(parents=True, exist_ok=True)
    by_split: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for r in manifest["records"]:
        if r["label_path"] is None:
            continue
        by_split[r["split"]].append(str((ROOT / r["file_path"]).resolve()))
    for split, paths in by_split.items():
        (out_dir / f"{split}.txt").write_text("\n".join(paths) + "\n")
        print(split, len(paths))

    seed = manifest["seed"]
    yaml_text = f"""# Auto-generated from data/manifests/damage_detection_manifest.json
# (seed {seed})
path: {ROOT.as_posix()}
train: data/processed/infrastructure/concrete/damage_detection/train.txt
val: data/processed/infrastructure/concrete/damage_detection/val.txt
test: data/processed/infrastructure/concrete/damage_detection/test.txt
names:
  0: class_0_unverified
  1: class_1_unverified
"""
    (ROOT / "configs" / "data" / "damage_detection.yaml").write_text(yaml_text)


if __name__ == "__main__":
    main()
