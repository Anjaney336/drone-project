from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RiskWeights:
    collision: float = 0.35
    geofence: float = 0.20
    uncertainty: float = 0.20
    sensor_degradation: float = 0.15
    communication: float = 0.10

    def __post_init__(self) -> None:
        if abs(sum(asdict(self).values()) - 1.0) > 1e-9:
            raise ValueError("Risk weights must sum to 1.0")


def combine_risk(components: dict[str, float], weights: RiskWeights) -> dict[str, float]:
    weighted = {
        name: max(0.0, min(1.0, components.get(name, 0.0))) * value
        for name, value in asdict(weights).items()
    }
    return {
        **components,
        **{f"weighted_{key}": value for key, value in weighted.items()},
        "total": sum(weighted.values()),
    }
