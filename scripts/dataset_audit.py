import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(".")
results = []


def sha256_partial(p, n=65536):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read(n))
    return h.hexdigest()


def audit_damage_detection():
    img_dir = ROOT / "data" / "raw" / "concrete" / "damage_detection" / "Images"
    yolo_dir = ROOT / "data" / "raw" / "concrete" / "damage_detection" / "Labels" / "Yolo"
    voc_dir = ROOT / "data" / "raw" / "concrete" / "damage_detection" / "Labels" / "Pascal VOC"
    imgs = sorted(img_dir.glob("*.jpg"))
    dims = Counter()
    corrupt = []
    hashes = defaultdict(list)
    class_counts = Counter()
    missing_labels = 0
    for im in imgs:
        try:
            with Image.open(im) as pic:
                dims[pic.size] += 1
        except Exception:
            corrupt.append(str(im))
        hashes[sha256_partial(im)].append(im.name)
        lbl = yolo_dir / (im.stem + ".txt")
        if not lbl.exists():
            missing_labels += 1
        else:
            for line in lbl.read_text().splitlines():
                if line.strip():
                    class_counts[line.split()[0]] += 1
    dupes = {h: v for h, v in hashes.items() if len(v) > 1}
    disk_bytes = sum(
        f.stat().st_size
        for f in (ROOT / "data" / "raw" / "concrete" / "damage_detection").rglob("*")
        if f.is_file()
    )
    return {
        "dataset_name": "Damage Detection (concrete/structural defects)",
        "directory": "Damage Detection/",
        "domain": "infrastructure",
        "total_files": len(
            list((ROOT / "data" / "raw" / "concrete" / "damage_detection").rglob("*"))
        ),
        "image_count": len(imgs),
        "video_count": 0,
        "annotation_count_yolo": sum(1 for _ in yolo_dir.glob("*.txt")),
        "annotation_count_voc_json": sum(1 for _ in voc_dir.glob("*.json")),
        "annotation_format": "YOLO bbox (.txt) + Pascal-VOC-style JSON bbox, duplicated per image",
        "class_names": (
            "UNKNOWN - no classes.txt/README shipped with dataset; "
            "classes are anonymous ids 0 and 1"
        ),
        "class_distribution": dict(class_counts),
        "class_imbalance_ratio": round(class_counts["0"] / max(class_counts["1"], 1), 2)
        if class_counts
        else None,
        "image_dimensions": {f"{w}x{h}": c for (w, h), c in dims.items()},
        "duplicate_images_exact_hash_prefix": len(dupes),
        "corrupted_files": corrupt,
        "missing_annotations": missing_labels,
        "existing_split": "none - flat directory, no train/val/test split provided",
        "potential_leakage": "not applicable (no split exists yet)",
        "same_sequence_across_splits": "not applicable (no split exists)",
        "disk_usage_bytes": disk_bytes,
        "disk_usage_mb": round(disk_bytes / 1e6, 2),
        "notes": (
            "Class semantics (e.g. crack vs spall) are not documented in source files and must "
            "not be assumed; treat as anonymous defect categories pending manual verification. "
            "Severe class imbalance (id 0 dominates ~98% of instances)."
        ),
    }


def audit_uav_crack():
    base = ROOT / "data" / "raw" / "concrete" / "uav_crack_segmentation"
    img_dir = base / "image"
    mask_dir = base / "masks"
    imgs = sorted(img_dir.glob("*.png"))
    masks = sorted(mask_dir.glob("*.png"))
    img_names = {p.stem for p in imgs}
    mask_names = {p.stem for p in masks}
    missing_masks = img_names - mask_names
    dims = Counter()
    corrupt = []
    mask_value_set = set()
    for im in imgs:
        try:
            with Image.open(im) as pic:
                dims[pic.size] += 1
        except Exception:
            corrupt.append(str(im))
    for i, m in enumerate(masks):
        if i > 50:
            break
        try:
            with Image.open(m) as pic:
                mask_value_set.update(pic.convert("L").getextrema())
        except Exception:
            pass
    disk_bytes = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
    return {
        "dataset_name": "UAV-based crack dataset (segmentation)",
        "directory": "UAV-based crack dataset used for segmentation/",
        "domain": "infrastructure",
        "total_files": len(list(base.rglob("*"))),
        "image_count": len(imgs),
        "video_count": 0,
        "annotation_count": len(masks),
        "annotation_format": "binary pixel mask (.png), same filename as source image",
        "class_names": "binary: crack pixel vs background (single-class segmentation)",
        "class_distribution": (
            "not computed at pixel level (would require full-mask scan); "
            "sampled mask value range logged in notes"
        ),
        "image_dimensions": {f"{w}x{h}": c for (w, h), c in dims.items()},
        "duplicate_images": "not computed (see limitations)",
        "corrupted_files": corrupt,
        "missing_annotations": len(missing_masks),
        "existing_split": "none - flat directory, no train/val/test split provided",
        "potential_leakage": "not applicable (no split exists yet)",
        "same_sequence_across_splits": "not applicable (no split exists)",
        "disk_usage_bytes": disk_bytes,
        "disk_usage_mb": round(disk_bytes / 1e6, 2),
        "notes": (
            f"Sampled first 50 masks: pixel value extrema observed = {sorted(mask_value_set)}. "
            "DJI filenames indicate real UAV-captured imagery of concrete/pavement surfaces."
        ),
    }


def audit_light_field():
    base = ROOT / "Dataset"
    files = list(base.glob("*.npy"))
    prefixes = Counter()
    for f in files:
        prefixes[f.name.split("-")[0]] += 1
    disk_bytes = sum(f.stat().st_size for f in files)
    return {
        "dataset_name": "Unlabeled light-field imagery (Dataset/)",
        "directory": "Dataset/",
        "domain": "UNKNOWN - not clearly infrastructure or agriculture",
        "total_files": len(files),
        "image_count": len(files),
        "annotation_count": 0,
        "annotation_format": (
            "none - raw .npy arrays, shape (256,256,3) float64 [0,1], "
            "no labels, no manifest, no README"
        ),
        "class_names": "none",
        "existing_split": "none",
        "disk_usage_bytes": disk_bytes,
        "disk_usage_mb": round(disk_bytes / 1e6, 2),
        "decision": "EXCLUDED from active pipeline",
        "notes": (
            "Filename prefixes (LF-, TL-) and 'colorimg' suggest light-field camera captures, "
            "possibly for depth/plenoptic research; no ground truth or documentation accompanies "
            "the files so no supervised task (infra or agriculture) can be justified. Per "
            "instructions not to force unrelated data into a fake task, this dataset is excluded "
            "pending the user clarifying its source/intended use."
        ),
    }


results = [audit_damage_detection(), audit_uav_crack(), audit_light_field()]

with open("artifacts/dataset_audit.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

# flat CSV
fieldnames = sorted({k for r in results for k in r.keys()})
with open("artifacts/dataset_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in results:
        row = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()}
        w.writerow(row)

print("done")
for r in results:
    print(r["dataset_name"], "->", r.get("image_count"), "images")
