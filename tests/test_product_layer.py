from pathlib import Path

from fastapi.testclient import TestClient

from aeris.app import api
from aeris.app.priority import assess_priority
from aeris.app.product_models import (
    ActionUpdate,
    FieldInspection,
    MissionIngest,
    ProductMissionCreate,
    SyncRequest,
)
from aeris.app.product_service import ProductStore


def store(tmp_path: Path) -> ProductStore:
    return ProductStore(tmp_path / "product.db")


def test_seeded_product_dataset_is_reproducible_and_tagged(tmp_path):
    first = store(tmp_path / "one").export_demo()
    second = store(tmp_path / "two").export_demo()
    assert first == second
    assert first["dataset"] == "AERIS DEMONSTRATION DATASET"
    for collection in ("assets", "missions", "observations", "priority_assessments", "actions"):
        assert all(row["origin"] == "demonstration" and row["source"] for row in first[collection])


def test_priority_scoring_is_explainable_and_conservative_without_confidence():
    result = assess_priority(
        severity=0.9,
        confidence=None,
        criticality=0.95,
        recurrence=3,
        trend=0.8,
        geographic_impact=0.7,
    )
    assert result.level == "CRITICAL"
    assert result.components["confidence"] == 0.5
    assert "confidence unavailable" in " ".join(result.factors).lower()
    assert "0.30×severity" in result.formula


def test_mission_ingestion_generates_traceable_priority(tmp_path):
    service = store(tmp_path)
    mission = service.create_mission(
        ProductMissionCreate(
            name="Test bridge mission",
            mission_type="Bridge Inspection",
            asset_ids=["BR-017"],
            district="Cuttack",
            origin="user_uploaded",
            source="test.operator",
        )
    )
    completed = service.ingest(
        mission["mission_id"],
        MissionIngest(
            observations=[
                {
                    "asset_id": "BR-017",
                    "observation_type": "damage",
                    "severity": 0.9,
                    "confidence": None,
                    "notes": "Human observation",
                    "origin": "user_uploaded",
                    "source": "test.operator",
                }
            ]
        ),
    )
    asset = service.get_asset("BR-017")
    assert completed["status"] == "COMPLETED"
    assert asset["observations"][0]["origin"] == "user_uploaded"
    assert asset["priority_explanation"]


def test_action_transition_is_persistent(tmp_path):
    service = store(tmp_path)
    action = service.priority_queue()[0]
    updated = service.update_action(
        action["action_id"], ActionUpdate(status="INSPECTION ASSIGNED", assigned_to="District cell")
    )
    assert updated["status"] == "INSPECTION ASSIGNED"
    assert updated["assigned_to"] == "District cell"


def test_resolved_action_cannot_be_reopened(tmp_path):
    import pytest

    service = store(tmp_path)
    action = service.priority_queue()[0]
    service.update_action(action["action_id"], ActionUpdate(status="INSPECTION ASSIGNED"))
    service.update_action(action["action_id"], ActionUpdate(status="RESOLVED"))
    with pytest.raises(ValueError):
        service.update_action(action["action_id"], ActionUpdate(status="NEW"))


def test_offline_sync_is_idempotent_and_preserves_field_origin(tmp_path):
    service = store(tmp_path)
    record = FieldInspection(
        client_record_id="FIELD-test-001",
        asset_id="CL-018",
        observation_type="obstruction",
        severity=0.7,
        notes="Captured offline",
        captured_at="2026-01-16T10:00:00Z",
        origin="field",
        source="aeris.field_capture",
    )
    first = service.sync(SyncRequest(records=[record]))
    second = service.sync(SyncRequest(records=[record]))
    assert len(first["accepted"]) == 1
    assert second["duplicates"] == ["FIELD-test-001"]
    assert service.get_asset("CL-018")["observations"][0]["origin"] == "field"


def test_digital_twin_origin_cannot_enter_product_ingest_schema():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MissionIngest(
            observations=[
                {
                    "asset_id": "BR-042",
                    "observation_type": "damage",
                    "severity": 0.8,
                    "origin": "simulation",
                    "source": "aeris.simulation.scenarios",
                }
            ]
        )


def test_product_api_returns_persisted_backend_records(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "product_store", store(tmp_path))
    client = TestClient(api.app)
    summary = client.get("/api/v1/executive-summary")
    assets = client.get("/api/v1/assets")
    regions = client.get("/api/v1/regions/analytics?district=Cuttack")
    assert summary.status_code == assets.status_code == regions.status_code == 200
    assert summary.json()["metrics"]["total_assets"] == len(assets.json())
    assert regions.json()["origin"] == "demonstration"
