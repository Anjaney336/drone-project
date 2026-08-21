"""Plain-language presentation helpers.

Extracted from the retired Streamlit dashboard, which was a second UI generation left
over from the autonomy-project era. The functions themselves are not Streamlit-specific:
they encode a product requirement that survives the UI that first used them — operational
state is explained in words a non-specialist can act on, and a value the backend did not
supply is reported as unavailable rather than replaced by a guess.
"""

from __future__ import annotations

from aeris.models import DataOrigin

UNAVAILABLE = "DATA UNAVAILABLE"


def show(value: object, suffix: str = "") -> str:
    return UNAVAILABLE if value is None else f"{value}{suffix}"


def provenance_label(origin: str | None) -> str:
    mapping = {
        DataOrigin.MEASURED.value: "MEASURED TELEMETRY",
        DataOrigin.PUBLIC_BENCHMARK.value: "PUBLIC BENCHMARK",
        DataOrigin.SIMULATION.value: "SIMULATED TELEMETRY",
        DataOrigin.SYNTHETIC.value: "SYNTHETIC SAMPLE",
        DataOrigin.SYNTHETIC_FAULT.value: "SYNTHETIC-FAULT TELEMETRY",
    }
    return mapping.get(origin, "SOURCE UNAVAILABLE")


def plain_safety_status(state: str | None) -> tuple[str, str]:
    mapping = {
        "NORMAL": ("✅ Safe", "Sensors agree and no safety rule is active."),
        "RECOVERY": ("🟦 Recovering", "AERIS is confirming that sensor readings are stable."),
        "DEGRADED": ("⚠️ Degraded — monitoring", "One or more inputs are less trustworthy."),
        "ANOMALY_DETECTED": (
            "⚠️ Degraded — monitoring",
            "A sensor disagrees with the expected motion, so AERIS reduced its influence.",
        ),
        "COLLISION_RISK": ("🚨 Action recommended", "The predicted path indicates collision risk."),
        "GEOFENCE_RISK": ("🚨 Action recommended", "The predicted path approaches a boundary."),
        "SAFE_RESPONSE": ("🚨 Action recommended", "A deterministic safety rule is active."),
    }
    return mapping.get(state, (UNAVAILABLE, "No backend safety state is available."))


def unavailable_explanation(row: dict, sensor: str | None = None) -> str:
    health = row.get("sensor_health") or {}
    if sensor == "gnss" and (row.get("gnss_quality") is None or health.get("gnss") == 0):
        return "GNSS is unavailable; the estimate is relying on remaining sensor inputs."
    if sensor == "camera" and row.get("camera_confidence") is None:
        return "Camera observations are unavailable; visual confirmation cannot be used."
    if sensor == "imu" and "imu" not in health:
        return "IMU supports motion prediction; this prototype does not compute separate IMU trust."
    return "The backend did not provide this value; AERIS does not substitute a guessed value."


def fault_summary(row: dict, records: list[dict]) -> str:
    if row.get("injected_fault"):
        return str(row["injected_fault"]).replace("_", " ").title() + " (active now)"
    prior = next(
        (item.get("injected_fault") for item in records if item.get("injected_fault")), None
    )
    if prior:
        return str(prior).replace("_", " ").title() + " (earlier; now inactive)"
    return "None (nominal scenario)"
