# Sample data

Small, deterministically-selected subsets committed to the repository so a judge can run real inference without downloading the full datasets.

Selection method: `random.Random(20260820).sample()` on each dataset's **test split only** (never train, so these are also legitimate held-out evaluation images, not cherry-picked successes). Regenerate with `python scripts/build_sample_dataset.py` - the selection is exactly reproducible from the seed.

**License note:** these are small excerpts (15 files each) of datasets whose original upstream license is unconfirmed (see `docs/datasets/available_datasets.md`). Included for demo/reproducibility purposes; do not treat as a cleared-for-redistribution release until the source is confirmed.

- **damage_detection**: 15 files from the `test` split, seed 20260820
- **uav_crack_segmentation**: 15 files from the `test` split, seed 20260820
