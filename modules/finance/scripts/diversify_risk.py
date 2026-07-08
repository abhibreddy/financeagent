"""
diversify_risk.py — inject Medium-risk accounts into the transaction data.

The generated data was bimodal (15 High, 185 Low, 0 Medium), so the alert queue only ever
showed High accounts. This promotes a deterministic set of Low accounts to Medium with varied
signals — some via a velocity burst, some via geo-anomaly flags — so the queue shows a realistic
mix of Low / Medium / High. Idempotent: re-running overwrites the same injected txn ids and the
same geo flips, so risk levels don't drift.

Run: python3 -m modules.finance.scripts.diversify_risk
"""
from __future__ import annotations

import pandas as pd

from core.config import FINANCE_DATA
from modules.finance.utils import compute_velocity

TX_PATH = FINANCE_DATA / "transactions.csv"

# Deterministic promotions. velocity=N injects N txns in a 5-min window (Medium via velocity);
# geo=G flips G existing rows' geo_flag True (Medium via geo). Kept below High thresholds
# (velocity < 15, geo < 3, score < 60).
VELOCITY_PROMOTIONS = {"count": [5, 6, 7, 5, 6]}   # 5 accounts
GEO_PROMOTIONS = {"flags": [1, 2, 2, 1, 2]}        # 5 accounts
BURST_BASE = "2025-03-01 10:00:00"


def _low_accounts(df: pd.DataFrame) -> list[str]:
    levels = {a: compute_velocity(g)["risk_level"] for a, g in df.groupby("account_id")}
    return sorted(a for a, lvl in levels.items() if lvl == "Low")


def main():
    df = pd.read_csv(TX_PATH, parse_dates=["timestamp"])
    lows = _low_accounts(df)
    n_vel = len(VELOCITY_PROMOTIONS["count"])
    vel_accts, geo_accts = lows[:n_vel], lows[n_vel:n_vel + len(GEO_PROMOTIONS["flags"])]

    # Drop any previously-injected burst rows so re-runs are idempotent.
    df = df[~df["txn_id"].str.startswith("TXN-MED-", na=False)]

    new_rows = []
    for acc, n in zip(vel_accts, VELOCITY_PROMOTIONS["count"]):
        template = df[df["account_id"] == acc].iloc[0]
        base = pd.Timestamp(BURST_BASE)
        for i in range(n):
            new_rows.append({
                **template.to_dict(),
                "txn_id": f"TXN-MED-{acc}-{i}",
                "timestamp": base + pd.Timedelta(seconds=40 * i),  # N txns inside a 5-min window
                "amount": 120.0 + i,
                "is_fraud": False, "fraud_type": None,
                "velocity_flag": True, "geo_flag": False,
                "notes": "synthetic medium-risk velocity burst",
            })

    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    # Geo-based Medium: flip the first G rows of each account to geo_flag True.
    for acc, g in zip(geo_accts, GEO_PROMOTIONS["flags"]):
        idx = df.index[df["account_id"] == acc][:g]
        df.loc[idx, "geo_flag"] = True

    df = df.sort_values(["account_id", "timestamp"]).reset_index(drop=True)
    df.to_csv(TX_PATH, index=False)

    # Report the new distribution.
    from collections import Counter
    levels = Counter(compute_velocity(g)["risk_level"] for _, g in df.groupby("account_id"))
    print(f"promoted via velocity: {vel_accts}")
    print(f"promoted via geo:      {geo_accts}")
    print(f"new distribution: {dict(levels)}  (rows: {len(df)})")


if __name__ == "__main__":
    main()
