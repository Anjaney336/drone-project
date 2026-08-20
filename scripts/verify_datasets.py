"""python scripts/verify_datasets.py

Checks every dataset manifest against the actual filesystem: expected
directories exist, file counts match, checksums (where recorded) match,
manifest/split consistency holds, and train/val/test splits don't leak
the same base filename across splits. Exits non-zero if anything fails.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "data" / "manifests"

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def report(check: str, status: str, detail: str) -> None:
    results.append((check, status, detail))


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def verify_checksums(name: str, checksums_file: Path, sample: int = 25) -> None:
    if not checksums_file.exists():
        report(
            f"{name}.checksums", WARN, f"{checksums_file} not found - run prepare_datasets.py first"
        )
        return
    lines = checksums_file.read_text().splitlines()
    if not lines:
        report(f"{name}.checksums", FAIL, "checksum file is empty")
        return
    import random

    random.seed(20260820)
    picked = random.sample(lines, min(sample, len(lines)))
    bad = []
    for line in picked:
        digest, rel = line.split("  ", 1)
        path = ROOT / rel
        if not path.exists():
            bad.append(f"missing: {rel}")
            continue
        if sha256_file(path) != digest:
            bad.append(f"checksum mismatch: {rel}")
    if bad:
        report(f"{name}.checksums", FAIL, f"{len(bad)}/{len(picked)} sampled files bad: {bad[:5]}")
    else:
        report(
            f"{name}.checksums", PASS, f"{len(picked)}/{len(lines)} files spot-checked, all match"
        )


def verify_split_leakage(name: str, manifest_path: Path) -> None:
    if not manifest_path.exists():
        report(f"{name}.split_leakage", WARN, f"{manifest_path} not found")
        return
    data = json.loads(manifest_path.read_text())
    records = data.get("records")
    if not records:
        report(f"{name}.split_leakage", WARN, "manifest has no per-file split records to check")
        return
    stem_to_splits: dict[str, set[str]] = {}
    for r in records:
        stem = Path(r["file_path"]).stem
        stem_to_splits.setdefault(stem, set()).add(r["split"])
    leaked = {s: v for s, v in stem_to_splits.items() if len(v) > 1}
    if leaked:
        report(
            f"{name}.split_leakage", FAIL, f"{len(leaked)} base filenames appear in multiple splits"
        )
    else:
        report(
            f"{name}.split_leakage", PASS, f"{len(stem_to_splits)} files, no cross-split leakage"
        )


def verify_damage_detection() -> None:
    base = ROOT / "data" / "raw" / "concrete" / "damage_detection"
    if not base.exists():
        report("damage_detection.present", WARN, "not present locally (not required to be)")
        return
    images = list((base / "images").glob("*.jpg"))
    labels = list((base / "labels").glob("*.txt"))
    report(
        "damage_detection.file_count",
        PASS if len(images) == 1500 else FAIL,
        f"{len(images)} images (expected 1500)",
    )
    report(
        "damage_detection.labels",
        PASS if len(labels) == 1500 else FAIL,
        f"{len(labels)} labels (expected 1500)",
    )
    verify_checksums("damage_detection", MANIFEST_DIR / "damage_detection_checksums.sha256")
    verify_split_leakage("damage_detection", MANIFEST_DIR / "damage_detection_manifest.json")


def verify_uav_crack() -> None:
    base = ROOT / "data" / "raw" / "concrete" / "uav_crack_segmentation"
    if not base.exists():
        report("uav_crack.present", WARN, "not present locally (not required to be)")
        return
    images = list((base / "image").glob("*.png"))
    masks = list((base / "masks").glob("*.png"))
    report(
        "uav_crack.file_count",
        PASS if len(images) == 315 else FAIL,
        f"{len(images)} images (expected 315)",
    )
    report(
        "uav_crack.masks", PASS if len(masks) == 315 else FAIL, f"{len(masks)} masks (expected 315)"
    )
    verify_checksums(
        "uav_crack_segmentation", MANIFEST_DIR / "uav_crack_segmentation_checksums.sha256"
    )
    verify_split_leakage(
        "uav_crack_segmentation", MANIFEST_DIR / "uav_crack_segmentation_manifest.json"
    )


def verify_agriculture() -> None:
    zip_path = ROOT / "data" / "raw" / "agriculture" / "mh_soyahealthvision.zip"
    if not zip_path.exists():
        report("agriculture.present", WARN, "not downloaded yet")
        return
    size = zip_path.stat().st_size
    expected = 9_750_000_000
    pct = 100 * size / expected
    if pct < 99.5:
        report("agriculture.download", WARN, f"{pct:.1f}% downloaded, not yet complete")
        return
    import zipfile

    try:
        zf = zipfile.ZipFile(zip_path)
        bad = zf.testzip()
        if bad:
            report("agriculture.integrity", FAIL, f"corrupt entry: {bad}")
        else:
            report(
                "agriculture.integrity", PASS, f"{len(zf.namelist())} entries, all pass testzip()"
            )
    except Exception as exc:  # noqa: BLE001
        report("agriculture.integrity", FAIL, f"{type(exc).__name__}: {exc}")


def verify_models() -> None:
    for name, path in [
        (
            "damage_detection_yolov8n_baseline",
            ROOT / "artifacts/experiments/damage_detection_yolov8n_baseline/weights/best.pt",
        ),
        (
            "crack_segmentation_tinyunet_baseline",
            ROOT / "artifacts/experiments/crack_segmentation_tinyunet_baseline/best_model.pt",
        ),
    ]:
        if path.exists():
            report(f"model.{name}", PASS, f"checkpoint present, {path.stat().st_size / 1e6:.1f} MB")
        else:
            report(f"model.{name}", FAIL, "checkpoint missing")


def main() -> int:
    verify_damage_detection()
    verify_uav_crack()
    verify_agriculture()
    verify_models()

    print(f"{'CHECK':45s} {'STATUS':6s} DETAIL")
    print("-" * 100)
    exit_code = 0
    for check, status, detail in results:
        print(f"{check:45s} {status:6s} {detail}")
        if status == FAIL:
            exit_code = 1
    print("-" * 100)
    n_pass = sum(1 for _, s, _ in results if s == PASS)
    n_fail = sum(1 for _, s, _ in results if s == FAIL)
    n_warn = sum(1 for _, s, _ in results if s == WARN)
    print(f"{n_pass} passed, {n_fail} failed, {n_warn} warnings")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
