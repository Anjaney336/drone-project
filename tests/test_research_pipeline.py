import pytest

from aeris.autonomy.perception import SimulationObservationDetector
from aeris.autonomy.safety import RiskWeights
from aeris.benchmark import (
    VARIANTS,
    evaluate_variant,
    run_benchmark,
    sensor_stream_digest,
    source_tree_digest,
)
from aeris.data import LiveHardwareAdapter
from aeris.simulation.runner import run_scenario
from aeris.simulation.scenarios import ScenarioConfig, available_scenarios, generate_scenario


def test_exact_required_scenario_matrix():
    assert set(available_scenarios()) == {
        "nominal",
        "gnss_drift",
        "gnss_dropout",
        "imu_bias",
        "camera_degradation",
        "camera_occlusion",
        "packet_loss",
        "communication_latency",
        "multiple_drones",
        "sensor_disagreement",
        "geofence_breach",
        "combined_degradation",
    }


def test_simulator_camera_enters_detector_and_tracker():
    config = ScenarioConfig("nominal", steps=4)
    sample = generate_scenario(config)[0]
    assert SimulationObservationDetector().detect(sample.camera_frame, sample.timestamp)
    result = run_scenario(config)
    assert result["state_snapshots"][0]["tracks"][0]["class"] == "drone"


def test_detector_rejects_unlabelled_real_frame():
    with pytest.raises(TypeError):
        SimulationObservationDetector().detect({"detections": []}, 0.0)


def test_fair_variants_run_on_same_generated_stream():
    config = ScenarioConfig("gnss_drift", seed=3, steps=30)
    samples = generate_scenario(config)
    results = {variant: evaluate_variant(config, variant, samples=samples) for variant in VARIANTS}
    assert all(result["position_rmse_m"] is not None for result in results.values())


def test_paired_variants_receive_byte_identical_immutable_stream():
    config = ScenarioConfig("gnss_drift", seed=7, steps=30)
    samples = generate_scenario(config)
    before = sensor_stream_digest(samples)
    for variant in VARIANTS:
        evaluate_variant(config, variant, samples=samples)
        assert sensor_stream_digest(samples) == before


def test_live_mode_reports_unavailable_instead_of_faking_data():
    with pytest.raises(RuntimeError):
        LiveHardwareAdapter().records()


def test_risk_weights_are_normalized():
    RiskWeights()
    with pytest.raises(ValueError):
        RiskWeights(collision=0.9)


def test_benchmark_artifact_has_reproducibility_lineage():
    report = run_benchmark(seed=20, trials=1)
    assert report["benchmark_type"] == "simulation"
    assert len(report["records"]) == 12 * 4
    required = {
        "scenario",
        "seed",
        "config_hash",
        "dataset_version",
        "algorithm_variant",
        "sensor_stream_sha256",
        "metrics",
        "runtime",
        "fault_configuration",
        "software_version",
        "timestamp",
    }
    assert required <= report["records"][0].keys()
    assert report["records"][0]["software_version"] == source_tree_digest()
    grouped: dict[tuple[str, int], set[str]] = {}
    for record in report["records"]:
        key = (record["scenario"], record["seed"])
        grouped.setdefault(key, set()).add(record["sensor_stream_sha256"])
    assert all(len(digests) == 1 for digests in grouped.values())
