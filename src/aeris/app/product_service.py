from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from aeris.app.mission_reliability import assess_mission_reliability, interpret_finding
from aeris.app.priority import assess_priority
from aeris.app.product_models import (
    ActionCreate,
    ActionUpdate,
    AIFindingCreate,
    AssetCreate,
    Domain,
    DroneCreate,
    HumanReviewCreate,
    MissionIngest,
    ProductMissionCreate,
    SyncRequest,
    TelemetryIngest,
)
from aeris.models import DataOrigin, utc_now

DEMO_TIMESTAMP = "2026-01-15T09:00:00+00:00"
DEMO_SOURCE = "aeris.demo.seed.v1"

DEMO_ASSETS = [
    (
        "BR-042",
        "Mahanadi East Bridge",
        "Bridge",
        "Cuttack",
        20.4752,
        85.8998,
        0.95,
        "2026-01-14",
        61.0,
    ),
    ("RD-109", "Ring Road Sector 9", "Road", "Cuttack", 20.4621, 85.8832, 0.82, "2026-01-13", 68.0),
    (
        "CL-018",
        "Drainage Culvert 18",
        "Culvert",
        "Cuttack",
        20.4890,
        85.9170,
        0.72,
        "2026-01-12",
        72.0,
    ),
    (
        "BR-017",
        "Kathajodi Service Bridge",
        "Bridge",
        "Cuttack",
        20.4510,
        85.8940,
        0.90,
        "2026-01-10",
        84.0,
    ),
    (
        "RD-221",
        "Bhubaneswar North Link",
        "Road",
        "Khordha",
        20.3260,
        85.8245,
        0.78,
        "2026-01-11",
        78.0,
    ),
    (
        "BL-063",
        "Ward Operations Building",
        "Building",
        "Khordha",
        20.2982,
        85.8157,
        0.70,
        "2026-01-09",
        88.0,
    ),
    ("CL-032", "Urban Culvert 32", "Culvert", "Khordha", 20.3150, 85.8400, 0.68, None, None),
    (
        "RD-305",
        "Puri Coastal Access Road",
        "Road",
        "Puri",
        19.8135,
        85.8312,
        0.86,
        "2026-01-08",
        55.0,
    ),
    ("BR-088", "Daya River Crossing", "Bridge", "Puri", 19.8580, 85.8480, 0.92, "2026-01-07", 74.0),
    (
        "BL-104",
        "Cyclone Shelter 104",
        "Building",
        "Puri",
        19.8010,
        85.8220,
        0.98,
        "2026-01-06",
        91.0,
    ),
]

DEMO_OBSERVATIONS = [
    (
        "OBS-001",
        "BR-042",
        "MIS-001",
        "possible crack",
        0.92,
        None,
        "Repeated linear surface discontinuity; requires engineering verification.",
        "evidence://demo/BR-042/frame-018.jpg",
        3,
        0.82,
        0.76,
    ),
    (
        "OBS-002",
        "RD-109",
        "MIS-002",
        "waterlogging",
        0.78,
        None,
        "Standing water visible across the carriageway edge.",
        "evidence://demo/RD-109/frame-044.jpg",
        2,
        0.67,
        0.74,
    ),
    (
        "OBS-003",
        "CL-018",
        "MIS-002",
        "obstruction",
        0.61,
        None,
        "Debris accumulation partially obstructs the inlet.",
        "evidence://demo/CL-018/frame-071.jpg",
        2,
        0.45,
        0.70,
    ),
    (
        "OBS-004",
        "BR-017",
        "MIS-001",
        "corrosion",
        0.44,
        None,
        "Surface discoloration; monitor and verify during routine inspection.",
        "evidence://demo/BR-017/frame-103.jpg",
        1,
        0.30,
        0.35,
    ),
    (
        "OBS-005",
        "RD-221",
        "MIS-003",
        "surface anomaly",
        0.69,
        None,
        "Rule-based demo observation from annotated mission package.",
        "evidence://demo/RD-221/frame-028.jpg",
        2,
        0.52,
        0.48,
    ),
    (
        "OBS-006",
        "RD-305",
        "MIS-004",
        "vegetation encroachment",
        0.84,
        None,
        "Road-edge vegetation may reduce usable shoulder width.",
        "evidence://demo/RD-305/frame-066.jpg",
        3,
        0.71,
        0.58,
    ),
    (
        "OBS-007",
        "BR-088",
        "MIS-004",
        "possible crack",
        0.58,
        None,
        "Possible surface discontinuity; physical verification required.",
        "evidence://demo/BR-088/frame-091.jpg",
        1,
        0.38,
        0.42,
    ),
]


class ProductStore:
    def __init__(self, path: Path = Path("artifacts/aeris_product.db")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY, name TEXT NOT NULL, asset_type TEXT NOT NULL,
                    district TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
                    criticality REAL NOT NULL, inspection_status TEXT NOT NULL,
                    condition_score REAL, priority TEXT NOT NULL, priority_score REAL,
                    priority_explanation TEXT NOT NULL, last_inspection TEXT,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY, name TEXT NOT NULL, mission_type TEXT NOT NULL,
                    district TEXT NOT NULL, asset_ids TEXT NOT NULL, status TEXT NOT NULL,
                    records_ingested INTEGER NOT NULL, origin TEXT NOT NULL,
                    source TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, mission_id TEXT,
                    observation_type TEXT NOT NULL, severity REAL NOT NULL, confidence REAL,
                    notes TEXT NOT NULL, evidence_uri TEXT, analysis_method TEXT NOT NULL,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
                );
                CREATE TABLE IF NOT EXISTS priority_assessments (
                    assessment_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, score REAL NOT NULL,
                    level TEXT NOT NULL, components TEXT NOT NULL, explanation TEXT NOT NULL,
                    formula TEXT NOT NULL, origin TEXT NOT NULL, source TEXT NOT NULL,
                    timestamp TEXT NOT NULL, FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
                );
                CREATE TABLE IF NOT EXISTS actions (
                    action_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL,
                    recommended_action TEXT NOT NULL, status TEXT NOT NULL, assigned_to TEXT,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
                );
                CREATE TABLE IF NOT EXISTS inspections (
                    inspection_id TEXT PRIMARY KEY, client_record_id TEXT UNIQUE NOT NULL,
                    asset_id TEXT NOT NULL, observation_type TEXT NOT NULL, severity REAL NOT NULL,
                    notes TEXT NOT NULL, latitude REAL, longitude REAL, evidence_name TEXT,
                    captured_at TEXT NOT NULL, sync_status TEXT NOT NULL,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
                );
                CREATE TABLE IF NOT EXISTS drones (
                    drone_id TEXT PRIMARY KEY, name TEXT NOT NULL, model TEXT NOT NULL,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telemetry_records (
                    telemetry_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, ts REAL NOT NULL,
                    gnss_quality REAL, satellite_count INTEGER, hdop REAL,
                    camera_confidence REAL, normalized_innovation_squared REAL,
                    packet_delay_s REAL, packet_loss INTEGER, battery_percent REAL,
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(mission_id) REFERENCES missions(mission_id)
                );
                CREATE TABLE IF NOT EXISTS mission_reliability_assessments (
                    assessment_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, level TEXT NOT NULL,
                    score REAL, components TEXT NOT NULL, weighted_components TEXT NOT NULL,
                    formula TEXT NOT NULL, reasons TEXT NOT NULL, is_simulation INTEGER NOT NULL,
                    sample_count INTEGER NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(mission_id) REFERENCES missions(mission_id)
                );
                CREATE TABLE IF NOT EXISTS ai_findings (
                    finding_id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, asset_id TEXT,
                    domain TEXT NOT NULL, task_type TEXT NOT NULL, label TEXT NOT NULL,
                    confidence REAL NOT NULL, model_name TEXT NOT NULL, model_version TEXT NOT NULL,
                    source_media TEXT, review_status TEXT NOT NULL DEFAULT 'PENDING',
                    origin TEXT NOT NULL, source TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(mission_id) REFERENCES missions(mission_id)
                );
                CREATE TABLE IF NOT EXISTS human_reviews (
                    review_id TEXT PRIMARY KEY, finding_id TEXT NOT NULL, verdict TEXT NOT NULL,
                    reviewer TEXT NOT NULL, notes TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY(finding_id) REFERENCES ai_findings(finding_id)
                );
                """
            )
            mission_columns = {
                row[1] for row in db.execute("PRAGMA table_info(missions)").fetchall()
            }
            if "domain" not in mission_columns:
                db.execute(
                    "ALTER TABLE missions ADD COLUMN domain TEXT NOT NULL DEFAULT 'infrastructure'"
                )
            if "drone_id" not in mission_columns:
                db.execute("ALTER TABLE missions ADD COLUMN drone_id TEXT")
            finding_columns = {
                row[1] for row in db.execute("PRAGMA table_info(ai_findings)").fetchall()
            }
            if "regions" not in finding_columns:
                db.execute("ALTER TABLE ai_findings ADD COLUMN regions TEXT")
            count = db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            if not count:
                self._seed(db)

    def _seed(self, db: sqlite3.Connection) -> None:
        for asset in DEMO_ASSETS:
            asset_id, name, asset_type, district, lat, lon, criticality, inspected, condition = (
                asset
            )
            db.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    asset_id,
                    name,
                    asset_type,
                    district,
                    lat,
                    lon,
                    criticality,
                    "INSPECTED" if inspected else "NOT INSPECTED",
                    condition,
                    "UNKNOWN",
                    None,
                    json.dumps(["No assessment available"]),
                    inspected,
                    DataOrigin.DEMONSTRATION,
                    DEMO_SOURCE,
                    DEMO_TIMESTAMP,
                ),
            )
        missions = [
            (
                "MIS-001",
                "Cuttack Bridge Survey",
                "Bridge Inspection",
                "Cuttack",
                ["BR-042", "BR-017"],
            ),
            (
                "MIS-002",
                "Cuttack Drainage Survey",
                "Road Inspection",
                "Cuttack",
                ["RD-109", "CL-018"],
            ),
            (
                "MIS-003",
                "Khordha Corridor Review",
                "Road Inspection",
                "Khordha",
                ["RD-221", "BL-063"],
            ),
            (
                "MIS-004",
                "Puri Resilience Survey",
                "Disaster Assessment",
                "Puri",
                ["RD-305", "BR-088", "BL-104"],
            ),
        ]
        for mission_id, name, kind, district, asset_ids in missions:
            db.execute(
                "INSERT INTO missions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    mission_id,
                    name,
                    kind,
                    district,
                    json.dumps(asset_ids),
                    "COMPLETED",
                    2480,
                    DataOrigin.DEMONSTRATION,
                    DEMO_SOURCE,
                    DEMO_TIMESTAMP,
                    Domain.INFRASTRUCTURE,
                    None,
                ),
            )
        for row in DEMO_OBSERVATIONS:
            (
                observation_id,
                asset_id,
                mission_id,
                kind,
                severity,
                confidence,
                notes,
                evidence,
                recurrence,
                trend,
                impact,
            ) = row
            db.execute(
                "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    observation_id,
                    asset_id,
                    mission_id,
                    kind,
                    severity,
                    confidence,
                    notes,
                    evidence,
                    "seeded_rule_based_demonstration",
                    DataOrigin.DEMONSTRATION,
                    DEMO_SOURCE,
                    DEMO_TIMESTAMP,
                ),
            )
            self._reassess(db, asset_id, recurrence, trend, impact, DEMO_TIMESTAMP)
        for asset_id in ("BL-063", "BL-104"):
            self._reassess(db, asset_id, 0, 0.1, 0.2, DEMO_TIMESTAMP)
        recommendations = {
            "CRITICAL": "Assign physical engineering inspection within 48 hours",
            "HIGH": "Schedule maintenance assessment",
            "MEDIUM": "Review evidence and monitor next inspection cycle",
            "LOW": "Continue routine monitoring",
        }
        rows = db.execute(
            "SELECT asset_id, priority FROM assets WHERE priority != 'UNKNOWN'"
        ).fetchall()
        for index, row in enumerate(rows, 1):
            db.execute(
                "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",
                (
                    f"ACT-{index:03d}",
                    row["asset_id"],
                    recommendations[row["priority"]],
                    "NEW",
                    None,
                    DataOrigin.DEMONSTRATION,
                    DEMO_SOURCE,
                    DEMO_TIMESTAMP,
                ),
            )

    def _reassess(
        self,
        db: sqlite3.Connection,
        asset_id: str,
        recurrence: int | None = None,
        trend: float | None = None,
        impact: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        asset = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        latest = db.execute(
            "SELECT * FROM observations WHERE asset_id=? ORDER BY timestamp DESC LIMIT 1",
            (asset_id,),
        ).fetchone()
        if not asset:
            raise KeyError(f"Asset {asset_id} was not found")
        if not latest:
            return
        recurrence = (
            recurrence
            if recurrence is not None
            else db.execute(
                "SELECT COUNT(*) FROM observations WHERE asset_id=?", (asset_id,)
            ).fetchone()[0]
        )
        result = assess_priority(
            severity=latest["severity"],
            confidence=latest["confidence"],
            criticality=asset["criticality"],
            recurrence=recurrence,
            trend=0.3 if trend is None else trend,
            geographic_impact=0.4 if impact is None else impact,
        )
        when = timestamp or utc_now()
        assessment_id = f"PA-DEMO-{asset_id}" if timestamp == DEMO_TIMESTAMP else str(uuid4())
        db.execute(
            "INSERT INTO priority_assessments VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                assessment_id,
                asset_id,
                result.score,
                result.level,
                json.dumps(result.components),
                json.dumps(result.factors),
                result.formula,
                latest["origin"],
                latest["source"],
                when,
            ),
        )
        condition = round(max(0.0, 100.0 - latest["severity"] * 60 - recurrence * 3), 1)
        db.execute(
            "UPDATE assets SET condition_score=?, priority=?, priority_score=?, "
            "priority_explanation=?, last_inspection=?, inspection_status='INSPECTED' "
            "WHERE asset_id=?",
            (
                condition,
                result.level,
                result.score,
                json.dumps(result.factors),
                when[:10],
                asset_id,
            ),
        )

    @staticmethod
    def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def executive_summary(self) -> dict[str, Any]:
        with self._connect() as db:
            totals = db.execute(
                "SELECT COUNT(*) total, SUM(inspection_status='INSPECTED') inspected, "
                "SUM(priority IN ('HIGH','CRITICAL')) high, SUM(priority='CRITICAL') critical "
                "FROM assets"
            ).fetchone()
            active = db.execute(
                "SELECT COUNT(*) FROM missions WHERE status!='COMPLETED'"
            ).fetchone()[0]
            findings = self._rows(
                db.execute(
                    "SELECT o.*, a.name asset_name, a.priority FROM observations o JOIN assets a "
                    "ON a.asset_id=o.asset_id ORDER BY o.timestamp DESC LIMIT 5"
                ).fetchall()
            )
            actions = self.priority_queue(limit=5)
            return {
                "metrics": {
                    "total_assets": totals["total"],
                    "assets_inspected": totals["inspected"],
                    "high_priority_assets": totals["high"],
                    "critical_findings": totals["critical"],
                    "active_missions": active,
                    "recent_ai_findings": len(findings),
                },
                "recent_findings": findings,
                "action_queue": actions,
                "origin": DataOrigin.DEMONSTRATION,
                "source": DEMO_SOURCE,
                "timestamp": DEMO_TIMESTAMP,
            }

    def list_assets(self, district: str | None = None, priority: str | None = None) -> list[dict]:
        query, params = "SELECT * FROM assets WHERE 1=1", []
        if district:
            query += " AND district=?"
            params.append(district)
        if priority:
            query += " AND priority=?"
            params.append(priority)
        query += (
            " ORDER BY CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 "
            "WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END"
        )
        with self._connect() as db:
            rows = self._rows(db.execute(query, params).fetchall())
        for row in rows:
            row["priority_explanation"] = json.loads(row["priority_explanation"])
        return rows

    def get_asset(self, asset_id: str) -> dict:
        with self._connect() as db:
            asset = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
            if not asset:
                raise KeyError(f"Asset {asset_id} was not found")
            result = dict(asset)
            result["priority_explanation"] = json.loads(result["priority_explanation"])
            result["observations"] = self._rows(
                db.execute(
                    "SELECT * FROM observations WHERE asset_id=? ORDER BY timestamp DESC",
                    (asset_id,),
                ).fetchall()
            )
            result["missions"] = self._rows(
                db.execute(
                    "SELECT * FROM missions WHERE asset_ids LIKE ? ORDER BY timestamp DESC",
                    (f'%"{asset_id}"%',),
                ).fetchall()
            )
            assessments = self._rows(
                db.execute(
                    "SELECT * FROM priority_assessments WHERE asset_id=? ORDER BY timestamp",
                    (asset_id,),
                ).fetchall()
            )
            for assessment in assessments:
                assessment["components"] = json.loads(assessment["components"])
                assessment["explanation"] = json.loads(assessment["explanation"])
            result["condition_trend"] = assessments
            return result

    def create_asset(self, request: AssetCreate) -> dict:
        with self._connect() as db:
            db.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    request.asset_id,
                    request.name,
                    request.asset_type,
                    request.district,
                    request.latitude,
                    request.longitude,
                    request.criticality,
                    "NOT INSPECTED",
                    None,
                    "UNKNOWN",
                    None,
                    json.dumps(["No inspection evidence available"]),
                    None,
                    request.origin,
                    request.source,
                    utc_now(),
                ),
            )
        return self.get_asset(request.asset_id)

    def list_missions(self) -> list[dict]:
        with self._connect() as db:
            rows = self._rows(
                db.execute("SELECT * FROM missions ORDER BY timestamp DESC").fetchall()
            )
        for row in rows:
            row["asset_ids"] = json.loads(row["asset_ids"])
        return rows

    def create_mission(self, request: ProductMissionCreate) -> dict:
        mission_id, timestamp = f"MIS-{uuid4().hex[:8].upper()}", utc_now()
        with self._connect() as db:
            known = {r[0] for r in db.execute("SELECT asset_id FROM assets").fetchall()}
            missing = set(request.asset_ids) - known
            if missing:
                raise KeyError(f"Unknown assets: {', '.join(sorted(missing))}")
            db.execute(
                "INSERT INTO missions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    mission_id,
                    request.name,
                    request.mission_type,
                    request.district,
                    json.dumps(request.asset_ids),
                    "CREATED",
                    0,
                    request.origin,
                    request.source,
                    timestamp,
                    request.domain,
                    request.drone_id,
                ),
            )
        return self.get_mission(mission_id)

    def get_mission(self, mission_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM missions WHERE mission_id=?", (mission_id,)).fetchone()
            if not row:
                raise KeyError(f"Mission {mission_id} was not found")
            result = dict(row)
            result["asset_ids"] = json.loads(result["asset_ids"])
            result["observations"] = self._rows(
                db.execute(
                    "SELECT * FROM observations WHERE mission_id=?", (mission_id,)
                ).fetchall()
            )
            result["ai_findings"] = [
                self._parse_finding(r)
                for r in self._rows(
                    db.execute(
                        "SELECT * FROM ai_findings WHERE mission_id=? ORDER BY timestamp DESC",
                        (mission_id,),
                    ).fetchall()
                )
            ]
            for finding in result["ai_findings"]:
                finding["reviews"] = self._rows(
                    db.execute(
                        "SELECT * FROM human_reviews WHERE finding_id=? ORDER BY timestamp DESC",
                        (finding["finding_id"],),
                    ).fetchall()
                )
            result["telemetry"] = self._rows(
                db.execute(
                    "SELECT * FROM telemetry_records WHERE mission_id=? ORDER BY ts", (mission_id,)
                ).fetchall()
            )
        result["drone"] = self.get_drone(result["drone_id"]) if result.get("drone_id") else None
        result["reliability"] = self.get_mission_reliability(mission_id)
        for finding in result["ai_findings"]:
            finding["mission_reliability"] = result["reliability"]
            self._attach_interpretation(finding)
        return result

    def ingest(self, mission_id: str, request: MissionIngest) -> dict:
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone():
                raise KeyError(f"Mission {mission_id} was not found")
            for item in request.observations:
                if not db.execute(
                    "SELECT 1 FROM assets WHERE asset_id=?", (item.asset_id,)
                ).fetchone():
                    raise KeyError(f"Asset {item.asset_id} was not found")
                db.execute(
                    "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        f"OBS-{uuid4().hex[:8].upper()}",
                        item.asset_id,
                        mission_id,
                        item.observation_type,
                        item.severity,
                        item.confidence,
                        item.notes,
                        item.evidence_uri,
                        "submitted_observation_no_model_inference",
                        item.origin,
                        item.source,
                        utc_now(),
                    ),
                )
                self._reassess(db, item.asset_id)
            db.execute(
                "UPDATE missions SET status='COMPLETED', records_ingested=? WHERE mission_id=?",
                (len(request.observations), mission_id),
            )
        return self.get_mission(mission_id)

    def priority_queue(self, limit: int | None = None) -> list[dict]:
        query = (
            "SELECT ac.*, a.name asset_name, a.asset_type, a.district, a.priority, "
            "a.priority_score, a.priority_explanation FROM actions ac JOIN assets a "
            "ON a.asset_id=ac.asset_id ORDER BY CASE a.priority WHEN 'CRITICAL' THEN 1 "
            "WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, a.priority_score DESC"
        )
        if limit:
            query += f" LIMIT {int(limit)}"
        with self._connect() as db:
            rows = self._rows(db.execute(query).fetchall())
        for row in rows:
            row["priority_explanation"] = json.loads(row["priority_explanation"])
        return rows

    def create_action(self, request: ActionCreate) -> dict:
        action_id = f"ACT-{uuid4().hex[:8].upper()}"
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM assets WHERE asset_id=?", (request.asset_id,)
            ).fetchone():
                raise KeyError(f"Asset {request.asset_id} was not found")
            db.execute(
                "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",
                (
                    action_id,
                    request.asset_id,
                    request.recommended_action,
                    request.status,
                    request.assigned_to,
                    request.origin,
                    request.source,
                    utc_now(),
                ),
            )
        return next(row for row in self.priority_queue() if row["action_id"] == action_id)

    def update_action(self, action_id: str, request: ActionUpdate) -> dict:
        with self._connect() as db:
            existing = db.execute(
                "SELECT status FROM actions WHERE action_id=?", (action_id,)
            ).fetchone()
            if not existing:
                raise KeyError(f"Action {action_id} was not found")
            allowed = {
                "NEW": {"NEW", "UNDER REVIEW", "INSPECTION ASSIGNED"},
                "UNDER REVIEW": {"UNDER REVIEW", "INSPECTION ASSIGNED", "ACTION IN PROGRESS"},
                "INSPECTION ASSIGNED": {
                    "INSPECTION ASSIGNED",
                    "ACTION IN PROGRESS",
                    "RESOLVED",
                },
                "ACTION IN PROGRESS": {"ACTION IN PROGRESS", "RESOLVED"},
                "RESOLVED": {"RESOLVED"},
            }
            if request.status not in allowed[existing["status"]]:
                raise ValueError(
                    f"Invalid action transition: {existing['status']} -> {request.status}"
                )
            cursor = db.execute(
                "UPDATE actions SET status=?, assigned_to=?, timestamp=? WHERE action_id=?",
                (request.status, request.assigned_to, utc_now(), action_id),
            )
            if not cursor.rowcount:
                raise KeyError(f"Action {action_id} was not found")
        return next(row for row in self.priority_queue() if row["action_id"] == action_id)

    def regional_analytics(self, district: str | None = None) -> dict:
        assets = self.list_assets(district=district)
        counts: dict[str, int] = {
            key: 0 for key in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
        }
        for asset in assets:
            counts[asset["priority"]] += 1
        with self._connect() as db:
            params: list[str] = []
            where = ""
            if district:
                where = " WHERE a.district=?"
                params = [district]
            observation_rows = self._rows(
                db.execute(
                    "SELECT o.observation_type, COUNT(*) count FROM observations o JOIN assets a "
                    f"ON a.asset_id=o.asset_id{where} GROUP BY o.observation_type "
                    "ORDER BY count DESC",
                    params,
                ).fetchall()
            )
        return {
            "district": district or "All districts",
            "asset_count": len(assets),
            "inspection_coverage_percent": round(
                100 * sum(a["inspection_status"] == "INSPECTED" for a in assets) / len(assets), 1
            )
            if assets
            else 0,
            "priority_distribution": counts,
            "recurring_observations": observation_rows,
            "assets": assets,
            "origin": DataOrigin.DEMONSTRATION,
            "source": DEMO_SOURCE,
            "timestamp": DEMO_TIMESTAMP,
        }

    def sync(self, request: SyncRequest) -> dict:
        accepted, duplicates = [], []
        with self._connect() as db:
            for item in request.records:
                if not db.execute(
                    "SELECT 1 FROM assets WHERE asset_id=?", (item.asset_id,)
                ).fetchone():
                    raise KeyError(f"Asset {item.asset_id} was not found")
                existing = db.execute(
                    "SELECT inspection_id FROM inspections WHERE client_record_id=?",
                    (item.client_record_id,),
                ).fetchone()
                if existing:
                    duplicates.append(item.client_record_id)
                    continue
                inspection_id = f"INSP-{uuid4().hex[:8].upper()}"
                db.execute(
                    "INSERT INTO inspections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        inspection_id,
                        item.client_record_id,
                        item.asset_id,
                        item.observation_type,
                        item.severity,
                        item.notes,
                        item.latitude,
                        item.longitude,
                        item.evidence_name,
                        item.captured_at,
                        "SYNCED",
                        item.origin,
                        item.source,
                        utc_now(),
                    ),
                )
                db.execute(
                    "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        f"OBS-{uuid4().hex[:8].upper()}",
                        item.asset_id,
                        None,
                        item.observation_type,
                        item.severity,
                        None,
                        item.notes,
                        None,
                        "field_observation_no_model_inference",
                        item.origin,
                        item.source,
                        utc_now(),
                    ),
                )
                self._reassess(db, item.asset_id)
                accepted.append(
                    {"client_record_id": item.client_record_id, "inspection_id": inspection_id}
                )
        return {"accepted": accepted, "duplicates": duplicates, "synchronized_at": utc_now()}

    # -- Drones --------------------------------------------------------------------

    def create_drone(self, request: DroneCreate) -> dict:
        with self._connect() as db:
            db.execute(
                "INSERT INTO drones VALUES (?,?,?,?,?,?)",
                (
                    request.drone_id,
                    request.name,
                    request.model,
                    request.origin,
                    request.source,
                    utc_now(),
                ),
            )
        return self.get_drone(request.drone_id)

    def get_drone(self, drone_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM drones WHERE drone_id=?", (drone_id,)).fetchone()
            if not row:
                raise KeyError(f"Drone {drone_id} was not found")
            return dict(row)

    def list_drones(self) -> list[dict]:
        with self._connect() as db:
            return self._rows(db.execute("SELECT * FROM drones ORDER BY name").fetchall())

    # -- Telemetry and Mission Reliability -------------------------------------------

    def ingest_telemetry(self, records: list[TelemetryIngest]) -> dict:
        if not records:
            raise ValueError("At least one telemetry record is required")
        mission_id = records[0].mission_id
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone():
                raise KeyError(f"Mission {mission_id} was not found")
            for record in records:
                if record.mission_id != mission_id:
                    raise ValueError(
                        "All telemetry records in one ingest call must share a mission_id"
                    )
                db.execute(
                    "INSERT INTO telemetry_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        f"TEL-{uuid4().hex[:8].upper()}",
                        record.mission_id,
                        record.timestamp,
                        record.gnss_quality,
                        record.satellite_count,
                        record.hdop,
                        record.camera_confidence,
                        record.normalized_innovation_squared,
                        record.packet_delay_s,
                        int(bool(record.packet_loss)) if record.packet_loss is not None else None,
                        record.battery_percent,
                        record.origin,
                        record.source,
                        utc_now(),
                    ),
                )
        return self.assess_mission_reliability(mission_id)

    def assess_mission_reliability(self, mission_id: str) -> dict:
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (mission_id,)
            ).fetchone():
                raise KeyError(f"Mission {mission_id} was not found")
            rows = self._rows(
                db.execute(
                    "SELECT * FROM telemetry_records WHERE mission_id=? ORDER BY ts", (mission_id,)
                ).fetchall()
            )
            result = assess_mission_reliability(rows)
            assessment_id = f"REL-{uuid4().hex[:8].upper()}"
            when = utc_now()
            db.execute(
                "INSERT INTO mission_reliability_assessments VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    assessment_id,
                    mission_id,
                    result["level"],
                    result["score"],
                    json.dumps(result["components"]),
                    json.dumps(result.get("weighted_components", {})),
                    result.get("formula", ""),
                    json.dumps(result["reasons"]),
                    int(result["is_simulation"]),
                    result["sample_count"],
                    when,
                ),
            )
        return {
            **result,
            "assessment_id": assessment_id,
            "mission_id": mission_id,
            "timestamp": when,
        }

    def get_mission_reliability(self, mission_id: str) -> dict:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM mission_reliability_assessments WHERE mission_id=? "
                "ORDER BY timestamp DESC LIMIT 1",
                (mission_id,),
            ).fetchone()
        if not row:
            return {
                "mission_id": mission_id,
                "level": "UNKNOWN",
                "score": None,
                "reasons": ["No telemetry has been ingested for this mission yet."],
                "components": {},
                "is_simulation": False,
                "sample_count": 0,
            }
        result = dict(row)
        result["components"] = json.loads(result["components"])
        result["weighted_components"] = json.loads(result["weighted_components"])
        result["reasons"] = json.loads(result["reasons"])
        result["is_simulation"] = bool(result["is_simulation"])
        return result

    # -- AI Findings and Human Review -------------------------------------------------

    def create_ai_finding(self, request: AIFindingCreate) -> dict:
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM missions WHERE mission_id=?", (request.mission_id,)
            ).fetchone():
                raise KeyError(f"Mission {request.mission_id} was not found")
            finding_id = f"AIF-{uuid4().hex[:8].upper()}"
            db.execute(
                "INSERT INTO ai_findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    finding_id,
                    request.mission_id,
                    request.asset_id,
                    request.domain,
                    request.task_type,
                    request.label,
                    request.confidence,
                    request.model_name,
                    request.model_version,
                    request.source_media,
                    "PENDING",
                    request.origin,
                    request.source,
                    utc_now(),
                    json.dumps(request.regions) if request.regions is not None else None,
                ),
            )
        return self.get_ai_finding(finding_id)

    @staticmethod
    def _parse_finding(row: dict) -> dict:
        row["regions"] = json.loads(row["regions"]) if row.get("regions") else None
        return row

    @staticmethod
    def _attach_interpretation(finding: dict) -> dict:
        finding.update(
            interpret_finding(
                finding["label"], finding["confidence"], finding["mission_reliability"]
            )
        )
        return finding

    def get_ai_finding(self, finding_id: str) -> dict:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM ai_findings WHERE finding_id=?", (finding_id,)
            ).fetchone()
            if not row:
                raise KeyError(f"Finding {finding_id} was not found")
            result = self._parse_finding(dict(row))
            result["reviews"] = self._rows(
                db.execute(
                    "SELECT * FROM human_reviews WHERE finding_id=? ORDER BY timestamp DESC",
                    (finding_id,),
                ).fetchall()
            )
            result["mission_reliability"] = self.get_mission_reliability(result["mission_id"])
        return self._attach_interpretation(result)

    def list_ai_findings(self, mission_id: str | None = None) -> list[dict]:
        query, params = "SELECT * FROM ai_findings WHERE 1=1", []
        if mission_id:
            query += " AND mission_id=?"
            params.append(mission_id)
        query += " ORDER BY timestamp DESC"
        with self._connect() as db:
            return [
                self._parse_finding(r) for r in self._rows(db.execute(query, params).fetchall())
            ]

    def review_queue(self) -> list[dict]:
        """Findings awaiting human review, annotated with mission reliability so a
        low-reliability mission's findings are never presented as equally actionable
        as a high-reliability one."""
        with self._connect() as db:
            rows = [
                self._parse_finding(r)
                for r in self._rows(
                    db.execute(
                        "SELECT * FROM ai_findings WHERE review_status='PENDING' "
                        "ORDER BY confidence DESC"
                    ).fetchall()
                )
            ]
        for row in rows:
            row["mission_reliability"] = self.get_mission_reliability(row["mission_id"])
            self._attach_interpretation(row)
        return rows

    def submit_human_review(self, finding_id: str, request: HumanReviewCreate) -> dict:
        with self._connect() as db:
            if not db.execute(
                "SELECT 1 FROM ai_findings WHERE finding_id=?", (finding_id,)
            ).fetchone():
                raise KeyError(f"Finding {finding_id} was not found")
            db.execute(
                "INSERT INTO human_reviews VALUES (?,?,?,?,?,?)",
                (
                    f"REV-{uuid4().hex[:8].upper()}",
                    finding_id,
                    request.verdict,
                    request.reviewer,
                    request.notes,
                    utc_now(),
                ),
            )
            db.execute(
                "UPDATE ai_findings SET review_status=? WHERE finding_id=?",
                (request.verdict, finding_id),
            )
        return self.get_ai_finding(finding_id)

    def export_demo(self) -> dict:
        with self._connect() as db:
            tables = {}
            for name in ("assets", "missions", "observations", "priority_assessments", "actions"):
                tables[name] = self._rows(
                    db.execute(
                        f"SELECT * FROM {name} WHERE origin=?", (DataOrigin.DEMONSTRATION,)
                    ).fetchall()
                )
        return {
            "dataset": "AERIS DEMONSTRATION DATASET",
            "seed": 2026,
            "origin": DataOrigin.DEMONSTRATION,
            "source": DEMO_SOURCE,
            "generated_at": DEMO_TIMESTAMP,
            **tables,
        }
