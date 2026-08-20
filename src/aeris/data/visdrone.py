from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VisDroneInventory:
    split: str
    image_count: int
    annotation_count: int


def inspect_visdrone(root: Path) -> list[VisDroneInventory]:
    """Inventory a local VisDrone tree without downloading or inventing samples."""
    inventories: list[VisDroneInventory] = []
    for split in ("train", "val", "test-dev"):
        split_root = root / split
        images = split_root / "images"
        if not split_root.exists():
            inventories.append(VisDroneInventory(split, 0, 0))
            continue
        image_count = sum(
            1 for path in images.glob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        annotations = split_root / "annotations"
        annotation_count = (
            sum(1 for path in annotations.glob("*.txt")) if annotations.exists() else 0
        )
        inventories.append(VisDroneInventory(split, image_count, annotation_count))
    return inventories
