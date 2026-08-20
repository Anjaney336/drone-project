"""python scripts/build_sample_dataset.py

Builds data/samples/ - a small, deterministically-selected subset of each
infrastructure dataset, small enough to commit to git and use for a judge
demo without downloading anything. Selection is from each dataset's TEST
split only (never train), using random.Random(SPLIT_SEED).sample so the
selection is exactly reproducible.
"""

from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLIT_SEED = 20260820
N_SAMPLES = 15


def build_damage_detection_sample() -> dict:
    manifest = json.loads(
        (ROOT / "data" / "manifests" / "damage_detection_manifest.json").read_text()
    )
    test_records = [r for r in manifest["records"] if r["split"] == "test" and r["label_path"]]
    picked = random.Random(SPLIT_SEED).sample(test_records, min(N_SAMPLES, len(test_records)))
    out_img = ROOT / "data" / "samples" / "damage_detection" / "images"
    out_lbl = ROOT / "data" / "samples" / "damage_detection" / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)
    for r in picked:
        shutil.copy2(ROOT / r["file_path"], out_img / Path(r["file_path"]).name)
        shutil.copy2(ROOT / r["label_path"], out_lbl / Path(r["label_path"]).name)
    return {
        "dataset": "damage_detection",
        "selected": len(picked),
        "from_split": "test",
        "seed": SPLIT_SEED,
    }


def build_uav_crack_sample() -> dict:
    manifest = json.loads(
        (ROOT / "data" / "manifests" / "uav_crack_segmentation_manifest.json").read_text()
    )
    test_records = [r for r in manifest["records"] if r["split"] == "test" and r["label_path"]]
    picked = random.Random(SPLIT_SEED).sample(test_records, min(N_SAMPLES, len(test_records)))
    out_img = ROOT / "data" / "samples" / "uav_crack_segmentation" / "image"
    out_msk = ROOT / "data" / "samples" / "uav_crack_segmentation" / "masks"
    out_img.mkdir(parents=True, exist_ok=True)
    out_msk.mkdir(parents=True, exist_ok=True)
    for r in picked:
        shutil.copy2(ROOT / r["file_path"], out_img / Path(r["file_path"]).name)
        shutil.copy2(ROOT / r["label_path"], out_msk / Path(r["label_path"]).name)
    return {
        "dataset": "uav_crack_segmentation",
        "selected": len(picked),
        "from_split": "test",
        "seed": SPLIT_SEED,
    }


def main() -> None:
    results = [build_damage_detection_sample(), build_uav_crack_sample()]
    readme = ROOT / "data" / "samples" / "README.md"
    readme.write_text(
        "# Sample data\n\n"
        "Small, deterministically-selected subsets committed to the repository so a judge can run "
        "real inference without downloading the full datasets.\n\n"
        f"Selection method: `random.Random({SPLIT_SEED}).sample()` on each dataset's "
        "**test split only** "
        "(never train, so these are also legitimate held-out evaluation images, not cherry-picked "
        "successes). Regenerate with `python scripts/build_sample_dataset.py` - the selection is "
        "exactly reproducible from the seed.\n\n"
        "**License note:** these are small excerpts (15 files each) of datasets whose original "
        "upstream license is unconfirmed (see `docs/datasets/available_datasets.md`). Included for "
        "demo/reproducibility purposes; do not treat as a cleared-for-redistribution release until "
        "the source is confirmed.\n\n"
        + "\n".join(
            f"- **{r['dataset']}**: {r['selected']} files from the `{r['from_split']}` split, "
            f"seed {r['seed']}"
            for r in results
        )
        + "\n"
    )
    for r in results:
        print(r)
    print(f"Wrote {readme}")


if __name__ == "__main__":
    main()
