from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from aeris.models import DataOrigin


@dataclass(frozen=True)
class InspectionObservation:
    observation_type: str
    severity: float
    confidence: float | None
    evidence_uri: str | None
    analysis_method: str
    origin: DataOrigin
    source: str


class InspectionAnalyzer(ABC):
    """Adapter boundary for a future evaluated defect model or human-labelled package."""

    @abstractmethod
    def analyze(
        self, payload: Any, *, origin: DataOrigin, source: str
    ) -> list[InspectionObservation]:
        raise NotImplementedError


class StructuredObservationAdapter(InspectionAnalyzer):
    """Accepts explicit observations; performs no image inference and creates no confidence."""

    def analyze(
        self, payload: Any, *, origin: DataOrigin, source: str
    ) -> list[InspectionObservation]:
        if not isinstance(payload, list):
            raise TypeError("Structured observation payload must be a list")
        return [
            InspectionObservation(
                observation_type=str(item["observation_type"]),
                severity=float(item["severity"]),
                confidence=None,
                evidence_uri=item.get("evidence_uri"),
                analysis_method="structured_observation_no_model_inference",
                origin=origin,
                source=source,
            )
            for item in payload
        ]
