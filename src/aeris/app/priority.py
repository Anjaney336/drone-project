from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriorityResult:
    score: float
    level: str
    factors: list[str]
    components: dict[str, float]
    formula: str


# Four or more repeat sightings saturate the recurrence term; beyond that, "seen again"
# stops adding information for triage purposes.
RECURRENCE_SATURATION = 4.0

WEIGHTS = {
    "severity": 0.30,
    "confidence": 0.15,
    "criticality": 0.25,
    "recurrence": 0.10,
    "trend": 0.10,
    "geographic_impact": 0.10,
}


def assess_priority(
    *,
    severity: float,
    confidence: float | None,
    criticality: float,
    recurrence: int,
    trend: float,
    geographic_impact: float,
) -> PriorityResult:
    """Transparent prototype score.

    Unlike mission reliability, priority must always produce a number — it exists to
    rank a queue, and an unrankable item is useless to an authority. So an unknown
    confidence is handled by *dropping the confidence term and renormalising the
    remaining weights*, exactly as the reliability engine does, rather than by
    substituting a neutral 0.5. Inventing an input would let a value nobody measured
    move an asset up or down the queue.
    """
    bounded = {
        "severity": min(max(severity, 0.0), 1.0),
        "criticality": min(max(criticality, 0.0), 1.0),
        "recurrence": min(max(recurrence / RECURRENCE_SATURATION, 0.0), 1.0),
        "trend": min(max(trend, 0.0), 1.0),
        "geographic_impact": min(max(geographic_impact, 0.0), 1.0),
    }
    if confidence is not None:
        bounded["confidence"] = min(max(confidence, 0.0), 1.0)
    applicable = {key: weight for key, weight in WEIGHTS.items() if key in bounded}
    total_weight = sum(applicable.values())
    weights_used = {key: weight / total_weight for key, weight in applicable.items()}
    score = round(100 * sum(bounded[key] * weight for key, weight in weights_used.items()), 1)
    level = (
        "CRITICAL" if score >= 80 else "HIGH" if score >= 65 else "MEDIUM" if score >= 40 else "LOW"
    )
    factors: list[str] = []
    if bounded["severity"] >= 0.75:
        factors.append("Severe observation recorded")
    if recurrence >= 3:
        factors.append(f"Repeated across {recurrence} inspections")
    if bounded["criticality"] >= 0.8:
        factors.append("High asset criticality")
    if bounded["trend"] >= 0.6:
        factors.append("Condition deterioration increased")
    if bounded["geographic_impact"] >= 0.6:
        factors.append("Located in a concentrated problem area")
    if confidence is None:
        factors.append(
            "Observation confidence NOT AVAILABLE; excluded from the score and the "
            "remaining weights renormalised"
        )
    if not factors:
        factors.append("Routine monitoring priority based on current evidence")
    return PriorityResult(
        score=score,
        level=level,
        factors=factors,
        components={key: round(value, 3) for key, value in bounded.items()},
        formula=" + ".join(f"{weight:.2f}×{key}" for key, weight in sorted(weights_used.items())),
    )
