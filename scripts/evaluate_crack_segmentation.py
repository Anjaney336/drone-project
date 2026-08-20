"""Detailed test-split evaluation of the trained crack-segmentation checkpoint.
Does not retrain. Computes per-image IoU/Dice/precision/recall and saves visual
examples spanning the full quality range (best, median, worst) so results are not
cherry-picked.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from aeris.training.segmentation import TinyUNet

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "artifacts" / "experiments" / "crack_segmentation_tinyunet_baseline"
OUT_DIR = ROOT / "artifacts" / "experiments" / "crack_segmentation_results"


def load_model() -> TinyUNet:
    model = TinyUNet(base=16)
    model.load_state_dict(torch.load(RUN_DIR / "best_model.pt", map_location="cpu"))
    model.eval()
    return model


def per_image_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray) -> dict:
    tp = float(np.logical_and(pred_mask, gt_mask).sum())
    fp = float(np.logical_and(pred_mask, ~gt_mask).sum())
    fn = float(np.logical_and(~pred_mask, gt_mask).sum())
    union = tp + fp + fn
    iou = tp / union if union > 0 else float("nan")
    dice = (2 * tp) / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else float("nan")
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    return {"iou": iou, "dice": dice, "precision": precision, "recall": recall,
            "gt_crack_pixels": int(gt_mask.sum()), "pred_crack_pixels": int(pred_mask.sum())}


def save_visual(name: str, img: Image.Image, gt: np.ndarray, pred: np.ndarray, out_path: Path) -> None:
    img_arr = np.asarray(img).astype(np.float32)
    overlay = img_arr.copy()
    # green = true positive, red = false positive (predicted, not gt), blue = false negative (missed)
    tp = np.logical_and(pred, gt)
    fp = np.logical_and(pred, ~gt)
    fn = np.logical_and(~pred, gt)
    overlay[tp] = [0, 255, 0]
    overlay[fp] = [255, 0, 0]
    overlay[fn] = [0, 0, 255]
    blended = (0.5 * img_arr + 0.5 * overlay).astype(np.uint8)
    Image.fromarray(blended).save(out_path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "data" / "manifests" / "uav_crack_segmentation_manifest.json").read_text())
    test_records = [r for r in manifest["records"] if r["split"] == "test" and r["label_path"]]

    model = load_model()
    results = []
    size = 256
    for record in test_records:
        img = Image.open(ROOT / record["file_path"]).convert("RGB").resize((size, size))
        gt_img = Image.open(ROOT / record["label_path"]).convert("L").resize((size, size))
        gt_mask = np.asarray(gt_img) > 127
        img_arr = np.asarray(img, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(img_arr).permute(2, 0, 1).unsqueeze(0)
        with torch.no_grad():
            probs = torch.sigmoid(model(tensor))[0, 0].numpy()
        pred_mask = probs > 0.5
        metrics = per_image_metrics(pred_mask, gt_mask)
        metrics["file"] = Path(record["file_path"]).name
        results.append(metrics)

    results.sort(key=lambda r: (r["iou"] if not np.isnan(r["iou"]) else -1))
    valid = [r for r in results if not np.isnan(r["iou"])]

    with (OUT_DIR / "per_image_metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # Save visual examples: 3 worst, 3 median, 3 best (by IoU), no cherry-picking of only good ones.
    def visualize_group(records_subset, tag):
        for r in records_subset:
            record = next(x for x in test_records if Path(x["file_path"]).name == r["file"])
            img = Image.open(ROOT / record["file_path"]).convert("RGB").resize((size, size))
            gt_mask = np.asarray(Image.open(ROOT / record["label_path"]).convert("L").resize((size, size))) > 127
            img_arr = np.asarray(img, dtype=np.float32) / 255.0
            tensor = torch.from_numpy(img_arr).permute(2, 0, 1).unsqueeze(0)
            with torch.no_grad():
                probs = torch.sigmoid(model(tensor))[0, 0].numpy()
            pred_mask = probs > 0.5
            save_visual(r["file"], img, gt_mask, pred_mask, OUT_DIR / f"{tag}_{r['file']}")

    n = len(valid)
    worst = valid[: min(3, n)]
    best = valid[max(0, n - 3):]
    median = valid[max(0, n // 2 - 1): n // 2 + 2]
    visualize_group(worst, "worst")
    visualize_group(median, "median")
    visualize_group(best, "best")

    summary = {
        "test_samples": len(results),
        "valid_samples_with_gt_or_pred_pixels": len(valid),
        "mean_iou": float(np.mean([r["iou"] for r in valid])) if valid else None,
        "mean_dice": float(np.mean([r["dice"] for r in valid])) if valid else None,
        "mean_precision": float(np.nanmean([r["precision"] for r in results])),
        "mean_recall": float(np.nanmean([r["recall"] for r in results])),
        "worst_iou": worst[0]["iou"] if worst else None,
        "best_iou": best[-1]["iou"] if best else None,
        "images_with_zero_predicted_and_zero_gt_pixels": sum(
            1 for r in results if r["gt_crack_pixels"] == 0 and r["pred_crack_pixels"] == 0
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
