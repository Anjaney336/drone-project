"""python scripts/cache_agriculture_images.py

Pre-resizes the UAV agriculture images once, in parallel, to a small cache.

Why this exists (measured, not assumed): the source images are 3840x2160.
Decoding one and resizing it to 224x224 costs ~115 ms. With 1,656 training
images that is ~190 s of pure JPEG decoding PER EPOCH, single-threaded,
before any actual learning happens - the GPU/CPU sits idle waiting on
Pillow. Caching to 256x256 once turns that into ~2 ms per image, and the
cache is reused by every subsequent epoch and every future experiment.

256 (not 224) so that random-crop/flip augmentation at 224 still has pixels
to work with rather than being forced to use the exact training resolution.
"""

from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = ROOT / "data" / "processed" / "agriculture" / "uav_cache_256"
CACHE_SIZE = 256


def cache_one(args: tuple[str, str]) -> tuple[str, bool]:
    src_rel, dst_rel = args
    dst = ROOT / dst_rel
    if dst.exists():
        return dst_rel, True
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(ROOT / src_rel) as im:
            im = im.convert("RGB").resize((CACHE_SIZE, CACHE_SIZE), Image.BILINEAR)
            im.save(dst, "JPEG", quality=92)
        return dst_rel, True
    except Exception:
        return dst_rel, False


def main() -> None:
    manifest_path = ROOT / "data" / "manifests" / "agriculture_uav_manifest.json"
    manifest = json.loads(manifest_path.read_text())

    jobs: list[tuple[str, str]] = []
    for r in manifest["records"]:
        src_rel = r["file_path"]
        cached_rel = (
            CACHE_ROOT.relative_to(ROOT) / r["label"] / Path(src_rel).name
        ).as_posix()
        r["cached_path"] = cached_rel
        jobs.append((src_rel, cached_rel))

    print(f"Caching {len(jobs)} images to {CACHE_ROOT.relative_to(ROOT)} at {CACHE_SIZE}px ...")
    failures = []
    with ProcessPoolExecutor(max_workers=12) as pool:
        for i, (dst_rel, ok) in enumerate(pool.map(cache_one, jobs, chunksize=16), 1):
            if not ok:
                failures.append(dst_rel)
            if i % 400 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    manifest["cache_dir"] = CACHE_ROOT.relative_to(ROOT).as_posix()
    manifest["cache_size_px"] = CACHE_SIZE
    manifest_path.write_text(json.dumps(manifest, indent=2))

    cached = len(list(CACHE_ROOT.rglob("*.jpg")))
    print(f"Done. {cached} cached images, {len(failures)} failures.")
    if failures:
        print("Failed:", failures[:10])


if __name__ == "__main__":
    main()
