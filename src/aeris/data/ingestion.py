from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path

from aeris.data.telemetry import TelemetryRecord
from aeris.models import DataOrigin, SafetyState


class IngestionMode(StrEnum):
    SIMULATION = "simulation"
    CSV_REPLAY = "csv_replay"
    PUBLIC_DATASET = "public_dataset"
    LIVE_HARDWARE = "live_hardware"


class TelemetryAdapter(ABC):
    @abstractmethod
    def records(self) -> list[TelemetryRecord]: ...


class CsvTelemetryAdapter(TelemetryAdapter):
    """Strict adapter for canonical AERIS CSV telemetry; blanks remain unavailable."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def records(self) -> list[TelemetryRecord]:
        with self.path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        output = []
        for row in rows:
            output.append(
                TelemetryRecord(
                    timestamp=float(row["timestamp"]),
                    position_m=self._vector(row, "position"),
                    velocity_mps=self._vector(row, "velocity"),
                    acceleration_mps2=self._vector(row, "acceleration"),
                    mission_mode="csv_replay",
                    safety_state=SafetyState.NORMAL,
                    origin=DataOrigin.MEASURED,
                    source=str(self.path),
                )
            )
        return output

    @staticmethod
    def _vector(row: dict[str, str], prefix: str) -> tuple[float, float, float] | None:
        if not row.get(f"{prefix}_x"):
            return None
        return (
            float(row[f"{prefix}_x"]),
            float(row[f"{prefix}_y"]),
            float(row[f"{prefix}_z"]),
        )


class EurocImuAdapter(TelemetryAdapter):
    """Reads EuRoC MAV `mav0/imu0/data.csv`; it does not infer unavailable position."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def records(self) -> list[TelemetryRecord]:
        with self.path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        output = []
        for row in rows:
            values = list(row.values())
            timestamp = float(values[0]) * 1e-9
            output.append(
                TelemetryRecord(
                    timestamp=timestamp,
                    gyro_rps=tuple(map(float, values[1:4])),
                    acceleration_mps2=tuple(map(float, values[4:7])),
                    mission_mode="public_dataset",
                    safety_state=SafetyState.NORMAL,
                    origin=DataOrigin.PUBLIC_BENCHMARK,
                    source=str(self.path),
                )
            )
        return output


class LiveHardwareAdapter(TelemetryAdapter):
    def records(self) -> list[TelemetryRecord]:
        raise RuntimeError("Live hardware transport is unavailable; no data were fabricated.")
