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
flights). No telemetry field is fabricated when absent — missing data lowers confidence
in that dimension and is stated explicitly, never silently defaulted to a good score.
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


def _combine(components: dict[str, float], weights: ReliabilityWeights) -> dict[str, float]:
    """Same combination mechanic as aeris.autonomy.safety.risk.combine_risk, applied to
    reliability dimensions (which score *good* as high, unlike risk which scores *bad*
    as high) — kept as a local copy because the two use inverted score polarity and
    importing combine_risk directly would silently invert the meaning of "weighted"."""
    weighted = {
        name: max(0.0, min(1.0, components.get(name, 0.0))) * value
        for name, value in asdict(weights).items()
    }
    return {
        **components,
        **{f"weighted_{key}": value for key, value in weighted.items()},
        "total": sum(weighted.values()),
    }


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
        interpretation = (
            f"The visual model detected '{label}' with {confidence:.0%} confidence. No telemetry "
            "was ingested for this mission, so reliability cannot be assessed."
        )
        action = (
            "Ingest mission telemetry, or treat this finding as unverified "
            "until reliability is known."
        )
    return {
        "interpretation": interpretation,
        "recommended_action": action,
        "reliability_level": level,
    }


def assess_mission_reliability(
    telemetry_rows: list[dict], weights: ReliabilityWeights = DEFAULT_WEIGHTS
) -> dict:
    """telemetry_rows: dicts shaped like TelemetryIngest (gnss_quality, satellite_count,
    hdop, camera_confidence, normalized_innovation_squared, packet_delay_s, packet_loss,
    battery_percent, origin). Returns a score, level, weighted components, and a list of
    plain-language reasons — never an unexplained number."""
    reasons: list[str] = []
    components: dict[str, float] = {}

    is_simulation = any(
        row.get("origin") in (DataOrigin.SIMULATION, DataOrigin.SYNTHETIC_FAULT)
        for row in telemetry_rows
    )

    if not telemetry_rows:
        return {
            "level": ReliabilityLevel.UNKNOWN,
            "score": None,
            "components": {},
            "reasons": ["No telemetry recorded for this mission; reliability cannot be assessed."],
            "is_simulation": False,
            "sample_count": 0,
        }

    # Navigation reliability: derived from GNSS quality and NIS consistency when present.
    nis_values = [
        r["normalized_innovation_squared"]
        for r in telemetry_rows
        if r.get("normalized_innovation_squared") is not None
    ]
    gnss_values = [r["gnss_quality"] for r in telemetry_rows if r.get("gnss_quality") is not None]
    if nis_values:
        mean_nis = sum(nis_values) / len(nis_values)
        nav_score = max(0.0, 1.0 - min(1.0, mean_nis / NIS_EXCURSION_DIVISOR))
        excursions = sum(1 for v in nis_values if v / NIS_EXCURSION_DIVISOR >= 0.8)
        if excursions:
            reasons.append(
                f"⚠ GNSS/navigation consistency degraded "
                f"({excursions} innovation excursion(s) detected)"
            )
        else:
            reasons.append("✓ Navigation consistency (NIS) within expected bounds")
    elif gnss_values:
        nav_score = sum(gnss_values) / len(gnss_values)
        reasons.append(
            f"GNSS quality reported directly (mean={nav_score:.2f}); "
            "no NIS consistency signal available"
        )
    else:
        nav_score = 0.5
        reasons.append(
            "⚠ No GNSS quality or navigation consistency data available; neutral value used"
        )
    components["navigation"] = nav_score

    # Sensor consistency: camera confidence as a proxy signal.
    camera_values = [
        r["camera_confidence"] for r in telemetry_rows if r.get("camera_confidence") is not None
    ]
    if camera_values:
        sensor_score = sum(camera_values) / len(camera_values)
        reasons.append(
            "✓ Camera data complete"
            if sensor_score >= 0.7
            else "⚠ Camera confidence below expected range"
        )
    else:
        sensor_score = 0.5
        reasons.append("⚠ No sensor-confidence telemetry reported; neutral value used")
    components["sensor_consistency"] = sensor_score

    # Telemetry continuity: packet loss/delay.
    loss_count = sum(1 for r in telemetry_rows if r.get("packet_loss"))
    delay_values = [
        r["packet_delay_s"] for r in telemetry_rows if r.get("packet_delay_s") is not None
    ]
    excessive_delay = sum(1 for v in delay_values if v > MAX_PACKET_DELAY_S)
    gaps = loss_count + excessive_delay
    continuity_score = max(0.0, 1.0 - min(1.0, gaps / max(len(telemetry_rows), 1)))
    if gaps:
        reasons.append(f"⚠ {gaps} telemetry gap(s)/excess-delay event(s) detected")
    else:
        reasons.append("✓ Telemetry stream continuous, no gaps detected")
    components["telemetry_continuity"] = continuity_score

    # Battery/power.
    battery_values = [
        r["battery_percent"] for r in telemetry_rows if r.get("battery_percent") is not None
    ]
    if battery_values:
        min_battery = min(battery_values)
        battery_score = min_battery / 100.0
        reasons.append(
            "✓ Battery remained within expected operating range"
            if min_battery >= 20
            else f"⚠ Battery dropped to {min_battery:.0f}% during mission"
        )
    else:
        battery_score = 0.5
        reasons.append("⚠ No battery telemetry reported; neutral value used")
    components["battery_power"] = battery_score

    # Data completeness: fraction of expected fields present across rows.
    tracked_fields = (
        "gnss_quality",
        "camera_confidence",
        "battery_percent",
        "normalized_innovation_squared",
    )
    present = sum(1 for r in telemetry_rows for f in tracked_fields if r.get(f) is not None)
    possible = len(telemetry_rows) * len(tracked_fields)
    completeness_score = present / possible if possible else 0.0
    components["data_completeness"] = completeness_score
    reasons.append(
        f"Data completeness: {completeness_score * 100:.0f}% of tracked telemetry fields "
        f"present across {len(telemetry_rows)} record(s)"
    )

    combined = _combine(components, weights)
    score = round(combined["total"] * 100, 1)
    level = (
        ReliabilityLevel.HIGH
        if score >= 75
        else ReliabilityLevel.MEDIUM
        if score >= 50
        else ReliabilityLevel.LOW
    )

    return {
        "level": level,
        "score": score,
        "components": {k: round(v, 3) for k, v in components.items()},
        "weighted_components": {
            k: round(v, 3) for k, v in combined.items() if k.startswith("weighted_")
        },
        "formula": " + ".join(f"{w:.2f}×{k}" for k, w in asdict(weights).items()),
        "reasons": reasons,
        "is_simulation": is_simulation,
        "sample_count": len(telemetry_rows),
    }
