from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from aeris.simulation.scenarios import available_scenarios


class MissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "nominal"
    seed: int = 7

    @field_validator("scenario_id")
    @classmethod
    def known_scenario(cls, value: str) -> str:
        if value not in available_scenarios():
            raise ValueError(f"scenario_id must be one of: {', '.join(available_scenarios())}")
        return value


class MissionSummary(BaseModel):
    mission_id: str
    status: str
    scenario_id: str
    seed: int


class MissionState(BaseModel):
    mission_id: str
    latest_telemetry: dict | None
    latest_state: dict | None
    data_status: str = Field(description="AVAILABLE only when backed by a telemetry record")


class MissionMetrics(BaseModel):
    mission_id: str
    values: dict[str, float | None]


class MissionEvents(BaseModel):
    mission_id: str
    events: list[dict]


class MissionTelemetry(BaseModel):
    mission_id: str
    records: list[dict]
    snapshots: list[dict]


class MissionArtifacts(BaseModel):
    mission_id: str
    artifacts: list[str]
