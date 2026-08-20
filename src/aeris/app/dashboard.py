from __future__ import annotations

import os

import altair as alt
import httpx
import streamlit as st

from aeris.models import DataOrigin
from aeris.simulation.scenarios import available_scenarios

UNAVAILABLE = "DATA UNAVAILABLE"
VARIANT_LABELS = {
    "raw_measurements": "Raw fusion",
    "ekf_fixed": "Fixed EKF",
    "ekf_hard_rejection": "Hard rejection",
    "aeris_adaptive": "AERIS adaptive",
}


def show(value: object, suffix: str = "") -> str:
    return UNAVAILABLE if value is None else f"{value}{suffix}"


def _get(api: str, path: str) -> dict:
    return httpx.get(f"{api}{path}", timeout=5).raise_for_status().json()


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


def friendly_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return "That mission ID was not found. Try the example mission or check the ID and retry."
    return "The AERIS API cannot be reached. Start the API, then refresh this page."


def fault_summary(row: dict, records: list[dict]) -> str:
    if row.get("injected_fault"):
        return str(row["injected_fault"]).replace("_", " ").title() + " (active now)"
    prior = next(
        (item.get("injected_fault") for item in records if item.get("injected_fault")), None
    )
    if prior:
        return str(prior).replace("_", " ").title() + " (earlier; now inactive)"
    return "None (nominal scenario)"


def guided_indices(records: list[dict]) -> dict[str, int]:
    fault = next(
        (
            index
            for index, row in enumerate(records)
            if row.get("injected_fault") and row.get("anomaly_label")
        ),
        next((i for i, row in enumerate(records) if row.get("injected_fault")), 0),
    )
    recovery = next(
        (
            index
            for index in range(fault + 1, len(records))
            if records[index].get("safety_state") == "RECOVERY"
        ),
        len(records) - 1,
    )
    return {"1 · Initialize": 0, "2 · Fault detected": fault, "3 · Recovery": recovery}


def current_story(row: dict, snapshot: dict) -> str:
    scenario = str(row.get("scenario_id") or "unknown scenario").replace("_", " ")
    fault = row.get("injected_fault")
    health = row.get("sensor_health") or {}
    action = (snapshot.get("safety_decision") or {}).get("action", UNAVAILABLE)
    if fault:
        affected = "GNSS" if "gnss" in str(fault) else "a sensor"
        trust = health.get("gnss") if affected == "GNSS" else None
        trust_text = ""
        if trust is not None:
            trust_text = f" Its adaptive trust is now {float(trust) * 100:.0f}%."
        return (
            f"A synthetic fault is active in {scenario}: {affected} is unreliable.{trust_text} "
            f"AERIS detected the disagreement instead of blindly fusing it and recommends "
            f"{str(action).replace('_', ' ').lower()}."
        )
    if row.get("safety_state") == "RECOVERY":
        return (
            f"The injected fault in {scenario} has cleared. AERIS is holding while it confirms "
            "that sensor agreement and estimator confidence remain stable."
        )
    return (
        f"AERIS is tracking a simulated {scenario} flight. Current sensor evidence satisfies "
        "the configured safety rules, so the deterministic policy recommends continuing."
    )


def benchmark_rows(benchmark: dict) -> list[dict]:
    rows = []
    for variant, label in VARIANT_LABELS.items():
        summary = (benchmark.get("aggregate") or {}).get(variant, {}).get("position_rmse_m")
        if summary:
            rows.append(
                {
                    "method": label,
                    "rmse_m": summary["mean"],
                    "ci_low_m": summary["ci95_low"],
                    "ci_high_m": summary["ci95_high"],
                }
            )
    return rows


def render_benchmark_chart(benchmark: dict) -> None:
    rows = benchmark_rows(benchmark)
    if not rows:
        st.info("Benchmark evidence is unavailable. Generate artifacts/benchmark.json first.")
        return
    order = list(VARIANT_LABELS.values())
    base = alt.Chart(alt.Data(values=rows)).encode(
        x=alt.X("method:N", sort=order, title=None),
        tooltip=[
            alt.Tooltip("method:N", title="Method"),
            alt.Tooltip("rmse_m:Q", title="Mean RMSE (m)", format=".3f"),
            alt.Tooltip("ci_low_m:Q", title="95% CI low", format=".3f"),
            alt.Tooltip("ci_high_m:Q", title="95% CI high", format=".3f"),
        ],
    )
    bars = base.mark_bar().encode(
        y=alt.Y("rmse_m:Q", title="Position RMSE (m); lower is better"),
        color=alt.Color(
            "method:N",
            scale=alt.Scale(
                domain=order,
                range=["#64748b", "#3b82f6", "#f59e0b", "#16a34a"],
            ),
            legend=None,
        ),
    )
    errors = base.mark_rule(color="#111827", strokeWidth=2).encode(
        y=alt.Y("ci_low_m:Q"), y2="ci_high_m:Q"
    )
    st.altair_chart((bars + errors).properties(height=270), width="stretch")
    st.caption(
        "🏷️ BENCHMARK RESULT · Source: artifacts/benchmark.json · Simulation benchmark, not "
        "field performance. Error bars are normal-approximation 95% confidence intervals."
    )
    with st.expander("How was RMSE calculated?"):
        start = benchmark.get("paired_seed_start", 7)
        trials = benchmark.get("trials", UNAVAILABLE)
        end = start + trials - 1 if isinstance(trials, int) else UNAVAILABLE
        st.write(
            "Root-mean-square distance between the estimated and exact simulated position. "
            f"The report aggregates {trials} paired trials, seeds {start}–{end}; every method "
            "received the same sensor stream for each seed."
        )


def render_trajectory(records: list[dict], snapshots: list[dict], end_index: int) -> None:
    values = []
    for row, snapshot in zip(records[: end_index + 1], snapshots[: end_index + 1], strict=False):
        estimate, truth = row.get("position_m"), snapshot.get("true_position_m")
        if estimate:
            values.append({"x_m": estimate[0], "y_m": estimate[1], "path": "AERIS estimate"})
        if truth:
            values.append({"x_m": truth[0], "y_m": truth[1], "path": "Exact simulation truth"})
    if not values:
        st.info(UNAVAILABLE)
        return
    chart = (
        alt.Chart(alt.Data(values=values))
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("x_m:Q", title="East position (m)"),
            y=alt.Y("y_m:Q", title="North position (m)"),
            color=alt.Color(
                "path:N",
                scale=alt.Scale(
                    domain=["Exact simulation truth", "AERIS estimate"],
                    range=["#111827", "#16a34a"],
                ),
            ),
            tooltip=[
                "path:N",
                alt.Tooltip("x_m:Q", format=".2f"),
                alt.Tooltip("y_m:Q", format=".2f"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "🏷️ SIMULATED TRUTH + ESTIMATED STATE · Truth comes from the seeded simulator; the "
        "green path comes from the adaptive EKF. Neither is flight telemetry."
    )


def render_trust_chart(records: list[dict]) -> None:
    values = []
    for row in records:
        for sensor, trust in (row.get("sensor_health") or {}).items():
            values.append({"time_s": row["timestamp"], "sensor": sensor.upper(), "trust": trust})
    if not values:
        st.info(UNAVAILABLE)
        return
    chart = (
        alt.Chart(alt.Data(values=values))
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("time_s:Q", title="Simulation time (s)"),
            y=alt.Y("trust:Q", title="Adaptive trust (0 = ignored, 1 = fully trusted)"),
            color=alt.Color("sensor:N", scale=alt.Scale(range=["#2563eb", "#f59e0b"])),
            tooltip=[
                "sensor:N",
                alt.Tooltip("time_s:Q", format=".1f"),
                alt.Tooltip("trust:Q", format=".3f"),
            ],
        )
        .properties(height=240)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "🏷️ ESTIMATED FROM SIMULATED TELEMETRY · Trust falls when a sensor disagrees with the "
        "predicted motion and recovers gradually after agreement returns."
    )


def render_fault_timeline(records: list[dict]) -> None:
    values = []
    for row in records:
        if row.get("injected_fault"):
            values.append({"time_s": row["timestamp"], "event": "Synthetic fault active"})
        if row.get("anomaly_label"):
            values.append({"time_s": row["timestamp"], "event": "AERIS anomaly flag"})
    if not values:
        st.info("No synthetic fault or anomaly flag occurred in this scenario.")
        return
    chart = (
        alt.Chart(alt.Data(values=values))
        .mark_tick(thickness=4, size=35)
        .encode(
            x=alt.X("time_s:Q", title="Simulation time (s)"),
            y=alt.Y("event:N", title=None),
            color=alt.Color(
                "event:N",
                scale=alt.Scale(
                    domain=["Synthetic fault active", "AERIS anomaly flag"],
                    range=["#dc2626", "#f59e0b"],
                ),
                legend=None,
            ),
            tooltip=["event:N", alt.Tooltip("time_s:Q", format=".1f")],
        )
        .properties(height=120)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        "🏷️ SYNTHETIC-FAULT TELEMETRY · Red marks the configured injected-fault interval; "
        "amber marks when backend anomaly evidence fired. Their offset is detection latency."
    )


def render_synthetic_preview(api: str, preview: dict) -> None:
    st.subheader("Synthetic dataset evidence")
    st.write(
        "Real synchronized AERIS flight data is not yet available. This held-out sample exercises "
        "the data pipeline using explicitly synthetic IMU/GNSS-like records; no imagery is "
        "fabricated."
    )
    if preview.get("data_status") != "AVAILABLE":
        st.info("Synthetic preview is unavailable. Run scripts/generate_synthetic_data.py first.")
        return
    values = [
        {
            "time_s": row["timestamp_s"],
            "signal": "IMU acceleration x (m/s²)",
            "value": row["imu_accel_x_mps2"],
        }
        for row in preview["records"]
    ]
    chart = (
        alt.Chart(alt.Data(values=values))
        .mark_line(point=True, color="#7c3aed")
        .encode(
            x=alt.X("time_s:Q", title="Synthetic sample time (s)"),
            y=alt.Y("value:Q", title="IMU acceleration x (m/s²)"),
            tooltip=[alt.Tooltip("time_s:Q", format=".1f"), alt.Tooltip("value:Q", format=".4f")],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, width="stretch")
    validation = "PASSED" if preview.get("validation_passed") else "NOT AVAILABLE / FAILED"
    st.caption(
        f"🏷️ SYNTHETIC SAMPLE · Held-out split · Statistical validation: {validation}. "
        "IMU acceleration includes cited BMI088 white-noise density plus an explicitly estimated "
        "Gauss–Markov bias model."
    )
    st.link_button(
        "Open synthetic validation artifact",
        f"{api}{preview.get('validation_artifact', '/artifacts/synthetic-validation')}",
    )
    st.caption("Method and citations: docs/synthetic_data.md")


def main() -> None:
    st.set_page_config(page_title="AERIS Research Command Center", layout="wide")
    st.title("AERIS — Adaptive Edge Resilience & Intelligence System")
    st.caption(
        "Reliable drone safety under uncertain sensors · Research prototype · "
        "Simulation ≠ field evidence"
    )
    api = os.getenv("AERIS_API_URL", "http://127.0.0.1:8000")
    view = st.radio(
        "Detail level",
        ["Basic", "Advanced"],
        horizontal=True,
        help="Basic tells the safety story; Advanced exposes estimator and validation evidence.",
    )
    with st.sidebar:
        st.header("Start here")
        example = st.button("▶ Try an example mission", type="primary", width="stretch")
        st.caption("One click runs the fixed GNSS-drift example with seed 7.")
        st.divider()
        st.subheader("Choose another simulation")
        scenario = st.selectbox(
            "Scenario",
            available_scenarios(),
            index=available_scenarios().index("gnss_drift"),
            help="The simulated operating condition and injected synthetic fault, if any.",
        )
        seed = st.number_input(
            "Reproducibility seed",
            min_value=0,
            value=7,
            step=1,
            help="The same seed produces the same simulated sensor stream.",
        )
        run_selected = st.button("Run selected simulation", width="stretch")
        if example or run_selected:
            try:
                response = (
                    httpx.post(
                        f"{api}/missions",
                        json={
                            "scenario_id": "gnss_drift" if example else scenario,
                            "seed": 7 if example else int(seed),
                        },
                        timeout=30,
                    )
                    .raise_for_status()
                    .json()
                )
                st.session_state["active_mission_id"] = response["mission_id"]
                st.session_state["guided_mode"] = bool(example)
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(friendly_error(exc))
        with st.expander("Open an existing mission"):
            entered_mission_id = st.text_input(
                "Mission ID",
                key="entered_mission_id",
                placeholder="Example: 550e8400-e29b-41d4-a716-446655440000",
            )
        mission_id = st.session_state.get("active_mission_id") or entered_mission_id
        st.caption("Mission values are read from the AERIS API; the UI does not create telemetry.")

    if not mission_id:
        st.info(
            "AERIS monitors a simulated drone, lowers trust in unreliable sensors, predicts its "
            "path, and recommends an explainable safety action. It is not flight-tested and never "
            "controls hardware. Select **Try an example mission** to see the full story."
        )
        return
    try:
        state = _get(api, f"/missions/{mission_id}/state")
        metrics = _get(api, f"/missions/{mission_id}/metrics")["values"]
        events = _get(api, f"/missions/{mission_id}/events")["events"]
        history = _get(api, f"/missions/{mission_id}/telemetry")
        benchmark = _get(api, "/benchmark")
        preview = _get(api, "/synthetic-data-preview") if view == "Advanced" else {}
    except httpx.HTTPError as exc:
        st.error(friendly_error(exc))
        return
    except (KeyError, ValueError):
        st.error("The API returned incomplete data. Re-run the mission or check the API logs.")
        return

    records, snapshots = history.get("records", []), history.get("snapshots", [])
    if not records:
        st.info("Mission telemetry is unavailable; AERIS will not display substitute values.")
        return
    indices = guided_indices(records)
    if st.session_state.get("guided_mode"):
        moment = st.radio(
            "Guided mission moment",
            list(indices),
            index=1,
            horizontal=True,
            help="Move between initialization, the detected fault, and recovery.",
        )
        selected_index = indices[moment]
    elif view == "Advanced":
        selected_index = st.slider(
            "Simulation playback step",
            0,
            len(records) - 1,
            len(records) - 1,
            help="Selects a backend telemetry record; it does not recompute mission state.",
        )
    else:
        selected_index = len(records) - 1
    row = records[selected_index]
    snapshot = snapshots[selected_index] if selected_index < len(snapshots) else {}
    origin = row.get("origin")

    st.info(
        "**What is AERIS doing right now?**  "
        + current_story(row, snapshot)
        + " This is a deterministic simulation demonstration, not a flight-tested system."
    )
    st.caption(
        f"🏷️ {provenance_label(origin)} · Backend record at simulation time "
        f"{float(row['timestamp']):.1f} s · Scenario {row.get('scenario_id')} · "
        f"Seed {row.get('seed')}"
    )

    status_label, status_reason = plain_safety_status(row.get("safety_state"))
    if str(row.get("safety_state")) in {"COLLISION_RISK", "GEOFENCE_RISK", "SAFE_RESPONSE"}:
        st.error(f"## {status_label}\n{status_reason}")
    elif str(row.get("safety_state")) in {"DEGRADED", "ANOMALY_DETECTED"}:
        st.warning(f"## {status_label}\n{status_reason}")
    elif row.get("safety_state") == "RECOVERY":
        st.info(f"## {status_label}\n{status_reason}")
    else:
        st.success(f"## {status_label}\n{status_reason}")
    decision = snapshot.get("safety_decision") or {}
    action = str(decision.get("action", UNAVAILABLE)).replace("_", " ").title()
    st.write(
        f"**AERIS safety response:** {action}. "
        f"{decision.get('reason', unavailable_explanation(row))}"
    )
    st.caption(
        "The safety response is produced by the backend deterministic policy from anomaly, "
        "uncertainty, predicted path, sensor trust, and communication evidence."
    )

    if view == "Basic":
        path_tab, benchmark_tab = st.tabs(["Position & trajectory", "Benchmark evidence"])
        with path_tab:
            render_trajectory(records, snapshots, selected_index)
        with benchmark_tab:
            render_benchmark_chart(benchmark)
        return

    st.header("Sensor health")
    sensor_columns = st.columns(3)
    for column, sensor in zip(sensor_columns, ("gnss", "camera", "imu"), strict=True):
        value = (row.get("sensor_health") or {}).get(sensor)
        label = UNAVAILABLE if value is None else f"{float(value) * 100:.0f}%"
        column.metric(
            f"{sensor.upper()} adaptive trust",
            label,
            help="Relative estimator influence: 0% means minimum trust; 100% means fully trusted.",
        )
        column.caption(
            f"🏷️ {provenance_label(origin)} · "
            + (
                "Computed by the EKF from measurement agreement over time."
                if value is not None
                else unavailable_explanation(row, sensor)
            )
        )
    render_trust_chart(records)

    st.header("Position & trajectory")
    render_trajectory(records, snapshots, selected_index)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Mission position RMSE", show(metrics.get("position_rmse_m"), " m"))
    metric_columns[0].caption(
        "🏷️ SIMULATION METRIC · RMS estimate-to-truth distance across this entire mission."
    )
    metric_columns[1].metric(
        "Mission velocity RMSE", show(metrics.get("velocity_rmse_mps"), " m/s")
    )
    metric_columns[1].caption(
        "🏷️ SIMULATION METRIC · RMS velocity error against exact simulator truth."
    )
    metric_columns[2].metric("Anomaly recall", show(metrics.get("anomaly_recall")))
    metric_columns[2].caption(
        "🏷️ SYNTHETIC-FAULT METRIC · Fraction of injected-fault samples with an anomaly flag."
    )

    st.header("Fault and anomaly evidence")
    render_fault_timeline(records)
    nis = row.get("normalized_innovation_squared")
    st.metric("NIS anomaly score at selected moment", show(nis))
    st.caption(
        f"🏷️ {provenance_label(origin)} · NIS measures how strongly the current sensor reading "
        "disagrees with the EKF prediction after accounting for uncertainty; larger is less "
        "consistent."
    )

    st.header("Benchmark evidence")
    render_benchmark_chart(benchmark)
    st.link_button("Open authoritative benchmark artifact", f"{api}/artifacts/benchmark")

    st.header("Synthetic-data evidence")
    render_synthetic_preview(api, preview)

    with st.expander("Expert audit details: covariance, events, tracks and policy evidence"):
        st.caption(
            f"🏷️ {provenance_label(origin)} / ESTIMATED / PREDICTED · Raw backend fields; "
            "covariance is estimator uncertainty, not a measured physical value."
        )
        st.json(
            {
                "mission_id": mission_id,
                "selected_telemetry": row,
                "covariance": snapshot.get("covariance"),
                "tracks": snapshot.get("tracks"),
                "prediction": snapshot.get("prediction"),
                "safety_decision": decision,
                "events": events,
                "data_status": state.get("data_status"),
            }
        )


if __name__ == "__main__":
    main()
