"""Minimal U-Net baseline for binary crack segmentation, CPU-friendly by design:
small channel widths, downsized inputs, few epochs. This is an explicit small
baseline, not an accuracy-optimized model (see configs/training/crack_segmentation.yaml).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[3]


class CrackSegDataset(Dataset):
    def __init__(self, records: list[dict], image_size: int, augment: bool) -> None:
        self.records = records
        self.image_size = image_size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        r = self.records[idx]
        img = (
            Image.open(ROOT / r["file_path"])
            .convert("RGB")
            .resize((self.image_size, self.image_size))
        )
        mask = (
            Image.open(ROOT / r["label_path"])
            .convert("L")
            .resize((self.image_size, self.image_size))
        )
        img_arr = np.asarray(img, dtype=np.float32) / 255.0
        mask_arr = (np.asarray(mask, dtype=np.float32) > 127).astype(np.float32)
        if self.augment and np.random.rand() < 0.5:
            img_arr = img_arr[:, ::-1, :].copy()
            mask_arr = mask_arr[:, ::-1].copy()
        img_t = torch.from_numpy(img_arr).permute(2, 0, 1)
        mask_t = torch.from_numpy(mask_arr).unsqueeze(0)
        return img_t, mask_t


class TinyUNet(nn.Module):
    def __init__(self, base: int = 16) -> None:
        super().__init__()

        def block(cin, cout):
            return nn.Sequential(
                nn.Conv2d(cin, cout, 3, padding=1),
                nn.BatchNorm2d(cout),
                nn.ReLU(inplace=True),
                nn.Conv2d(cout, cout, 3, padding=1),
                nn.BatchNorm2d(cout),
                nn.ReLU(inplace=True),
            )

        self.enc1 = block(3, base)
        self.enc2 = block(base, base * 2)
        self.enc3 = block(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = block(base * 4, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.dec3 = block(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.dec2 = block(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.dec1 = block(base * 2, base)
        self.out = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b = self.bottleneck(self.pool(e3))
        d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.out(d1)


def iou_dice(pred_logits: torch.Tensor, target: torch.Tensor) -> tuple[float, float]:
    pred = (torch.sigmoid(pred_logits) > 0.5).float()
    inter = (pred * target).sum().item()
    union = ((pred + target) > 0).float().sum().item()
    iou = inter / union if union > 0 else float("nan")
    dice = (
        (2 * inter) / (pred.sum().item() + target.sum().item())
        if (pred.sum().item() + target.sum().item()) > 0
        else float("nan")
    )
    return iou, dice


def run_segmentation(cfg: dict, run_dir: Path) -> dict:
    torch.manual_seed(cfg["seed"])
    manifest = json.loads(
        (ROOT / "data" / "manifests" / "uav_crack_segmentation_manifest.json").read_text()
    )
    by_split = {"train": [], "val": [], "test": []}
    for r in manifest["records"]:
        if r["label_path"] is not None:
            by_split[r["split"]].append(r)

    size = cfg["model"]["input_size"]
    train_ds = CrackSegDataset(by_split["train"], size, augment=True)
    val_ds = CrackSegDataset(by_split["val"], size, augment=False)
    test_ds = CrackSegDataset(by_split["test"], size, augment=False)

    t = cfg["training"]
    train_loader = DataLoader(train_ds, batch_size=t["batch_size"], shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=t["batch_size"])
    test_loader = DataLoader(test_ds, batch_size=t["batch_size"])

    model = TinyUNet(base=cfg["model"]["base_channels"])
    optimizer = torch.optim.Adam(model.parameters(), lr=t["learning_rate"])

    best_val_loss = float("inf")
    best_state = None
    patience_left = t["early_stopping_patience"]
    history = []

    for epoch in range(t["epochs"]):
        model.train()
        train_loss = 0.0
        for imgs, masks in train_loader:
            optimizer.zero_grad()
            logits = model(imgs)
            loss = F.binary_cross_entropy_with_logits(logits, masks)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * imgs.size(0)
        train_loss /= len(train_ds)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, masks in val_loader:
                logits = model(imgs)
                val_loss += F.binary_cross_entropy_with_logits(logits, masks).item() * imgs.size(0)
        val_loss /= max(len(val_ds), 1)
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss})
        print(
            f"epoch {epoch + 1}/{t['epochs']} train_loss={train_loss:.4f} val_loss={val_loss:.4f}"
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

    model.eval()
    ious, dices = [], []
    with torch.no_grad():
        for imgs, masks in test_loader:
            logits = model(imgs)
            for i in range(imgs.size(0)):
                iou, dice = iou_dice(logits[i], masks[i])
                if not np.isnan(iou):
                    ious.append(iou)
                    dices.append(dice)

    (run_dir / "training_history.json").write_text(json.dumps(history, indent=2))

    return {
        "task_type": "semantic_segmentation_binary",
        "final_metrics": {
            "mean_iou": float(np.mean(ious)) if ious else None,
            "mean_dice": float(np.mean(dices)) if dices else None,
            "best_val_loss": float(best_val_loss),
            "test_samples_evaluated": len(ious),
        },
        "checkpoint_path": str(ckpt_path.relative_to(ROOT)),
    }
