"""python scripts/prepare_datasets.py

Builds/refreshes manifests (with real, computed SHA-256 fingerprints) and
deterministic splits for every locally-present dataset. Does not download
anything - see scripts/download_datasets.py for that. Does not invent a
checksum, file count, or split for a dataset that isn't actually present.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "data" / "manifests"
SPLIT_SEED = 20260820


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def fingerprint_dataset(files: list[Path], checksums_path: Path) -> str:
    """Per-file SHA-256 written to checksums_path (sha256sum format, sorted by
    relative path for determinism); the dataset fingerprint is the SHA-256 of
    that sorted checksum listing, so it changes iff any file's content or the
    file set changes."""
    lines = []
    for f in sorted(files, key=lambda p: str(p).lower()):
        digest = sha256_file(f)
        rel = f.relative_to(ROOT).as_posix()
        lines.append(f"{digest}  {rel}")
    checksums_path.write_text("\n".join(lines) + ("\n" if lines else ""))
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def prepare_damage_detection() -> dict:
    base = ROOT / "data" / "raw" / "concrete" / "damage_detection"
    images = sorted((base / "images").glob("*.jpg"))
    if not images:
        return {"name": "damage_detection", "status": "NOT_PRESENT_LOCALLY"}
    files = images + list((base / "labels").glob("*.txt"))
    checksums = MANIFEST_DIR / "damage_detection_checksums.sha256"
    fingerprint = fingerprint_dataset(files, checksums)
    manifest = {
        "name": "damage_detection",
        "version": "local-1",
        "source": (
            "unverified - raw folder acquired without accompanying "
            "README/classes.txt/LICENSE; upstream origin not retained "
            "(see docs/datasets/available_datasets.md)"
        ),
        "license": (
            "UNCONFIRMED - do not redistribute the full dataset publicly until a human "
            "confirms the original source and license"
        ),
        "task": "object_detection",
        "domain": "infrastructure (concrete defects)",
        "file_count": len(files),
        "image_count": len(images),
        "sha256_fingerprint": fingerprint,
        "checksums_file": str(checksums.relative_to(ROOT)).replace("\\", "/"),
        "status": "READY_LOCAL_LICENSE_UNCONFIRMED",
        "split_seed": SPLIT_SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (MANIFEST_DIR / "damage_detection_manifest_v2.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def prepare_uav_crack() -> dict:
    base = ROOT / "data" / "raw" / "concrete" / "uav_crack_segmentation"
    images = sorted((base / "image").glob("*.png"))
    if not images:
        return {"name": "uav_crack_segmentation", "status": "NOT_PRESENT_LOCALLY"}
    files = images + list((base / "masks").glob("*.png"))
    checksums = MANIFEST_DIR / "uav_crack_segmentation_checksums.sha256"
    fingerprint = fingerprint_dataset(files, checksums)
    manifest = {
        "name": "uav_crack_segmentation",
        "version": "local-1",
        "source": (
            "unverified - raw folder acquired without accompanying README/LICENSE; "
            "DJI filenames indicate genuine UAV capture but upstream release is not retained"
        ),
        "license": (
            "UNCONFIRMED - do not redistribute the full dataset publicly until a human "
            "confirms the original source and license"
        ),
        "task": "semantic_segmentation_binary",
        "domain": "infrastructure (pavement/structure cracks)",
        "file_count": len(files),
        "image_count": len(images),
        "sha256_fingerprint": fingerprint,
        "checksums_file": str(checksums.relative_to(ROOT)).replace("\\", "/"),
        "status": "READY_LOCAL_LICENSE_UNCONFIRMED",
        "split_seed": SPLIT_SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (MANIFEST_DIR / "uav_crack_segmentation_manifest_v2.json").write_text(
        json.dumps(manifest, indent=2)
    )
    return manifest


def prepare_agriculture() -> dict:
    zip_path = ROOT / "data" / "raw" / "agriculture" / "mh_soyahealthvision.zip"
    expected_bytes = 9_750_000_000  # Mendeley page's stated ~9.75 GB, approximate
    manifest = {
        "name": "mh_soyahealthvision",
        "version": "1",
        "source": "Mendeley Data, DOI 10.17632/hkbgh5s3b7.1",
        "license": "CC BY 4.0 (attribution required)",
        "task": "image_classification (pending confirmation from extracted annotations)",
        "domain": "agriculture (soybean leaf disease + UAV aerial)",
        "split_seed": SPLIT_SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not zip_path.exists():
        manifest["status"] = "DOWNLOAD_NOT_STARTED"
    else:
        actual = zip_path.stat().st_size
        pct = 100 * actual / expected_bytes
        manifest["downloaded_bytes"] = actual
        manifest["expected_bytes_approx"] = expected_bytes
        manifest["completion_percent_approx"] = round(pct, 1)
        manifest["status"] = (
            "DOWNLOADING" if pct < 99.5 else "DOWNLOAD_COMPLETE_INTEGRITY_UNVERIFIED"
        )
    (MANIFEST_DIR / "agriculture_manifest_v2.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    results = [prepare_damage_detection(), prepare_uav_crack(), prepare_agriculture()]
    for r in results:
        print(
            f"{r['name']}: {r['status']}"
            + (f" ({r.get('file_count')} files)" if "file_count" in r else "")
        )


if __name__ == "__main__":
    main()
