from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aeris.models import DataOrigin, SafetyState


class TelemetryRecord(BaseModel):
    """Canonical telemetry row. Unknown readings remain null."""

    model_config = ConfigDict(extra="forbid")
    timestamp: float
    position_m: tuple[float, float, float] | None = None
    velocity_mps: tuple[float, float, float] | None = None
    acceleration_mps2: tuple[float, float, float] | None = None
    gyro_rps: tuple[float, float, float] | None = None
    magnetometer_ut: tuple[float, float, float] | None = None
    barometer_pa: float | None = None
    gnss_quality: float | None = Field(default=None, ge=0, le=1)
    satellite_count: int | None = Field(default=None, ge=0)
    hdop: float | None = None
    vdop: float | None = None
    camera_confidence: float | None = Field(default=None, ge=0, le=1)
    tracking_confidence: float | None = Field(default=None, ge=0, le=1)
    ekf_innovation_m: tuple[float, float, float] | None = None
    normalized_innovation_squared: float | None = None
    packet_delay_s: float | None = None
    packet_loss: bool | None = None
    sensor_health: dict[str, float] = Field(default_factory=dict)
    mission_mode: str
    anomaly_label: str | None = None
    safety_state: SafetyState
    origin: DataOrigin
    source: str
    scenario_id: str | None = None
    seed: int | None = None
    injected_fault: str | None = None
    fault_configuration: dict | None = None
    generator_version: str | None = None
    configuration_hash: str | None = None
