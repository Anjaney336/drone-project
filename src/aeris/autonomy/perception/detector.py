from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from aeris.models import Detection


class Detector(ABC):
    """Interface for timestamped visual detections; model loading stays adapter-specific."""

    @abstractmethod
    def detect(self, frame: Any, timestamp: float) -> list[Detection]:
        raise NotImplementedError


class UnavailableDetector(Detector):
    """Represents an absent camera/model without fabricating detections."""

    def detect(self, frame: Any, timestamp: float) -> list[Detection]:
        return []


class SimulationObservationDetector(Detector):
    """Converts labelled simulator camera observations; never runs on real frames."""

    def detect(self, frame: Any, timestamp: float) -> list[Detection]:
        if frame is None:
            return []
        if not isinstance(frame, dict) or frame.get("origin") != "simulation":
            raise TypeError("SimulationObservationDetector accepts simulation observations only")
        return [
            Detection(
                timestamp=timestamp,
                confidence=float(item["confidence"]),
                object_class=str(item["object_class"]),
                bbox_xyxy=tuple(map(float, item["bbox_xyxy"])),
                position=np.asarray(item["position_m"], dtype=float),
                provenance=item.get("provenance"),
            )
            for item in frame.get("detections", [])
        ]
