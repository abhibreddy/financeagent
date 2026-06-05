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
