"""Mission Reliability Engine.

Answers "can we trust this mission's data?" as an explainable score, not a black box.
Reuses the generic weighted-decomposition pattern from `aeris.autonomy.safety.risk`
(`combine_risk`) directly — same mechanism the Digital Twin uses for its risk score,
repointed at reliability dimensions instead of interception risk. NIS thresholds echo
`aeris.autonomy.anomaly.detector.SensorHealthMonitor`'s innovation-excursion threshold
(nis/25.0) for consistency with the Digital Twin's own anomaly evidence, since a mission
run through the Digital Twin will produce directly comparable numbers.

This module does NOT re-run the EKF against product telemetry: `TelemetryIngest.
normalized_innovation_squared` is consumed as a value the caller supplies (produced by
the Digital Twin when a mission is simulated, or by a future onboard estimator for real
flights). No telemetry field is fabricated when absent: a dimension with no supporting
telemetry is reported as NOT AVAILABLE and dropped from the score entirely, and the
remaining weights are renormalised over the dimensions that could actually be assessed.
A dimension is never given a neutral or optimistic stand-in value, because a score
computed from invented inputs is indistinguishable from one computed from real ones.

If no substantive dimension can be assessed, the result is UNKNOWN with a null score —
never a number. `data_completeness` alone is not enough to call a mission reliable or
unreliable; it only describes how much of the telemetry arrived.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from aeris.app.product_models import ReliabilityLevel
from aeris.models import DataOrigin


@dataclass(frozen=True, slots=True)
class ReliabilityWeights:
    navigation: float = 0.30
    sensor_consistency: float = 0.20
    telemetry_continuity: float = 0.20
    battery_power: float = 0.15
    data_completeness: float = 0.15

    def __post_init__(self) -> None:
        if abs(sum(asdict(self).values()) - 1.0) > 1e-9:
            raise ValueError("Reliability weights must sum to 1.0")


DEFAULT_WEIGHTS = ReliabilityWeights()
NIS_EXCURSION_DIVISOR = 25.0  # matches SensorHealthMonitor's innovation-excursion scaling
MAX_PACKET_DELAY_S = 0.5  # matches SensorHealthMonitor.max_packet_delay_s default


NOT_AVAILABLE = "NOT AVAILABLE"

# data_completeness describes how much telemetry arrived, not whether the flight was
# sound. On its own it cannot justify a reliability verdict, so at least one of these
# must be assessable before any score is produced.
SUBSTANTIVE_DIMENSIONS = (
    "navigation",
    "sensor_consistency",
    "telemetry_continuity",
    "battery_power",
)


def _combine(
    components: dict[str, float], weights: ReliabilityWeights
) -> tuple[dict[str, float], dict[str, float]]:
    """Weighted decomposition over the assessed dimensions only.

    Same combination mechanic as aeris.autonomy.safety.risk.combine_risk, applied to
    reliability dimensions (which score *good* as high, unlike risk which scores *bad*
    as high) — kept as a local copy because the two use inverted score polarity and
    importing combine_risk directly would silently invert the meaning of "weighted".

    Dimensions absent from `components` are NOT AVAILABLE. They are excluded rather
    than zero-filled, and the remaining weights are renormalised to sum to 1.0, so a
    mission assessed on two dimensions is scored out of those two dimensions instead of
    being penalised for telemetry it never claimed to carry.
    """
    declared = asdict(weights)
    applicable = {name: w for name, w in declared.items() if name in components}
    total_weight = sum(applicable.values())
    if not total_weight:
        return {}, {}
    normalised = {name: w / total_weight for name, w in applicable.items()}
    weighted = {
        name: max(0.0, min(1.0, components[name])) * weight for name, weight in normalised.items()
    }
    return weighted, normalised


def interpret_finding(label: str, confidence: float, reliability: dict) -> dict:
    """Combine an AI finding with its mission's reliability into a human-readable
    interpretation and recommended action — this is the part that matters more than a
    bare confidence number: a confident finding from an unreliable mission is not the
    same thing as a confident finding from a reliable one."""
    level = reliability.get("level", "UNKNOWN")
    if level == "HIGH":
        interpretation = (
            f"The visual model detected '{label}' with {confidence:.0%} confidence, and mission "
            "telemetry quality was HIGH — this finding can be treated as reasonably actionable."
        )
        action = "Proceed with standard engineering review of the flagged evidence."
    elif level == "MEDIUM":
        interpretation = (
            f"The visual model detected '{label}' with {confidence:.0%} confidence. Mission "
            "reliability was MEDIUM — some telemetry signals were degraded or incomplete."
        )
        action = "Review the evidence alongside the mission reliability reasons before escalating."
    elif level == "LOW":
        interpretation = (
            f"The visual model detected '{label}' with {confidence:.0%} confidence, but mission "
            "telemetry quality was LOW — navigation, sensor, or telemetry signals were degraded "
            "during this mission."
        )
        action = (
            "Reinspect before operational escalation. Do not treat this finding as "
            "confirmed evidence on its own."
        )
    else:
        # UNKNOWN has two distinct causes and the operator needs to know which:
        # no telemetry at all, or telemetry that carried nothing assessable.
        if reliability.get("sample_count"):
            missing = ", ".join(sorted(reliability.get("unavailable_components", {}))) or "any"
            interpretation = (
                f"The visual model detected '{label}' with {confidence:.0%} confidence. "
                f"Telemetry was ingested for this mission, but none of it supported a "
                f"reliability assessment ({missing} could not be assessed), so mission "
                "reliability is UNKNOWN."
            )
            action = (
                "Supply telemetry covering at least one of GNSS/NIS, camera confidence, "
                "packet loss or battery, or treat this finding as unverified."
            )
        else:
            interpretation = (
                f"The visual model detected '{label}' with {confidence:.0%} confidence. "
                "No telemetry was ingested for this mission, so reliability cannot be assessed."
            )
            action = (
                "Ingest mission telemetry, or treat this finding as unverified until "
                "reliability is known."
            )
    return {
        "interpretation": interpretation,
        "recommended_action": action,
        "reliability_level": level,
    }


def assess_mission_reliability(
    telemetry_rows: list[dict], weights: ReliabilityWeights = DEFAULT_WEIGHTS
) -> dict:
    """Score how far this mission's telemetry can be trusted.

    telemetry_rows: dicts shaped like TelemetryIngest (gnss_quality, satellite_count,
    hdop, camera_confidence, normalized_innovation_squared, packet_delay_s, packet_loss,
    battery_percent, origin).

    Every dimension is either assessed from real values or reported in
    `unavailable_components` with the reason it could not be assessed. Nothing is
    defaulted, so a telemetry file carrying only timestamps returns UNKNOWN with a null
    score rather than a middling number that looks like a measurement.
    """
    reasons: list[str] = []
    components: dict[str, float] = {}
    unavailable: dict[str, str] = {}

    if not telemetry_rows:
        return {
            "level": ReliabilityLevel.UNKNOWN,
            "score": None,
            "components": {},
            "unavailable_components": {
                name: "No telemetry recorded for this mission" for name in asdict(weights)
            },
            "weighted_components": {},
            "weights_used": {},
            "formula": "",
            "reasons": ["No telemetry recorded for this mission; reliability cannot be assessed."],
            "is_simulation": False,
            "sample_count": 0,
        }

    is_simulation = any(
        row.get("origin") in (DataOrigin.SIMULATION, DataOrigin.SYNTHETIC_FAULT)
        for row in telemetry_rows
    )

    def values_of(field: str) -> list[float]:
        return [r[field] for r in telemetry_rows if r.get(field) is not None]

    # Navigation: NIS consistency preferred, GNSS quality as a fallback signal.
    nis_values = values_of("normalized_innovation_squared")
    gnss_values = values_of("gnss_quality")
    if nis_values:
        mean_nis = sum(nis_values) / len(nis_values)
        components["navigation"] = max(0.0, 1.0 - min(1.0, mean_nis / NIS_EXCURSION_DIVISOR))
        excursions = sum(1 for v in nis_values if v / NIS_EXCURSION_DIVISOR >= 0.8)
        if excursions:
            reasons.append(
                f"⚠ GNSS/navigation consistency degraded "
                f"({excursions} innovation excursion(s) detected)"
            )
        else:
            reasons.append("✓ Navigation consistency (NIS) within expected bounds")
    elif gnss_values:
        mean_gnss = sum(gnss_values) / len(gnss_values)
        components["navigation"] = mean_gnss
        reasons.append(
            f"GNSS quality reported directly (mean={mean_gnss:.2f}); "
            "no NIS consistency signal available"
        )
    else:
        unavailable["navigation"] = "No gnss_quality or normalized_innovation_squared reported"
        reasons.append(f"{NOT_AVAILABLE}: navigation — no GNSS quality or NIS values in telemetry")

    # Sensor consistency: camera confidence as a proxy signal.
    camera_values = values_of("camera_confidence")
    if camera_values:
        sensor_score = sum(camera_values) / len(camera_values)
        components["sensor_consistency"] = sensor_score
        reasons.append(
            "✓ Camera data complete"
            if sensor_score >= 0.7
            else "⚠ Camera confidence below expected range"
        )
    else:
        unavailable["sensor_consistency"] = "No camera_confidence reported"
        reasons.append(f"{NOT_AVAILABLE}: sensor consistency — no camera_confidence in telemetry")

    # Telemetry continuity: only assessable if the stream actually reported loss/delay.
    # Absence of a packet_loss column is not evidence of an unbroken stream, so it must
    # not score as one.
    continuity_rows = [
        r
        for r in telemetry_rows
        if r.get("packet_loss") is not None or r.get("packet_delay_s") is not None
    ]
    if continuity_rows:
        # Count degraded *records*, not events: a record that both lost a packet and
        # exceeded the delay budget is one bad record, not two, or the reported count
        # can exceed the number of records it was measured over.
        degraded = sum(
            1
            for r in continuity_rows
            if r.get("packet_loss")
            or (r.get("packet_delay_s") is not None and r["packet_delay_s"] > MAX_PACKET_DELAY_S)
        )
        components["telemetry_continuity"] = 1.0 - (degraded / len(continuity_rows))
        if degraded:
            reasons.append(
                f"⚠ {degraded} of {len(continuity_rows)} reporting record(s) showed packet "
                f"loss or delay above {MAX_PACKET_DELAY_S}s"
            )
        else:
            reasons.append(
                f"✓ Telemetry stream continuous across {len(continuity_rows)} reporting record(s)"
            )
    else:
        unavailable["telemetry_continuity"] = "No packet_loss or packet_delay_s reported"
        reasons.append(
            f"{NOT_AVAILABLE}: telemetry continuity — no packet_loss or packet_delay_s "
            "in telemetry, so stream integrity cannot be confirmed"
        )

    # Battery / power.
    battery_values = values_of("battery_percent")
    if battery_values:
        min_battery = min(battery_values)
        components["battery_power"] = min_battery / 100.0
        reasons.append(
            "✓ Battery remained within expected operating range"
            if min_battery >= 20
            else f"⚠ Battery dropped to {min_battery:.0f}% during mission"
        )
    else:
        unavailable["battery_power"] = "No battery_percent reported"
        reasons.append(f"{NOT_AVAILABLE}: battery — no battery_percent in telemetry")

    # Data completeness: how much of the tracked telemetry arrived. Reported always, but
    # only scored alongside at least one substantive dimension.
    tracked_fields = (
        "gnss_quality",
        "camera_confidence",
        "battery_percent",
        "normalized_innovation_squared",
    )
    present = sum(1 for r in telemetry_rows for f in tracked_fields if r.get(f) is not None)
    possible = len(telemetry_rows) * len(tracked_fields)
    completeness_score = present / possible if possible else 0.0
    reasons.append(
        f"Data completeness: {completeness_score * 100:.0f}% of tracked telemetry fields "
        f"present across {len(telemetry_rows)} record(s)"
    )

    assessed_substantive = [name for name in SUBSTANTIVE_DIMENSIONS if name in components]
    if not assessed_substantive:
        unavailable["data_completeness"] = (
            "Not scored on its own; no substantive dimension could be assessed"
        )
        reasons.append(
            "Reliability cannot be assessed: none of navigation, sensor consistency, "
            "telemetry continuity or battery had any supporting telemetry."
        )
        return {
            "level": ReliabilityLevel.UNKNOWN,
            "score": None,
            "components": {},
            "unavailable_components": unavailable,
            "weighted_components": {},
            "weights_used": {},
            "formula": "",
            "reasons": reasons,
            "is_simulation": is_simulation,
            "sample_count": len(telemetry_rows),
        }

    components["data_completeness"] = completeness_score
    weighted, normalised = _combine(components, weights)
    score = round(sum(weighted.values()) * 100, 1)
    level = (
        ReliabilityLevel.HIGH
        if score >= 75
        else ReliabilityLevel.MEDIUM
        if score >= 50
        else ReliabilityLevel.LOW
    )
    if unavailable:
        reasons.append(
            f"Score computed over {len(components)} of {len(asdict(weights))} dimensions; "
            f"weights renormalised. Not assessed: {', '.join(sorted(unavailable))}."
        )

    return {
        "level": level,
        "score": score,
        "components": {k: round(v, 3) for k, v in components.items()},
        "unavailable_components": unavailable,
        "weighted_components": {f"weighted_{k}": round(v, 3) for k, v in weighted.items()},
        "weights_used": {k: round(v, 3) for k, v in normalised.items()},
        "formula": " + ".join(f"{w:.2f}×{k}" for k, w in sorted(normalised.items())),
        "reasons": reasons,
        "is_simulation": is_simulation,
        "sample_count": len(telemetry_rows),
    }
