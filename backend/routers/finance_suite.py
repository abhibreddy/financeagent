"""
finance_suite.py — plain JSON endpoints for the Finance AI Suite.

Serves the selectable scenario list and the deterministic report for a chosen scenario
(the same report the agent chat streams as its data stage). Reuses modules/finance_suite/*
verbatim; only serialization is added.
"""
from fastapi import APIRouter, HTTPException

from modules.finance_suite.specs import SUITE
from modules.finance_suite.scenarios import list_scenarios, load_scenario
from modules.finance_suite.data import build_report
from backend.serializers import jsonable

router = APIRouter(prefix="/api/finance-suite", tags=["finance-suite"])


@router.get("/agents")
def agents():
    """Metadata for all six suite agents (drives nav / landing tiles)."""
    return {"agents": [
        {"key": s.key, "title": s.title, "icon": s.icon, "subtitle": s.subtitle,
         "has_report": s.has_report, "suggestions": s.suggestions}
        for s in SUITE.values()
    ]}


def _require_report_agent(agent: str):
    spec = SUITE.get(agent)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent}'")
    if not spec.has_report:
        raise HTTPException(status_code=400, detail=f"Agent '{agent}' has no scenarios")
    return spec


@router.get("/{agent}/scenarios")
def scenarios(agent: str):
    _require_report_agent(agent)
    return {"agent": agent, "scenarios": jsonable(list_scenarios(agent))}


@router.get("/{agent}/report")
def report(agent: str, scenario: str):
    _require_report_agent(agent)
    try:
        sc = load_scenario(agent, scenario)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario}' not found for '{agent}'")
    return {
        "agent": agent,
        "scenario": {"id": sc["id"], "name": sc["name"], "description": sc.get("description", "")},
        "report": jsonable(build_report(agent, sc)),
    }
