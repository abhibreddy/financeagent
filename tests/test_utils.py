# tests/test_utils.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest
from utils import compute_velocity, compare_accounts


def _make_txns(account_id, timestamps, geo_flags=None):
    n = len(timestamps)
    return pd.DataFrame({
        "account_id":    [account_id] * n,
        "timestamp":     pd.to_datetime(timestamps),
        "amount":        [100.0] * n,
        "txn_type":      ["Purchase"] * n,
        "city":          ["NYC"] * n,
        "status":        ["Completed"] * n,
        "velocity_flag": [False] * n,
        "geo_flag":      geo_flags if geo_flags else [False] * n,
        "is_fraud":      [False] * n,
        "fraud_type":    [None] * n,
        "merchant":      ["ACME"] * n,
    })


def test_compute_velocity_empty():
    result = compute_velocity(pd.DataFrame())
    assert result["max_velocity"] == 0
    assert result["risk_level"] == "Low"


def test_compute_velocity_high():
    timestamps = [
        "2024-01-01 10:00", "2024-01-01 10:01", "2024-01-01 10:02",
        "2024-01-01 10:03", "2024-01-01 10:04", "2024-01-01 10:05",
    ]
    txns = _make_txns("ACC-001", timestamps)
    result = compute_velocity(txns)
    assert result["max_velocity"] >= 5
    assert result["risk_level"] in ("Medium", "High")


def test_compute_velocity_geo_flags():
    txns = _make_txns("ACC-002",
                      ["2024-01-01 10:00", "2024-01-01 10:01", "2024-01-01 10:02"],
                      geo_flags=[True, True, True])
    result = compute_velocity(txns)
    assert result["geo_flags"] == 3
    assert result["risk_level"] == "High"


def test_compare_accounts_returns_list():
    from utils import load_data
    txns, accounts = load_data()
    ids = txns["account_id"].unique()[:2].tolist()
    result = compare_accounts(ids, txns, accounts)
    assert isinstance(result, list)
    assert len(result) == 2
    assert "account_id" in result[0]
    assert "risk_score" in result[0]
    assert "max_velocity" in result[0]


def test_compare_accounts_unknown_id():
    from utils import load_data
    txns, accounts = load_data()
    result = compare_accounts(["DOES-NOT-EXIST"], txns, accounts)
    assert result == []


# ── Invoice fraud detection ────────────────────────────────────────────────────
from utils import (
    detect_exact_duplicates, detect_near_duplicates, detect_split_billing,
    detect_threshold_avoidance, detect_ghost_vendors, build_invoice_risk_report,
)


def test_detect_exact_duplicates_finds_duplicates():
    df = pd.DataFrame([
        {"invoice_id": "INV-001", "vendor": "ACME", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-002", "vendor": "ACME", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-003", "vendor": "ACME", "amount": 2000.0, "date": pd.Timestamp("2024-01-01")},
    ])
    result = detect_exact_duplicates(df)
    assert len(result) == 2
    assert set(result["invoice_id"]) == {"INV-001", "INV-002"}


def test_detect_exact_duplicates_no_false_positives():
    df = pd.DataFrame([
        {"invoice_id": "INV-001", "vendor": "ACME", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-002", "vendor": "ACME", "amount": 2000.0, "date": pd.Timestamp("2024-01-01")},
    ])
    result = detect_exact_duplicates(df)
    assert result.empty


def test_detect_threshold_avoidance():
    df = pd.DataFrame([
        {"invoice_id": "INV-001", "vendor": "A", "amount": 9800.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-002", "vendor": "B", "amount": 5000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-003", "vendor": "C", "amount": 10500.0, "date": pd.Timestamp("2024-01-01")},
    ])
    result = detect_threshold_avoidance(df)
    assert len(result) == 1
    assert result.iloc[0]["invoice_id"] == "INV-001"


def test_detect_ghost_vendors():
    df = pd.DataFrame(
        [{"invoice_id": f"INV-{i:03d}", "vendor": "BigCo", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")} for i in range(5)]
        + [{"invoice_id": "INV-099", "vendor": "Ghost LLC", "amount": 5000.0, "date": pd.Timestamp("2024-01-01")}]
    )
    result = detect_ghost_vendors(df)
    assert len(result) == 1
    assert result.iloc[0]["vendor"] == "Ghost LLC"


def test_build_invoice_risk_report_on_real_data():
    df = pd.read_csv("synthetictables/invoices.csv", parse_dates=["date"])
    report = build_invoice_risk_report(df)
    assert "total_invoices" in report
    assert "flagged_count" in report
    assert report["flagged_count"] > 0
    assert isinstance(report["exact_duplicates"], list)
    assert isinstance(report["ghost_vendors"], list)


def test_run_agent_returns_tuple():
    """Smoke test: run_agent returns (str, list) with mocked LLM."""
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.content = "Account ACC-001 shows high risk."
    mock_response.tool_calls = []

    with patch("agent.ChatOllama") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        from agent import run_agent
        result = run_agent(
            messages=[{"role": "user", "content": "Check ACC-00009"}],
            session_id="test-abc",
            analyst="tester",
        )
        assert isinstance(result, tuple) and len(result) == 2
        text, msgs = result
        assert isinstance(text, str) and isinstance(msgs, list)
