"""python scripts/download_datasets.py [--dataset agriculture]

Only the agriculture dataset (MH-SoyaHealthVision, CC BY 4.0, confirmed
license) has an automated download path - it is the only dataset here
with a verified, licensed, public source. Damage Detection and the UAV
crack dataset were acquired manually before their provenance was audited
and have no confirmed redistribution rights (see
docs/datasets/available_datasets.md); this script deliberately does not
try to "download" them from anywhere, since no verified source is known.

The download is resumable: re-running this script continues an existing
partial file (`curl -C -`) rather than restarting from zero.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGRICULTURE_URL = "https://data.mendeley.com/public-api/zip/hkbgh5s3b7/download/1"
AGRICULTURE_PATH = ROOT / "data" / "raw" / "agriculture" / "mh_soyahealthvision.zip"
EXPECTED_BYTES = 9_750_000_000


def download_agriculture() -> None:
    AGRICULTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if AGRICULTURE_PATH.exists():
        current = AGRICULTURE_PATH.stat().st_size
        pct = 100 * current / EXPECTED_BYTES
        print(
            f"Resuming existing partial download: {current:,} bytes "
            f"(~{pct:.1f}% of ~{EXPECTED_BYTES:,})."
        )
    else:
        print(
            "Starting fresh download of MH-SoyaHealthVision "
            "(~9.75 GB, CC BY 4.0, Mendeley DOI 10.17632/hkbgh5s3b7.1)."
        )
    cmd = ["curl", "-L", "-C", "-", "-o", str(AGRICULTURE_PATH), AGRICULTURE_URL]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            f"curl exited with code {result.returncode} - this is normal for a dropped "
            "connection; rerun this script to resume.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)
    print("Download finished. Run scripts/verify_datasets.py to check integrity before extracting.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["agriculture", "all"], default="agriculture")
    args = parser.parse_args()

    if args.dataset in ("agriculture", "all"):
        download_agriculture()

    print(
        "\nDamage Detection and UAV crack segmentation are NOT downloaded by this "
        "script - their upstream source is unverified. If you have the original "
        "source for either, add it to docs/datasets/available_datasets.md and this "
        "script, then re-run scripts/prepare_datasets.py."
    )


if __name__ == "__main__":
    main()
