"""MobileNetV3-Small baseline for the MH-SoyaHealthVision UAV crop-health
subset (image classification: healthy / rust / mosaic / pest_attack).
Group-aware split (by flight session) - see scripts/build_agriculture_splits.py.
CPU-only, ImageNet-pretrained backbone fine-tuned, deliberately small epoch
budget for CPU turnaround, same as the infrastructure baselines.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

ROOT = Path(__file__).resolve().parents[3]
CLASSES = ["healthy", "rust", "mosaic", "pest_attack"]


class CropDataset(Dataset):
    def __init__(self, records: list[dict], image_size: int, augment: bool) -> None:
        self.records = records
        self.image_size = image_size
        self.augment = augment
        self.class_to_idx = {c: i for i, c in enumerate(CLASSES)}
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        r = self.records[idx]
        img = (
            Image.open(ROOT / r["file_path"])
            .convert("RGB")
            .resize((self.image_size, self.image_size))
        )
        arr = np.asarray(img, dtype=np.float32) / 255.0
        if self.augment and np.random.rand() < 0.5:
            arr = arr[:, ::-1, :].copy()
        arr = (arr - self.mean) / self.std
        tensor = torch.from_numpy(arr).permute(2, 0, 1).float()
        label = self.class_to_idx[r["label"]]
        return tensor, label


def load_manifest_split() -> dict[str, list[dict]]:
    manifest = json.loads(
        (ROOT / "data" / "manifests" / "agriculture_uav_manifest.json").read_text()
    )
    by_split: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for r in manifest["records"]:
        by_split[r["split"]].append(r)
    return by_split


def run_agriculture_training(cfg: dict, run_dir: Path) -> dict:
    torch.manual_seed(cfg["seed"])
    by_split = load_manifest_split()
    size = cfg["model"]["input_size"]
    t = cfg["training"]

    train_ds = CropDataset(by_split["train"], size, augment=True)
    val_ds = CropDataset(by_split["val"], size, augment=False)
    test_ds = CropDataset(by_split["test"], size, augment=False)

    train_loader = DataLoader(train_ds, batch_size=t["batch_size"], shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=t["batch_size"], num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=t["batch_size"], num_workers=0)

    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, len(CLASSES))

    optimizer = torch.optim.Adam(model.parameters(), lr=t["learning_rate"])
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    patience_left = t["early_stopping_patience"]
    history = []

    for epoch in range(t["epochs"]):
        model.train()
        train_loss, train_correct, train_n = 0.0, 0, 0
        for imgs, labels in train_loader:
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * imgs.size(0)
            train_correct += (logits.argmax(1) == labels).sum().item()
            train_n += imgs.size(0)
        train_loss /= max(train_n, 1)
        train_acc = train_correct / max(train_n, 1)

        model.eval()
        val_loss, val_correct, val_n = 0.0, 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                logits = model(imgs)
                val_loss += criterion(logits, labels).item() * imgs.size(0)
                val_correct += (logits.argmax(1) == labels).sum().item()
                val_n += imgs.size(0)
        val_loss /= max(val_n, 1)
        val_acc = val_correct / max(val_n, 1)
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
            }
        )
        print(
            f"epoch {epoch + 1}/{t['epochs']} train_loss={train_loss:.4f} "
            f"train_acc={train_acc:.3f} val_loss={val_loss:.4f} val_acc={val_acc:.3f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_left = t["early_stopping_patience"]
        else:
            patience_left -= 1
            if patience_left <= 0:
                print(f"early stopping at epoch {epoch + 1}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = run_dir / "best_model.pt"
    torch.save(model.state_dict(), ckpt_path)
    (run_dir / "training_history.json").write_text(json.dumps(history, indent=2))

    # Final untouched-test evaluation: per-class precision/recall/F1 + confusion matrix.
    model.eval()
    n_classes = len(CLASSES)
    confusion = np.zeros((n_classes, n_classes), dtype=int)
    with torch.no_grad():
        for imgs, labels in test_loader:
            preds = model(imgs).argmax(1)
            for p, y in zip(preds.tolist(), labels.tolist(), strict=False):
                confusion[y, p] += 1

    per_class = {}
    for i, c in enumerate(CLASSES):
        tp = confusion[i, i]
        fp = confusion[:, i].sum() - tp
        fn = confusion[i, :].sum() - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else None
        recall = tp / (tp + fn) if (tp + fn) > 0 else None
        f1 = (
            (2 * precision * recall / (precision + recall))
            if precision and recall and (precision + recall) > 0
            else None
        )
        per_class[c] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(confusion[i, :].sum()),
        }

    overall_acc = float(np.trace(confusion) / confusion.sum()) if confusion.sum() > 0 else None

    return {
        "task_type": "image_classification",
        "classes": CLASSES,
        "final_metrics": {
            "overall_accuracy": overall_acc,
            "per_class": per_class,
            "confusion_matrix": confusion.tolist(),
            "test_samples_evaluated": int(confusion.sum()),
        },
        "checkpoint_path": str(ckpt_path.relative_to(ROOT)),
    }
