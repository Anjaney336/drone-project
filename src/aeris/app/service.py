from __future__ import annotations

from uuid import uuid4

from aeris.app.schemas import MissionCreate
from aeris.simulation.runner import run_scenario
from aeris.simulation.scenarios import ScenarioConfig


class MissionStore:
    def __init__(self) -> None:
        self._missions: dict[str, dict] = {}

    def create(self, request: MissionCreate) -> tuple[str, dict]:
        mission_id = str(uuid4())
        result = run_scenario(ScenarioConfig(scenario_id=request.scenario_id, seed=request.seed))
        mission = {"request": request, "result": result, "status": "completed"}
        self._missions[mission_id] = mission
        return mission_id, mission

    def get(self, mission_id: str) -> dict:
        try:
            return self._missions[mission_id]
        except KeyError as exc:
            raise KeyError(f"Mission {mission_id} was not found") from exc
