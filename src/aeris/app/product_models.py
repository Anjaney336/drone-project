from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aeris.models import DataOrigin


class PriorityLevel(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ActionStatus(StrEnum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER REVIEW"
    INSPECTION_ASSIGNED = "INSPECTION ASSIGNED"
    ACTION_IN_PROGRESS = "ACTION IN PROGRESS"
    RESOLVED = "RESOLVED"


class MissionType(StrEnum):
    ROAD = "Road Inspection"
    BRIDGE = "Bridge Inspection"
    BUILDING = "Building Inspection"
    DISASTER = "Disaster Assessment"
    CROP_SURVEY = "Crop Health Survey"
    CUSTOM = "Custom"


class Domain(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    AGRICULTURE = "agriculture"


class ReliabilityLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ReviewVerdict(StrEnum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_REINSPECTION = "NEEDS_REINSPECTION"
    ESCALATED = "ESCALATED"


class ModelStatus(StrEnum):
    NOT_TRAINED = "NOT_TRAINED"
    TRAINING = "TRAINING"
    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"


class DroneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drone_id: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=120)
    model: str = Field(default="unspecified", max_length=120)
    origin: DataOrigin
    source: str = Field(min_length=2)


class TelemetryIngest(BaseModel):
    """Mirrors aeris.data.telemetry.TelemetryRecord's reliability-relevant fields,
    scoped to a product mission rather than a Digital Twin scenario."""

    model_config = ConfigDict(extra="forbid")
    mission_id: str
    timestamp: float
    gnss_quality: float | None = Field(default=None, ge=0, le=1)
    satellite_count: int | None = Field(default=None, ge=0)
    hdop: float | None = None
    camera_confidence: float | None = Field(default=None, ge=0, le=1)
    normalized_innovation_squared: float | None = None
    packet_delay_s: float | None = None
    packet_loss: bool | None = None
    battery_percent: float | None = Field(default=None, ge=0, le=100)
    origin: DataOrigin
    source: str = Field(min_length=2)

    @field_validator("origin")
    @classmethod
    def telemetry_origin_must_be_declared(cls, value: DataOrigin) -> DataOrigin:
        # USER_UPLOADED belongs here: a telemetry file a user attaches to a mission is
        # not the same evidence class as a measurement taken by an instrumented field
        # deployment, and must not have to masquerade as FIELD to be ingestible.
        # DEMONSTRATION and PUBLIC_BENCHMARK stay excluded — seeded and benchmark data
        # never enter a mission's telemetry stream.
        if value not in {
            DataOrigin.FIELD,
            DataOrigin.USER_UPLOADED,
            DataOrigin.MEASURED,
            DataOrigin.SIMULATION,
            DataOrigin.SYNTHETIC_FAULT,
            DataOrigin.SYNTHETIC,
        }:
            raise ValueError(f"Unexpected telemetry origin: {value}")
        return value


class AIFindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: str
    asset_id: str | None = None
    domain: Domain
    task_type: str = Field(min_length=2, max_length=60)
    label: str = Field(min_length=2, max_length=120)
    confidence: float = Field(ge=0, le=1)
    model_name: str = Field(min_length=2, max_length=120)
    model_version: str = Field(min_length=1, max_length=40)
    source_media: str | None = None
    regions: list[dict] | None = None
    origin: DataOrigin
    source: str = Field(min_length=2)


class HumanReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: ReviewVerdict
    reviewer: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=1000)


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=120)
    asset_type: str = Field(min_length=2, max_length=50)
    district: str = Field(min_length=2, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    criticality: float = Field(ge=0, le=1)
    origin: DataOrigin
    source: str = Field(min_length=2)


class ProductMissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=3, max_length=120)
    mission_type: MissionType
    asset_ids: list[str] = Field(min_length=1)
    district: str = Field(min_length=2, max_length=80)
    domain: Domain = Domain.INFRASTRUCTURE
    drone_id: str | None = None
    origin: DataOrigin
    source: str = Field(min_length=2)


class IngestObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    observation_type: str
    severity: float = Field(ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str = Field(default="", max_length=1000)
    evidence_uri: str | None = None
    origin: DataOrigin
    source: str = Field(min_length=2)

    @field_validator("origin")
    @classmethod
    def no_simulation_as_field_evidence(cls, value: DataOrigin) -> DataOrigin:
        if value in {DataOrigin.SIMULATION, DataOrigin.SYNTHETIC_FAULT}:
            raise ValueError("Digital-twin telemetry cannot be submitted as field evidence")
        return value


class MissionIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observations: list[IngestObservation] = Field(min_length=1)


class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: str
    recommended_action: str = Field(min_length=3, max_length=300)
    status: ActionStatus = ActionStatus.NEW
    assigned_to: str | None = Field(default=None, max_length=120)
    origin: DataOrigin
    source: str = Field(min_length=2)


class ActionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ActionStatus
    assigned_to: str | None = Field(default=None, max_length=120)


class FieldInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_record_id: str = Field(min_length=4, max_length=100)
    asset_id: str
    observation_type: str
    severity: float = Field(ge=0, le=1)
    notes: str = Field(default="", max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    evidence_name: str | None = Field(default=None, max_length=255)
    captured_at: str
    origin: DataOrigin = DataOrigin.FIELD
    source: str = "aeris.field_capture"

    @field_validator("origin")
    @classmethod
    def field_only(cls, value: DataOrigin) -> DataOrigin:
        if value not in {DataOrigin.FIELD, DataOrigin.USER_UPLOADED}:
            raise ValueError("Field synchronization requires field or user_uploaded origin")
        return value


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[FieldInspection]
