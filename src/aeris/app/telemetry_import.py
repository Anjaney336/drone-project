"""Parse user-supplied telemetry CSV/JSON into TelemetryIngest rows.

Adapts to whatever columns are actually present — a file with only a battery
column produces rows with only battery_percent set; nothing is invented for
missing fields. Column names are matched case-insensitively against known
aliases so a real drone log's slightly different header names still work.

Rows are tagged USER_UPLOADED, not FIELD. A file a user attaches through the
browser is not a measurement from an instrumented field deployment, and the two
must stay structurally distinguishable in the database.
"""

from __future__ import annotations

import csv
import io
import json

from aeris.app.product_models import TelemetryIngest
from aeris.models import DataOrigin

COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "ts", "t"],
    "gnss_quality": ["gnss_quality", "gnss", "gps_quality", "gps"],
    "satellite_count": ["satellite_count", "satellites", "num_satellites", "sats"],
    "hdop": ["hdop"],
    "camera_confidence": ["camera_confidence", "camera_conf", "camera"],
    "normalized_innovation_squared": ["nis", "normalized_innovation_squared"],
    "packet_delay_s": ["packet_delay_s", "packet_delay", "delay_s", "delay"],
    "packet_loss": ["packet_loss", "loss"],
    "battery_percent": ["battery_percent", "battery", "battery_pct", "battery_level"],
}

BOOL_TRUE = {"1", "true", "yes", "y", "t"}


def _find_column(header: list[str], aliases: list[str]) -> str | None:
    lower = {h.lower().strip(): h for h in header}
    for alias in aliases:
        if alias in lower:
            return lower[alias]
    return None


def _coerce(field: str, raw: str | None):
    if raw is None or str(raw).strip() == "":
        return None
    raw = str(raw).strip()
    if field == "packet_loss":
        return raw.lower() in BOOL_TRUE
    try:
        return float(raw) if field != "satellite_count" else int(float(raw))
    except ValueError:
        return None


def parse_telemetry_csv(
    content: bytes, mission_id: str, source: str
) -> tuple[list[TelemetryIngest], list[str]]:
    """Returns (rows, recognized_columns). Raises ValueError on structurally unusable input."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")
    header = list(reader.fieldnames)
    column_map: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        found = _find_column(header, aliases)
        if found:
            column_map[field] = found
    if "timestamp" not in column_map:
        raise ValueError(
            f"No recognizable timestamp column found. Header was: {header}. "
            f"Expected one of: {COLUMN_ALIASES['timestamp']}"
        )

    rows: list[TelemetryIngest] = []
    for index, row in enumerate(reader):
        kwargs: dict = {
            "mission_id": mission_id,
            "origin": DataOrigin.USER_UPLOADED,
            "source": source,
        }
        for field, column_name in column_map.items():
            value = _coerce(field, row.get(column_name))
            if value is not None:
                kwargs[field] = value
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = float(index)
        rows.append(TelemetryIngest(**kwargs))
    return rows, sorted(column_map.keys())


def parse_telemetry_json(
    content: bytes, mission_id: str, source: str
) -> tuple[list[TelemetryIngest], list[str]]:
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON telemetry file must be a list of records")
    rows: list[TelemetryIngest] = []
    seen_fields: set[str] = set()
    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} is not an object")
        # Resolve aliases exactly as the CSV path does. Matching only canonical names
        # here would silently drop a `battery` or `gps` key that the same file would
        # have been read from in CSV form.
        kwargs: dict = {
            "mission_id": mission_id,
            "origin": DataOrigin.USER_UPLOADED,
            "source": source,
        }
        for field, aliases in COLUMN_ALIASES.items():
            found = _find_column(list(record), aliases)
            if found is None or record[found] is None:
                continue
            value = record[found] if field != "packet_loss" else bool(record[found])
            kwargs[field] = value
            seen_fields.add(field)
        kwargs.setdefault("timestamp", float(index))
        rows.append(TelemetryIngest(**kwargs))
    return rows, sorted(seen_fields)
