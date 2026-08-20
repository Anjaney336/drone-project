from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeris.app.product_service import ProductStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the seeded AERIS demonstration dataset")
    parser.add_argument("--output", type=Path, default=Path("data/demo/aeris_demo_seed_2026.json"))
    args = parser.parse_args()
    store = ProductStore()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(store.export_demo(), indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
