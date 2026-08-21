"""Regression tests for the guarantees AERIS actually advertises.

Each test here corresponds to a defect where the code contradicted a documented claim.
They are grouped by the claim they defend rather than by module, because the point is
the claim, not the implementation detail that happened to break it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from aeris.app import api
from aeris.app.mission_reliability import assess_mission_reliability
from aeris.app.product_models import (
    AIFindingCreate,
    HumanReviewCreate,
    ProductMissionCreate,
    TelemetryIngest,
)
from aeris.app.telemetry_import import parse_telemetry_csv, parse_telemetry_json


def _mission(store, **overrides) -> str:
    payload = {
        "name": "Integrity test mission",
        "mission_type": "Bridge Inspection",
        "asset_ids": ["BR-042"],
        "district": "Cuttack",
        "origin": "user_uploaded",
        "source": "test.suite",
        **overrides,
    }
    return store.create_mission(ProductMissionCreate(**payload))["mission_id"]


# --- Claim: a dimension with no telemetry is NOT AVAILABLE, never a stand-in value ----


def test_telemetry_without_signals_is_unknown_not_a_middling_score():
    """A file carrying only timestamps used to score MEDIUM / 52.5, with a green
    "telemetry stream continuous" tick derived from the absence of a packet_loss
    column."""
    result = assess_mission_reliability([{"timestamp": float(i)} for i in range(10)])
    assert result["level"] == "UNKNOWN"
    assert result["score"] is None
    assert result["components"] == {}
    assert set(result["unavailable_components"]) == {
        "navigation",
        "sensor_consistency",
        "telemetry_continuity",
        "battery_power",
        "data_completeness",
    }


def test_absent_packet_loss_is_not_evidence_of_an_unbroken_stream():
    rows = [{"timestamp": float(i), "battery_percent": 90.0} for i in range(5)]
    result = assess_mission_reliability(rows)
    assert "telemetry_continuity" not in result["components"]
    assert "telemetry_continuity" in result["unavailable_components"]


def test_weights_renormalise_over_assessed_dimensions_only():
    rows = [{"timestamp": float(i), "battery_percent": 80.0} for i in range(5)]
    result = assess_mission_reliability(rows)
    assert set(result["weights_used"]) == set(result["components"])
    assert result["weights_used"]
    assert sum(result["weights_used"].values()) == pytest.approx(1.0, abs=1e-6)


def test_degraded_record_count_cannot_exceed_the_records_measured():
    """A record that both lost a packet and exceeded the delay budget is one bad
    record, not two."""
    rows = [{"timestamp": float(i), "packet_loss": True, "packet_delay_s": 5.0} for i in range(4)]
    result = assess_mission_reliability(rows)
    assert result["components"]["telemetry_continuity"] == 0.0
    assert "4 of 4 reporting record(s)" in " ".join(result["reasons"])


def test_no_telemetry_and_unassessable_telemetry_are_distinguishable():
    empty = assess_mission_reliability([])
    unassessable = assess_mission_reliability([{"timestamp": 0.0}])
    assert empty["level"] == unassessable["level"] == "UNKNOWN"
    assert empty["sample_count"] == 0
    assert unassessable["sample_count"] == 1


# --- Claim: origins are structurally distinct -----------------------------------------


def test_user_uploaded_telemetry_need_not_masquerade_as_field():
    row = TelemetryIngest(
        mission_id="M-1", timestamp=0.0, origin="user_uploaded", source="test.suite"
    )
    assert row.origin == "user_uploaded"


def test_demonstration_origin_still_cannot_enter_the_telemetry_stream():
    with pytest.raises(ValidationError):
        TelemetryIngest(
            mission_id="M-1", timestamp=0.0, origin="demonstration", source="test.suite"
        )


def test_uploaded_telemetry_is_tagged_user_uploaded():
    csv = b"timestamp,battery\n0,90\n1,88\n"
    rows, recognised = parse_telemetry_csv(csv, "M-1", "aeris.telemetry_upload")
    assert [r.origin for r in rows] == ["user_uploaded", "user_uploaded"]
    assert "battery_percent" in recognised


def test_json_telemetry_resolves_the_same_aliases_as_csv():
    """`battery` and `gps` are accepted by the CSV path; the JSON path used to match
    only canonical names and silently dropped them."""
    payload = b'[{"t": 0, "battery": 91, "gps": 0.88}, {"t": 1, "battery": 88, "gps": 0.79}]'
    rows, recognised = parse_telemetry_json(payload, "M-1", "aeris.telemetry_upload")
    assert set(recognised) >= {"battery_percent", "gnss_quality", "timestamp"}
    assert rows[0].battery_percent == 91
    assert rows[0].gnss_quality == pytest.approx(0.88)


def test_findings_inherit_the_provenance_of_the_analysed_medium():
    assert api._media_origin("data/uploads/M-1/abc.jpg") == "user_uploaded"
    assert api._media_origin("data/demo/sample.jpg") == "demonstration"
    assert api._media_origin("data/raw/concrete/x.jpg") == "public_benchmark"


def test_aggregates_report_a_mixed_provenance_rather_than_claiming_demonstration(
    isolated_product_store,
):
    store = isolated_product_store
    assert store.executive_summary()["origin"] == "demonstration"
    store.create_asset(
        api.AssetCreate(
            asset_id="USR-1",
            name="User Bridge",
            asset_type="Bridge",
            district="Cuttack",
            latitude=20.4,
            longitude=85.9,
            criticality=0.5,
            origin="user_uploaded",
            source="aeris.new_mission_wizard",
        )
    )
    summary = store.executive_summary()
    assert summary["origin"] == "mixed"
    assert summary["origins"]["user_uploaded"] == 1


# --- Claim: only a human reviewer settles a finding ------------------------------------


def _finding(store, mission_id: str) -> str:
    return store.create_ai_finding(
        AIFindingCreate(
            mission_id=mission_id,
            asset_id="BR-042",
            domain="infrastructure",
            task_type="object_detection",
            label="AI Flagged: Possible Defect",
            confidence=0.7,
            model_name="test_model",
            model_version="v1",
            origin="user_uploaded",
            source="test.suite",
        )
    )["finding_id"]


def test_a_settled_verdict_cannot_be_silently_overwritten(isolated_product_store):
    store = isolated_product_store
    finding_id = _finding(store, _mission(store))
    store.submit_human_review(
        finding_id, HumanReviewCreate(verdict="CONFIRMED", reviewer="A. Engineer")
    )
    with pytest.raises(ValueError, match="already CONFIRMED"):
        store.submit_human_review(
            finding_id, HumanReviewCreate(verdict="REJECTED", reviewer="B. Engineer")
        )


def test_reinspection_may_still_settle_and_keeps_the_whole_trail(isolated_product_store):
    store = isolated_product_store
    finding_id = _finding(store, _mission(store))
    store.submit_human_review(
        finding_id, HumanReviewCreate(verdict="NEEDS_REINSPECTION", reviewer="A. Engineer")
    )
    store.submit_human_review(
        finding_id, HumanReviewCreate(verdict="CONFIRMED", reviewer="B. Engineer")
    )
    finding = store.get_ai_finding(finding_id)
    assert finding["review_status"] == "CONFIRMED"
    assert [r["reviewer"] for r in finding["reviews"]] == ["B. Engineer", "A. Engineer"]


def test_illegal_review_transition_is_refused(isolated_product_store):
    store = isolated_product_store
    finding_id = _finding(store, _mission(store))
    store.submit_human_review(
        finding_id, HumanReviewCreate(verdict="ESCALATED", reviewer="A. Engineer")
    )
    with pytest.raises(ValueError, match="Cannot move finding"):
        store.submit_human_review(
            finding_id, HumanReviewCreate(verdict="NEEDS_REINSPECTION", reviewer="A. Engineer")
        )


# --- Claim: uploads and media access are bounded --------------------------------------


def test_media_endpoint_rejects_a_sibling_directory_sharing_a_root_prefix(tmp_path):
    """`data/demolition` merely starts with the `data/demo` root; the previous
    string-prefix check accepted it."""
    sneaky = api.ROOT / "data" / "demolition"
    sneaky.mkdir(parents=True, exist_ok=True)
    target = sneaky / "secret.txt"
    target.write_text("not for serving", encoding="utf-8")
    try:
        response = TestClient(api.app).get(
            "/api/v1/media", params={"path": "data/demolition/secret.txt"}
        )
        assert response.status_code == 403
    finally:
        target.unlink()
        sneaky.rmdir()


def test_upload_content_is_validated_against_real_image_bytes(isolated_product_store):
    client = TestClient(api.app)
    mission_id = _mission(isolated_product_store)
    response = client.post(
        f"/api/v1/missions/{mission_id}/media",
        files={"file": ("evil.png", b"<?php echo 1; ?>" + b"A" * 64, "image/png")},
    )
    assert response.status_code == 415
    assert "not a valid" in response.json()["detail"]


def test_a_real_png_is_accepted_and_stored_under_uploads(isolated_product_store):
    client = TestClient(api.app)
    mission_id = _mission(isolated_product_store)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    response = client.post(
        f"/api/v1/missions/{mission_id}/media", files={"file": ("ok.png", png, "image/png")}
    )
    assert response.status_code == 200
    stored = api.ROOT / response.json()["media_path"]
    try:
        assert response.json()["media_path"].startswith("data/uploads/")
        assert stored.read_bytes() == png
    finally:
        stored.unlink(missing_ok=True)


# --- Claim: a model that is not READY never produces a finding -------------------------


def test_analyze_refuses_rather_than_fabricating_when_no_checkpoint_exists(
    isolated_product_store,
):
    client = TestClient(api.app)
    mission_id = _mission(isolated_product_store)
    if api.REGISTRY["infrastructure_detection"].status().value == "READY":
        pytest.skip("a published checkpoint is present in this environment")
    response = client.post(
        f"/api/v1/missions/{mission_id}/analyze",
        json={"image_path": "data/demo/whatever.jpg", "model_key": "infrastructure_detection"},
    )
    assert response.status_code == 409
    assert "refusing to fabricate" in response.json()["detail"]
    assert client.get(f"/api/v1/findings?mission_id={mission_id}").json() == []
