import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from aeris.app import api
from aeris.app.api import app
from aeris.app.plain_language import (
    UNAVAILABLE,
    fault_summary,
    plain_safety_status,
    show,
    unavailable_explanation,
)
from aeris.data.telemetry import TelemetryRecord


def test_typed_mission_api_and_unavailable_invariant():
    client = TestClient(app)
    created = client.post("/missions", json={"scenario_id": "nominal", "seed": 9})
    assert created.status_code == 201
    mission_id = created.json()["mission_id"]
    state = client.get(f"/missions/{mission_id}/state").json()
    assert state["data_status"] == "AVAILABLE"
    assert state["latest_telemetry"]["origin"] == "simulation"
    assert state["latest_state"]["prediction"]["model"] == "constant_velocity"
    telemetry = client.get(f"/missions/{mission_id}/telemetry").json()
    assert telemetry["records"][-1] == state["latest_telemetry"]
    assert telemetry["snapshots"][-1] == state["latest_state"]
    assert state["latest_telemetry"]["configuration_hash"]
    assert show(None) == UNAVAILABLE


def test_unknown_api_fields_are_rejected():
    response = TestClient(app).post(
        "/missions", json={"scenario_id": "nominal", "fake_metric": 0.85}
    )
    assert response.status_code == 422

    unknown_scenario = TestClient(app).post(
        "/missions", json={"scenario_id": "not_a_scenario", "seed": 7}
    )
    assert unknown_scenario.status_code == 422


def test_dashboard_plain_language_contract():
    assert plain_safety_status("NORMAL")[0] == "✅ Safe"
    assert "Action recommended" in plain_safety_status("GEOFENCE_RISK")[0]
    assert "does not compute separate IMU trust" in unavailable_explanation({}, "imu")
    assert fault_summary({}, [{"injected_fault": "synthetic_gnss_drift_high"}]).endswith(
        "(earlier; now inactive)"
    )


def test_benchmark_endpoint_reads_only_authoritative_artifact(tmp_path, monkeypatch):
    authoritative = tmp_path / "benchmark.json"
    legacy = tmp_path / "legacy_protocol_benchmark.json"
    authoritative.write_text(
        json.dumps({"benchmark_type": "simulation", "trials": 2, "aggregate": {"fair": 1}}),
        encoding="utf-8",
    )
    legacy.write_text(json.dumps({"aggregate": {"legacy": 999}}), encoding="utf-8")
    monkeypatch.setattr(api, "BENCHMARK_PATH", authoritative)
    result = TestClient(app).get("/benchmark").json()
    assert result["aggregate"] == {"fair": 1}
    assert "legacy" not in json.dumps(result)


def test_synthetic_preview_is_explicitly_tagged():
    response = TestClient(app).get("/synthetic-data-preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"] == "synthetic"
    assert all(row["origin"] in {"synthetic", "synthetic_fault"} for row in payload["records"])


def test_untagged_telemetry_is_structurally_rejected():
    with pytest.raises(ValidationError):
        TelemetryRecord(timestamp=0.0, mission_mode="SIM", safety_state="NORMAL")


def test_health_endpoint_reports_truthful_status():
    """Regression test for the 2026-08-20 'Failed to fetch' incident: the incident itself
    was operational (a backend process was killed under a live browser tab), not a code
    defect, so the durable regression coverage is (a) a real health endpoint exists and
    reflects actual DB connectivity rather than a hardcoded constant, and (b) every route
    the frontend depends on for its previously-broken pages responds successfully against
    a running backend."""
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "aeris-api"
    assert payload["database"] == "ok"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/priority-queue",  # Government Decision Center
        "/api/v1/missions",  # Drone Mission Management
        "/api/v1/executive-summary",  # Command Center
        "/api/v1/assets",
        "/api/v1/regions/analytics",
        "/api/v1/review-queue",  # Human Review Queue
        "/api/v1/drones",  # Drone Health
        "/api/v1/models/status",
    ],
)
def test_critical_frontend_routes_respond(path):
    response = TestClient(app).get(path)
    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text}"


def test_models_status_never_errors_and_reports_valid_states():
    """NOT_TRAINED is a valid, expected application state and must never surface as an
    API failure — this is what would make a NOT_TRAINED model look like a broken backend
    to the frontend."""
    response = TestClient(app).get("/api/v1/models/status")
    assert response.status_code == 200
    for entry in response.json():
        assert entry["status"] in {"NOT_TRAINED", "TRAINING", "READY", "UNAVAILABLE"}


def test_model_adapter_refuses_inference_when_not_ready(tmp_path):
    """A model that isn't READY must raise rather than fabricate a prediction."""
    from aeris.app.model_registry import AgricultureModel

    adapter = AgricultureModel()
    adapter.run_dir = tmp_path / "nonexistent_run"  # guarantees NOT_TRAINED
    assert adapter.status().value == "NOT_TRAINED"
    with pytest.raises(RuntimeError, match="NOT_TRAINED"):
        adapter.analyze("does-not-matter.jpg")


def test_review_queue_is_empty_state_not_error_on_fresh_data():
    """An empty result set must render as a legitimate empty state, never as a fetch
    failure — distinct from the NETWORK_ERROR/SERVER_ERROR cases the frontend now
    differentiates in aeris/app/static/app.js's request()."""
    response = TestClient(app).get("/api/v1/review-queue")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_media_upload_and_real_inference_end_to_end():
    """The real browser-facing upload path: multipart upload -> stored under data/uploads/
    -> the returned path feeds /analyze -> real model inference (skipped gracefully if the
    model isn't trained in this environment, never fabricated)."""
    client = TestClient(app)
    mission = client.post(
        "/api/v1/missions",
        json={
            "name": "Upload Integration Test",
            "mission_type": "Bridge Inspection",
            "asset_ids": ["BR-042"],
            "district": "Cuttack",
            "domain": "infrastructure",
            "origin": "field",
            "source": "test",
        },
    ).json()
    from pathlib import Path

    image_path = Path("data/raw/concrete/damage_detection/images/E (12).jpg")
    if not image_path.exists():
        pytest.skip("sample infrastructure image not present in this environment")
    upload = client.post(
        f"/api/v1/missions/{mission['mission_id']}/media",
        files={"file": ("test.jpg", image_path.read_bytes(), "image/jpeg")},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["media_path"].startswith("data/uploads/")
    assert payload["size_bytes"] > 0

    from aeris.app.model_registry import REGISTRY

    if REGISTRY["infrastructure_detection"].status().value != "READY":
        pytest.skip("infrastructure model not READY in this environment")
    analyzed = client.post(
        f"/api/v1/missions/{mission['mission_id']}/analyze",
        json={"image_path": payload["media_path"], "model_key": "infrastructure_detection"},
    )
    assert analyzed.status_code == 200
    for finding in analyzed.json():
        assert finding["label"].startswith("AI Flagged:")
        assert finding["review_status"] == "PENDING"


def test_media_endpoint_blocks_path_traversal():
    response = TestClient(app).get("/api/v1/media", params={"path": "../../../../etc/passwd"})
    assert response.status_code == 403


def test_finding_carries_reliability_interpretation():
    """Every finding response must explain what the confidence + mission reliability
    combination actually means, not just show a bare number (Part 10 requirement)."""
    client = TestClient(app)
    mission = client.post(
        "/api/v1/missions",
        json={
            "name": "Interpretation Test",
            "mission_type": "Bridge Inspection",
            "asset_ids": ["BR-042"],
            "district": "Cuttack",
            "domain": "infrastructure",
            "origin": "field",
            "source": "test",
        },
    ).json()
    finding = client.post(
        "/api/v1/findings",
        json={
            "mission_id": mission["mission_id"],
            "asset_id": "BR-042",
            "domain": "infrastructure",
            "task_type": "object_detection",
            "label": "AI Flagged: Possible Defect",
            "confidence": 0.5,
            "model_name": "test_model",
            "model_version": "v1",
            "origin": "measured",
            "source": "test",
        },
    ).json()
    assert "interpretation" in finding
    assert "recommended_action" in finding
    assert finding["reliability_level"] == "UNKNOWN"
