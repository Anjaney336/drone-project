from pathlib import Path

from aeris.data.synthetic import SyntheticConfig, write_dataset


def main() -> None:
    for split, seed in (("tuning", 20261), ("held_out", 20262)):
        write_dataset(
            SyntheticConfig(seed=seed, split=split),
            Path(f"data/processed/synthetic/{split}.npz"),
            Path(f"data/manifests/synthetic_{split}.json"),
        )
        print(f"generated {split} seed={seed}")


if __name__ == "__main__":
    main()
