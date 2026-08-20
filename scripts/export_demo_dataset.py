"""Export the seeded AERIS demonstration dataset to a byte-reproducible JSON file.

Two things make the output reproducible, and both matter:

1. The export runs against a **throwaway database**, never the working
   `artifacts/aeris_product.db`. That database accumulates whatever the app and the
   test suite happened to create, and anything tagged `demonstration` in it would
   otherwise leak into the "authoritative" export.
2. The file is written as **bytes with explicit LF newlines**. `Path.write_text` opens
   in text mode, so on Windows it silently rewrites every \\n as \\r\\n and the SHA-256
   of the result no longer matches the one recorded in docs/dataset.md.

Verify the committed file against this generator with `--check`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from aeris.app.product_service import ProductStore

DEFAULT_OUTPUT = Path("data/demo/aeris_demo_seed_2026.json")


def render() -> bytes:
    """The seeded dataset as canonical UTF-8 bytes with LF newlines."""
    with tempfile.TemporaryDirectory() as tmp:
        store = ProductStore(Path(tmp) / "demo_export.db")
        payload = store.export_demo()
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the seeded AERIS demonstration dataset")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the existing file matches this generator instead of rewriting it",
    )
    args = parser.parse_args()

    content = render()
    digest = hashlib.sha256(content).hexdigest()

    if args.check:
        if not args.output.exists():
            raise SystemExit(f"{args.output} does not exist; run without --check to generate it.")
        actual = args.output.read_bytes()
        if actual != content:
            raise SystemExit(
                f"{args.output} does not match the generator.\n"
                f"  committed: {hashlib.sha256(actual).hexdigest()}\n"
                f"  expected:  {digest}\n"
                f"Regenerate with: python scripts/export_demo_dataset.py"
            )
        print(f"{args.output} matches the generator (sha256 {digest})")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    print(f"Wrote {args.output}")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
