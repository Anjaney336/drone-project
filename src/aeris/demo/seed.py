"""python -m aeris.demo.seed — explicit, reproducible demo-data initialization.

AERIS auto-seeds its demonstration dataset (origin=demonstration, source=aeris.demo.seed.v1,
fixed timestamp 2026-01-15T09:00:00+00:00) the first time ProductStore opens an empty
database (see product_service.py:_seed). This command exists so demo initialization is an
explicit, named, documented step rather than something that only happens as a side effect
of the API server starting - it does not add a second seeding path or silently inject data
into a database that already has real records.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from aeris.app.product_service import ProductStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("artifacts/aeris_product.db"))
    args = parser.parse_args()

    is_fresh = not args.db.exists()
    store = ProductStore(path=args.db)
    assets = store.list_assets()
    demo_count = sum(1 for a in assets if a["origin"] == "demonstration")

    if is_fresh:
        print(f"Initialized {args.db} and seeded {demo_count} DEMO DATA assets (origin=demonstration).")
    else:
        print(f"{args.db} already exists with {len(assets)} asset(s), {demo_count} labelled DEMO DATA.")
        print("No data was overwritten. To start clean, delete the database file first and rerun this command.")


if __name__ == "__main__":
    main()
