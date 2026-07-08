# tests/test_finance_suite.py
# Regression guard for the Finance AI Suite shared engine. Deterministic — the only LLM
# seam (core.llm.AzureChatOpenAI) is mocked, so no network is needed.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock

import pytest

from modules.finance_suite.scenarios import list_scenarios, load_scenario
from modules.finance_suite.data import build_report, verify_report
from modules.finance_suite.specs import SUITE

REPORT_AGENTS = ["ap", "ar", "cashflow", "reconciliation", "insights"]


def test_suite_registry_has_six_agents():
    assert set(SUITE) == {"ap", "ar", "cashflow", "reconciliation", "insights", "copilot"}
    assert SUITE["copilot"].has_report is False


@pytest.mark.parametrize("agent", REPORT_AGENTS)
def test_ten_scenarios_each(agent):
    scenarios = list_scenarios(agent)
    assert len(scenarios) == 10
    assert all({"id", "name"} <= set(s) for s in scenarios)


@pytest.mark.parametrize("agent", REPORT_AGENTS)
def test_report_is_deterministic(agent):
    sc = load_scenario(agent, list_scenarios(agent)[0]["id"])
    assert build_report(agent, sc) == build_report(agent, sc)


@pytest.mark.parametrize("agent", REPORT_AGENTS)
def test_ground_truth_passes_clean_and_catches_tamper(agent):
    sc = load_scenario(agent, list_scenarios(agent)[0]["id"])
    report = build_report(agent, sc)
    assert "GROUND TRUTH VERIFIED" in verify_report(agent, report, sc)

    scalar_key = next(k for k, v in report.items() if not isinstance(v, dict))
    tampered = dict(report, **{scalar_key: "TAMPERED"})
    result = verify_report(agent, tampered, sc)
    assert "DISCREPANCIES" in result and "MISMATCH" in result
    assert scalar_key in result


def _mock_llm():
    resp = MagicMock()
    resp.content = "Synthesized finance answer."
    resp.tool_calls = []
    llm = MagicMock()
    llm.bind_tools.return_value = llm  # Copilot's data stage binds tools
    llm.invoke.return_value = resp
    return llm


def test_copilot_tools_are_deterministic():
    """The Copilot tool-calling data stage pulls exact build_report() output (no LLM needed)."""
    import json
    from modules.finance_suite.copilot import list_finance_data, get_finance_report

    catalog = json.loads(list_finance_data.invoke({}))
    assert set(catalog) == {"ap", "ar", "cashflow", "reconciliation", "insights"}
    assert len(catalog["ap"]) == 10

    ok = json.loads(get_finance_report.invoke({"agent_key": "ap", "scenario_id": catalog["ap"][0]}))
    assert "report" in ok and "total_outstanding" in ok["report"]

    bad = json.loads(get_finance_report.invoke({"agent_key": "ap", "scenario_id": "nope"}))
    assert "error" in bad


def test_run_suite_agent_returns_three_tuple_with_debug_keys():
    with patch("core.llm.AzureChatOpenAI") as mock_cls:
        mock_cls.return_value = _mock_llm()
        from modules.finance_suite.engine import run_suite_agent
        result = run_suite_agent(
            "ap",
            messages=[{"role": "user", "content": "Summarize this scenario"}],
            session_id="test-suite",
            analyst="tester",
            scenario=list_scenarios("ap")[0]["id"],
        )
        assert isinstance(result, tuple) and len(result) == 3
        final, msgs, debug = result
        assert isinstance(final, str) and isinstance(msgs, list) and isinstance(debug, dict)
        assert {"data_agent", "ground_truth", "audit_agent"} <= set(debug)
        assert "GROUND TRUTH" in debug["ground_truth"]
        assert msgs[-1]["role"] == "assistant"


def test_copilot_runs_without_scenario():
    with patch("core.llm.AzureChatOpenAI") as mock_cls:
        mock_cls.return_value = _mock_llm()
        from modules.finance_suite.engine import run_suite_agent
        final, msgs, debug = run_suite_agent(
            "copilot",
            messages=[{"role": "user", "content": "What should we focus on?"}],
            session_id="test-copilot",
            analyst="tester",
        )
        assert isinstance(final, str)
        assert {"data_agent", "ground_truth", "audit_agent"} <= set(debug)
