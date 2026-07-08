"""
scenarios.py — load the selectable mock-scenario fixtures for each suite agent.

Each modules/finance_suite/data/<agent>.json is a list of scenarios:
    {"id", "name", "description", "dataset": {...}}
Copilot has no fixtures (it routes across the other agents) and returns [].
"""
from __future__ import annotations

import json
from functools import lru_cache

from core.config import FINANCE_SUITE_DATA


@lru_cache(maxsize=None)
def _load_file(agent: str) -> tuple:
    path = FINANCE_SUITE_DATA / f"{agent}.json"
    if not path.exists():
        return tuple()
    with open(path, encoding="utf-8") as fh:
        return tuple(json.load(fh))


def list_scenarios(agent: str) -> list[dict]:
    """Return the scenarios for an agent as lightweight cards (id/name/description, no dataset)."""
    return [{"id": s["id"], "name": s["name"], "description": s.get("description", "")}
            for s in _load_file(agent)]


def load_scenario(agent: str, scenario_id: str) -> dict:
    """Return the full scenario (including its dataset). Raises KeyError if not found."""
    for s in _load_file(agent):
        if s["id"] == scenario_id:
            return s
    raise KeyError(f"Scenario '{scenario_id}' not found for agent '{agent}'")
