"""Model registry / inference interface (Phase 9).

The application layer (product_service.py, api.py) must never import ultralytics/torch
or know a checkpoint's file layout directly — it goes through this registry, which
reports one of four honest states per model and only runs inference when READY. No
adapter fabricates a prediction: if a checkpoint isn't there, analyze() raises rather
than returning a made-up finding.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aeris.app.product_models import Domain, ModelStatus

ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ModelPrediction:
    domain: str
    task_type: str
    label: str
    confidence: float
    model_name: str
    model_version: str
    regions: list[dict] | None = None  # bounding boxes or mask summary, when applicable


class ModelAdapter(ABC):
    domain: Domain
    task_type: str
    model_name: str
    model_version: str
    run_dir: Path

    def status(self) -> ModelStatus:
        status_file = self.run_dir / "status.json"
        if not status_file.exists():
            return ModelStatus.NOT_TRAINED
        payload = json.loads(status_file.read_text())
        raw = payload.get("status", "NOT_TRAINED")
        try:
            return ModelStatus(raw)
        except ValueError:
            return ModelStatus.UNAVAILABLE

    def status_detail(self) -> dict[str, Any]:
        status_file = self.run_dir / "status.json"
        base = {
            "domain": self.domain,
            "task_type": self.task_type,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "status": self.status(),
        }
        if status_file.exists():
            base.update(
                {k: v for k, v in json.loads(status_file.read_text()).items() if k != "status"}
            )
        return base

    @abstractmethod
    def analyze(self, image_path: str) -> list[ModelPrediction]:
        """Raises RuntimeError if status() is not READY. Never fabricates a result."""
        raise NotImplementedError

    def _require_ready(self) -> None:
        status = self.status()
        if status != ModelStatus.READY:
            raise RuntimeError(
                f"{self.model_name} is {status.value}, not READY; "
                "refusing to fabricate a prediction."
            )


class InfrastructureDetectionModel(ModelAdapter):
    domain = Domain.INFRASTRUCTURE
    task_type = "object_detection"
    model_name = "damage_detection_yolov8n_baseline"
    model_version = "baseline-1"
    run_dir = ROOT / "artifacts" / "experiments" / "damage_detection_yolov8n_baseline"

    _model = None

    def _load(self):
        if self._model is None:
            from ultralytics import YOLO

            checkpoint = self.run_dir / "weights" / "best.pt"
            self._model = YOLO(str(checkpoint))
        return self._model

    def analyze(self, image_path: str) -> list[ModelPrediction]:
        self._require_ready()
        model = self._load()
        results = model.predict(source=image_path, verbose=False)
        predictions: list[ModelPrediction] = []
        names = {0: "class_0_unverified", 1: "class_1_unverified"}
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                xyxy = [round(v, 1) for v in box.xyxy[0].tolist()]
                predictions.append(
                    ModelPrediction(
                        domain=self.domain,
                        task_type=self.task_type,
                        label="AI Flagged: Possible Defect "
                        f"({names.get(cls_id, f'class_{cls_id}')})",
                        confidence=round(conf, 4),
                        model_name=self.model_name,
                        model_version=self.model_version,
                        regions=[{"type": "bbox", "xyxy": xyxy}],
                    )
                )
        return predictions


class CrackSegmentationModel(ModelAdapter):
    domain = Domain.INFRASTRUCTURE
    task_type = "semantic_segmentation_binary"
    model_name = "crack_segmentation_tinyunet_baseline"
    model_version = "baseline-1"
    run_dir = ROOT / "artifacts" / "experiments" / "crack_segmentation_tinyunet_baseline"

    _model = None

    def _load(self):
        if self._model is None:
            import torch

            from aeris.training.segmentation import TinyUNet

            model = TinyUNet(base=16)
            model.load_state_dict(torch.load(self.run_dir / "best_model.pt", map_location="cpu"))
            model.eval()
            self._model = model
        return self._model

    def analyze(self, image_path: str) -> list[ModelPrediction]:
        self._require_ready()
        import numpy as np
        import torch
        from PIL import Image

        model = self._load()
        img = Image.open(image_path).convert("RGB").resize((256, 256))
        tensor = (
            torch.from_numpy(np.asarray(img, dtype=np.float32) / 255.0)
            .permute(2, 0, 1)
            .unsqueeze(0)
        )
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.sigmoid(logits)[0, 0]
        crack_mask = probs > 0.5
        affected_fraction = float(crack_mask.float().mean().item())
        if affected_fraction < 0.001:
            return []
        mean_confidence = float(probs[crack_mask].mean().item()) if crack_mask.any() else 0.0
        return [
            ModelPrediction(
                domain=self.domain,
                task_type=self.task_type,
                label="AI Flagged: Possible Crack",
                confidence=round(mean_confidence, 4),
                model_name=self.model_name,
                model_version=self.model_version,
                regions=[
                    {"type": "mask_summary", "affected_area_fraction": round(affected_fraction, 4)}
                ],
            )
        ]


class AgricultureModel(ModelAdapter):
    domain = Domain.AGRICULTURE
    task_type = "image_classification"
    model_name = "agriculture_mobilenetv3_baseline"
    model_version = "unbuilt"
    run_dir = ROOT / "artifacts" / "experiments" / "agriculture_mobilenetv3_baseline"

    def analyze(self, image_path: str) -> list[ModelPrediction]:
        self._require_ready()
        raise RuntimeError("Agriculture model is not implemented yet")


REGISTRY: dict[str, ModelAdapter] = {
    "infrastructure_detection": InfrastructureDetectionModel(),
    "crack_segmentation": CrackSegmentationModel(),
    "agriculture": AgricultureModel(),
}


def registry_status() -> list[dict[str, Any]]:
    return [adapter.status_detail() for adapter in REGISTRY.values()]
