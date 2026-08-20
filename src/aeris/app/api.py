from __future__ import annotations

import json
import uuid
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aeris.app.model_registry import REGISTRY, registry_status
from aeris.app.product_models import (
    ActionCreate,
    ActionUpdate,
    AIFindingCreate,
    AssetCreate,
    DroneCreate,
    HumanReviewCreate,
    MissionIngest,
    ProductMissionCreate,
    SyncRequest,
    TelemetryIngest,
)
from aeris.app.product_service import ProductStore
from aeris.app.schemas import (
    MissionArtifacts,
    MissionCreate,
    MissionEvents,
    MissionMetrics,
    MissionState,
    MissionSummary,
    MissionTelemetry,
)
from aeris.app.service import MissionStore
from aeris.models import DataOrigin

app = FastAPI(title="AERIS Infrastructure Intelligence API", version="1.0.0")
store = MissionStore()
product_store = ProductStore()


@app.get("/api/v1/health")
def health() -> dict:
    """Truthful liveness/readiness check. No fabricated counts or model states —
    just confirms the process is up and the database connection actually works."""
    try:
        product_store.list_drones()
        db_ok = True
    except Exception:  # noqa: BLE001 - health check must not raise, just report
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "aeris-api",
        "database": "ok" if db_ok else "unavailable",
    }


BENCHMARK_PATH = Path("artifacts/benchmark.json")
SYNTHETIC_VALIDATION_PATH = Path("artifacts/synthetic_data_validation.json")
SYNTHETIC_HELD_OUT_PATH = Path("data/processed/synthetic/held_out.npz")


def _mission(mission_id: str) -> dict:
    try:
        return store.get(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/missions", response_model=MissionSummary, status_code=201)
def create_mission(request: MissionCreate) -> MissionSummary:
    mission_id, mission = store.create(request)
    return MissionSummary(
        mission_id=mission_id,
        status=mission["status"],
        scenario_id=request.scenario_id,
        seed=request.seed,
    )


@app.get("/missions/{mission_id}", response_model=MissionSummary)
def get_mission(mission_id: str) -> MissionSummary:
    mission = _mission(mission_id)
    request = mission["request"]
    return MissionSummary(
        mission_id=mission_id,
        status=mission["status"],
        scenario_id=request.scenario_id,
        seed=request.seed,
    )


@app.get("/missions/{mission_id}/state", response_model=MissionState)
def get_state(mission_id: str) -> MissionState:
    result = _mission(mission_id)["result"]
    telemetry = result.get("telemetry", [])
    snapshots = result.get("state_snapshots", [])
    return MissionState(
        mission_id=mission_id,
        latest_telemetry=telemetry[-1] if telemetry else None,
        latest_state=snapshots[-1] if snapshots else None,
        data_status="AVAILABLE" if telemetry else "DATA UNAVAILABLE",
    )


@app.get("/missions/{mission_id}/metrics", response_model=MissionMetrics)
def get_metrics(mission_id: str) -> MissionMetrics:
    return MissionMetrics(mission_id=mission_id, values=_mission(mission_id)["result"]["metrics"])


@app.get("/missions/{mission_id}/events", response_model=MissionEvents)
def get_events(mission_id: str) -> MissionEvents:
    rows = _mission(mission_id)["result"].get("telemetry", [])
    events = [
        {
            "timestamp": row["timestamp"],
            "anomaly_type": row["anomaly_label"],
            "source": row["source"],
        }
        for row in rows
        if row.get("anomaly_label")
    ]
    return MissionEvents(mission_id=mission_id, events=events)


@app.get("/missions/{mission_id}/telemetry", response_model=MissionTelemetry)
def get_telemetry(mission_id: str) -> MissionTelemetry:
    result = _mission(mission_id)["result"]
    return MissionTelemetry(
        mission_id=mission_id,
        records=result.get("telemetry", []),
        snapshots=result.get("state_snapshots", []),
    )


@app.get("/missions/{mission_id}/artifacts", response_model=MissionArtifacts)
def get_artifacts(mission_id: str) -> MissionArtifacts:
    _mission(mission_id)
    return MissionArtifacts(mission_id=mission_id, artifacts=[])


@app.get("/benchmark")
def get_benchmark() -> dict:
    if not BENCHMARK_PATH.exists():
        return {"data_status": "DATA UNAVAILABLE", "aggregate": None}
    report = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    return {
        "data_status": "AVAILABLE",
        "benchmark_type": report.get("benchmark_type"),
        "paired_seed_start": report.get("paired_seed_start"),
        "trials": report.get("trials"),
        "claim_boundary": report.get("claim_boundary"),
        "aggregate": report.get("aggregate"),
    }


@app.get("/artifacts/benchmark")
def get_benchmark_artifact() -> dict:
    if not BENCHMARK_PATH.exists():
        raise HTTPException(status_code=404, detail="Authoritative benchmark artifact unavailable")
    return json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))


@app.get("/artifacts/synthetic-validation")
def get_synthetic_validation_artifact() -> dict:
    if not SYNTHETIC_VALIDATION_PATH.exists():
        raise HTTPException(status_code=404, detail="Synthetic validation artifact unavailable")
    return json.loads(SYNTHETIC_VALIDATION_PATH.read_text(encoding="utf-8"))


@app.get("/synthetic-data-preview")
def get_synthetic_data_preview() -> dict:
    if not SYNTHETIC_HELD_OUT_PATH.exists():
        return {"data_status": "DATA UNAVAILABLE", "provenance": "synthetic", "records": []}
    with np.load(SYNTHETIC_HELD_OUT_PATH) as data:
        indices = np.linspace(0, len(data["timestamp_s"]) - 1, 30, dtype=int)
        rows = [
            {
                "timestamp_s": float(data["timestamp_s"][index]),
                "imu_accel_x_mps2": float(data["imu_accel_mps2"][index, 0]),
                "gnss_error_x_m": float(data["gnss_error_m"][index, 0]),
                "hdop": float(data["hdop"][index]),
                "origin": str(data["origin"][index]),
            }
            for index in indices
        ]
    validation = (
        json.loads(SYNTHETIC_VALIDATION_PATH.read_text(encoding="utf-8"))
        if SYNTHETIC_VALIDATION_PATH.exists()
        else None
    )
    return {
        "data_status": "AVAILABLE",
        "provenance": "synthetic",
        "split": "held_out",
        "records": rows,
        "validation_passed": None if validation is None else validation.get("passed"),
        "validation_artifact": "/artifacts/synthetic-validation",
    }


def _product_call(callback):
    try:
        return callback()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/executive-summary")
def executive_summary() -> dict:
    return product_store.executive_summary()


@app.get("/api/v1/assets")
def list_assets(district: str | None = None, priority: str | None = None) -> list[dict]:
    return product_store.list_assets(district=district, priority=priority)


@app.post("/api/v1/assets", status_code=201)
def create_asset(request: AssetCreate) -> dict:
    return _product_call(lambda: product_store.create_asset(request))


@app.get("/api/v1/assets/{asset_id}")
def get_asset(asset_id: str) -> dict:
    return _product_call(lambda: product_store.get_asset(asset_id))


@app.get("/api/v1/missions")
def list_product_missions() -> list[dict]:
    return product_store.list_missions()


@app.post("/api/v1/missions", status_code=201)
def create_product_mission(request: ProductMissionCreate) -> dict:
    return _product_call(lambda: product_store.create_mission(request))


@app.get("/api/v1/missions/{mission_id}")
def get_product_mission(mission_id: str) -> dict:
    return _product_call(lambda: product_store.get_mission(mission_id))


@app.post("/api/v1/missions/{mission_id}/ingest")
def ingest_product_mission(mission_id: str, request: MissionIngest) -> dict:
    return _product_call(lambda: product_store.ingest(mission_id, request))


@app.get("/api/v1/priority-queue")
def priority_queue() -> list[dict]:
    return product_store.priority_queue()


@app.post("/api/v1/actions", status_code=201)
def create_action(request: ActionCreate) -> dict:
    return _product_call(lambda: product_store.create_action(request))


@app.patch("/api/v1/actions/{action_id}")
def update_action(action_id: str, request: ActionUpdate) -> dict:
    return _product_call(lambda: product_store.update_action(action_id, request))


@app.get("/api/v1/regions/analytics")
def regional_analytics(district: str | None = None) -> dict:
    return product_store.regional_analytics(district=district)


@app.post("/api/v1/sync")
def sync_field_records(request: SyncRequest) -> dict:
    return _product_call(lambda: product_store.sync(request))


@app.get("/api/v1/demo-dataset")
def demo_dataset() -> dict:
    return product_store.export_demo()


@app.get("/api/v1/drones")
def list_drones() -> list[dict]:
    return product_store.list_drones()


@app.post("/api/v1/drones", status_code=201)
def create_drone(request: DroneCreate) -> dict:
    return _product_call(lambda: product_store.create_drone(request))


@app.post("/api/v1/telemetry")
def ingest_telemetry(records: list[TelemetryIngest]) -> dict:
    return _product_call(lambda: product_store.ingest_telemetry(records))


@app.get("/api/v1/missions/{mission_id}/reliability")
def get_mission_reliability(mission_id: str) -> dict:
    return product_store.get_mission_reliability(mission_id)


@app.get("/api/v1/findings")
def list_ai_findings(mission_id: str | None = None) -> list[dict]:
    return product_store.list_ai_findings(mission_id=mission_id)


@app.post("/api/v1/findings", status_code=201)
def create_ai_finding(request: AIFindingCreate) -> dict:
    return _product_call(lambda: product_store.create_ai_finding(request))


@app.get("/api/v1/review-queue")
def review_queue() -> list[dict]:
    return product_store.review_queue()


@app.post("/api/v1/findings/{finding_id}/review")
def submit_human_review(finding_id: str, request: HumanReviewCreate) -> dict:
    return _product_call(lambda: product_store.submit_human_review(finding_id, request))


@app.get("/api/v1/models/status")
def models_status() -> list[dict]:
    return registry_status()


class AnalyzeRequest(BaseModel):
    image_path: str
    asset_id: str | None = None
    model_key: str = "infrastructure_detection"


@app.post("/api/v1/missions/{mission_id}/analyze")
def analyze_mission_image(mission_id: str, request: AnalyzeRequest) -> list[dict]:
    _product_call(lambda: product_store.get_mission(mission_id))
    adapter = REGISTRY.get(request.model_key)
    if adapter is None:
        raise HTTPException(status_code=400, detail=f"Unknown model_key: {request.model_key}")
    try:
        predictions = adapter.analyze(request.image_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    findings = []
    for prediction in predictions:
        finding = product_store.create_ai_finding(
            AIFindingCreate(
                mission_id=mission_id,
                asset_id=request.asset_id,
                domain=prediction.domain,
                task_type=prediction.task_type,
                label=prediction.label,
                confidence=prediction.confidence,
                model_name=prediction.model_name,
                model_version=prediction.model_version,
                source_media=request.image_path,
                regions=prediction.regions,
                origin=DataOrigin.MEASURED,
                source="aeris.model_registry",
            )
        )
        findings.append(finding)
    return findings


ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = ROOT / "data" / "uploads"
MEDIA_ROOTS = [
    ROOT / "data" / "raw",
    ROOT / "data" / "processed",
    ROOT / "data" / "demo",
    UPLOAD_ROOT,
]
ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@app.get("/api/v1/media")
def get_media(path: str) -> FileResponse:
    """Serves mission-referenced imagery for display. Restricted to data/ subdirectories
    to prevent path traversal outside the dataset roots."""
    candidate = (ROOT / path).resolve()
    if not any(str(candidate).startswith(str(root.resolve())) for root in MEDIA_ROOTS):
        raise HTTPException(status_code=403, detail="Path is outside permitted media roots")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(candidate)


@app.post("/api/v1/missions/{mission_id}/media")
async def upload_mission_media(mission_id: str, file: UploadFile) -> dict:
    """Real upload path so the normal user workflow never requires a server filesystem
    path: browser -> multipart upload -> stored under data/uploads/<mission>/ -> the
    returned relative path is usable directly by /analyze and /media."""
    _product_call(lambda: product_store.get_mission(mission_id))
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported content type: {file.content_type}. "
                f"Allowed: {sorted(ALLOWED_UPLOAD_TYPES)}"
            ),
        )
    body = await file.read()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit"
        )
    ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
    mission_dir = UPLOAD_ROOT / mission_id
    mission_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = mission_dir / stored_name
    stored_path.write_bytes(body)
    relative_path = str(stored_path.relative_to(ROOT)).replace("\\", "/")
    return {
        "mission_id": mission_id,
        "media_path": relative_path,
        "media_url": f"/api/v1/media?path={relative_path}",
        "original_filename": file.filename,
        "size_bytes": len(body),
        "content_type": file.content_type,
    }


@app.post("/api/v1/missions/{mission_id}/telemetry/upload")
async def upload_mission_telemetry(mission_id: str, file: UploadFile) -> dict:
    """Real file-based telemetry ingestion: CSV or JSON, adapting to whatever columns
    are actually present. A file with only a battery column produces a reliability
    assessment that only scores battery — every other dimension honestly says why it
    could not be assessed, never silently defaulting to a good score."""
    from aeris.app.telemetry_import import parse_telemetry_csv, parse_telemetry_json

    _product_call(lambda: product_store.get_mission(mission_id))
    body = await file.read()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit"
        )
    name = (file.filename or "").lower()
    try:
        if name.endswith(".json"):
            records, recognized = parse_telemetry_json(body, mission_id, "aeris.telemetry_upload")
        elif name.endswith(".csv"):
            records, recognized = parse_telemetry_csv(body, mission_id, "aeris.telemetry_upload")
        else:
            raise HTTPException(status_code=415, detail="Telemetry file must be .csv or .json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not records:
        raise HTTPException(status_code=422, detail="No telemetry rows found in the uploaded file")
    reliability = _product_call(lambda: product_store.ingest_telemetry(records))
    return {
        "mission_id": mission_id,
        "records_ingested": len(records),
        "recognized_fields": recognized,
        "reliability": reliability,
    }


@app.get("/api/v1/telemetry/sample-csv")
def sample_telemetry_csv() -> dict:
    """Documents the expected schema so a user knows what a telemetry file can contain
    without requiring every field."""
    from aeris.app.telemetry_import import COLUMN_ALIASES

    return {
        "columns": sorted({alias for aliases in COLUMN_ALIASES.values() for alias in aliases}),
        "example_csv": (
            "timestamp,battery,gnss,satellites,camera,packet_loss\n"
            "0,91,0.88,11,0.95,0\n"
            "1,88,0.79,9,0.90,0\n"
            "2,84,0.52,6,0.85,1\n"
        ),
        "note": (
            "Only timestamp is required. Every other column is optional — omit any you don't "
            "have; AERIS will mark that dimension NOT AVAILABLE rather than assuming a value."
        ),
    }


STATIC_PATH = Path(__file__).with_name("static")
if STATIC_PATH.exists():
    app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")


@app.get("/", include_in_schema=False)
def product_frontend():
    return FileResponse(STATIC_PATH / "index.html")


def run() -> None:
    import uvicorn

    uvicorn.run("aeris.app.api:app", host="127.0.0.1", port=8000)


def run_product() -> None:
    import uvicorn

    uvicorn.run("aeris.app.api:app", host="127.0.0.1", port=8501)
