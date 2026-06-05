import pandas as pd
import sqlite3
from datetime import timedelta
from pathlib import Path

VELOCITY_THRESHOLD = 5   # txns per 5-min window
DB_PATH            = "fraudguard.db"


# ── Data loading ──────────────────────────────────────────────────────────────
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    txns     = pd.read_csv("synthetictables/transactions.csv", parse_dates=["timestamp"])
    accounts = pd.read_csv("synthetictables/accounts.csv")
    return txns, accounts


# ── Velocity computation ──────────────────────────────────────────────────────
def compute_velocity(acc_txns: pd.DataFrame) -> dict:
    """
    For a single account's transactions, compute:
      - max_velocity  : highest txn count in any 5-min rolling window
      - peak_window   : (start, end) timestamps of that worst window
      - geo_flags     : number of geo-anomaly flagged transactions
      - total_amount  : sum of all transaction amounts
      - fraud_types   : list of distinct fraud_type values seen
      - risk_level    : High / Medium / Low
      - risk_score    : 0–100 numeric score for sorting
    """
    if acc_txns.empty:
        return {
            "max_velocity": 0, "peak_window": (None, None),
            "geo_flags": 0, "total_amount": 0.0,
            "fraud_types": [], "risk_level": "Low", "risk_score": 0,
        }

    acc_txns = acc_txns.sort_values("timestamp")

    # Rolling 5-min window count
    def txns_in_window(t):
        ws = t - timedelta(minutes=5)
        return ((acc_txns["timestamp"] >= ws) & (acc_txns["timestamp"] <= t)).sum()

    counts       = acc_txns["timestamp"].apply(txns_in_window)
    max_velocity = int(counts.max())

    # Find the actual peak window timestamps
    peak_end_ts   = acc_txns.iloc[counts.argmax()]["timestamp"]
    peak_start_ts = peak_end_ts - timedelta(minutes=5)

    geo_flags    = int(acc_txns["geo_flag"].sum())
    total_amount = round(acc_txns["amount"].sum(), 2)
    fraud_types  = [ft for ft in acc_txns["fraud_type"].dropna().unique().tolist() if ft]

    # Risk scoring: weighted combination of signals
    score = 0
    score += min(max_velocity / VELOCITY_THRESHOLD * 40, 60)  # up to 60 pts for velocity
    score += min(geo_flags * 10, 30)                          # up to 30 pts for geo flags
    score += 10 if not acc_txns.empty and acc_txns["is_fraud"].any() else 0
    risk_score = min(int(score), 100)

    if risk_score >= 60 or max_velocity >= 15 or geo_flags >= 3:
        risk_level = "High"
    elif risk_score >= 25 or max_velocity >= VELOCITY_THRESHOLD or geo_flags > 0:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "max_velocity": max_velocity,
        "peak_window":  (peak_start_ts, peak_end_ts),
        "geo_flags":    geo_flags,
        "total_amount": total_amount,
        "fraud_types":  fraud_types,
        "risk_level":   risk_level,
        "risk_score":   risk_score,
    }


def build_alert_queue(txns: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """
    Compute velocity for every account and return a ranked DataFrame
    of flagged accounts for the alert queue.
    """
    rows = []
    for acc_id, group in txns.groupby("account_id"):
        v = compute_velocity(group)
        if v["risk_level"] in ("High", "Medium"):
            acc = accounts[accounts["account_id"] == acc_id]
            if acc.empty:
                continue
            acc = acc.iloc[0]
            rows.append({
                "account_id":   acc_id,
                "customer":     acc["customer_name"],
                "account_type": acc["account_type"],
                "home_city":    acc["home_city"],
                "risk_level":   v["risk_level"],
                "risk_score":   v["risk_score"],
                "max_velocity": v["max_velocity"],
                "geo_flags":    v["geo_flags"],
                "total_amount": v["total_amount"],
                "fraud_types":  ", ".join(v["fraud_types"]) if v["fraud_types"] else "—",
                "is_dormant":   bool(acc["is_dormant"]),
                "kyc_verified": bool(acc["kyc_verified"]),
                "peak_start":   v["peak_window"][0],
                "peak_end":     v["peak_window"][1],
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("risk_score", ascending=False).reset_index(drop=True)


# ── SQLite — alert decisions ──────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS alert_decisions (
            account_id  TEXT PRIMARY KEY,
            decision    TEXT,       -- 'blocked', 'cleared', 'escalated', 'monitoring'
            analyst     TEXT,
            notes       TEXT,
            decided_at  TEXT
        )
    """)
    con.commit()
    con.close()


def get_decisions() -> dict:
    """Return {account_id: decision_row} for all decided accounts."""
    init_db()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT * FROM alert_decisions").fetchall()
    con.close()
    cols = ["account_id", "decision", "analyst", "notes", "decided_at"]
    return {r[0]: dict(zip(cols, r)) for r in rows}


def save_decision(account_id: str, decision: str, analyst: str, notes: str):
    init_db()
    from datetime import datetime
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO alert_decisions (account_id, decision, analyst, notes, decided_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            decision=excluded.decision,
            analyst=excluded.analyst,
            notes=excluded.notes,
            decided_at=excluded.decided_at
    """, (account_id, decision, analyst, notes, datetime.now().isoformat()))
    con.commit()
    con.close()


# ── Multi-account comparison ──────────────────────────────────────────────────
def compare_accounts(account_ids: list, txns: pd.DataFrame, accounts: pd.DataFrame) -> list:
    """
    Return a list of velocity + account summary dicts for each account_id.
    Used for the multi-account comparison view.
    """
    results = []
    for acc_id in account_ids:
        acc_row = accounts[accounts["account_id"] == acc_id]
        acc_txns = txns[txns["account_id"] == acc_id]
        if acc_row.empty:
            continue
        acc = acc_row.iloc[0]
        v = compute_velocity(acc_txns.copy())
        results.append({
            "account_id":   acc_id,
            "customer":     acc["customer_name"],
            "account_type": acc["account_type"],
            "home_city":    acc["home_city"],
            "risk_tier":    acc["risk_tier"],
            "kyc_verified": bool(acc["kyc_verified"]),
            "is_dormant":   bool(acc["is_dormant"]),
            "dormant_days": int(acc["dormant_days"]),
            "risk_score":   v["risk_score"],
            "risk_level":   v["risk_level"],
            "max_velocity": v["max_velocity"],
            "geo_flags":    v["geo_flags"],
            "total_amount": v["total_amount"],
            "fraud_types":  v["fraud_types"],
            "peak_window":  v["peak_window"],
            "txn_count":    len(acc_txns),
        })
    return results


# ── Invoice fraud detection ────────────────────────────────────────────────────
APPROVAL_THRESHOLD = 10_000.0
THRESHOLD_BAND     = 500.0
SPLIT_WINDOW_DAYS  = 7
SPLIT_MIN_COUNT    = 4


def load_invoices() -> pd.DataFrame:
    df = pd.read_csv("synthetictables/invoices.csv", parse_dates=["date"])
    return df


def detect_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows that share the same vendor + amount + date as another row."""
    key = ["vendor", "amount", "date"]
    counts = df.groupby(key)["invoice_id"].transform("count")
    return df[counts > 1].copy()


def detect_near_duplicates(df: pd.DataFrame, amount_tolerance: float = 0.01,
                            day_window: int = 3) -> pd.DataFrame:
    """
    Return rows where the same vendor billed a very similar amount within day_window days.
    Skips pairs already caught by exact duplicate detection.
    """
    df = df.sort_values(["vendor", "date"]).reset_index(drop=True)
    flagged_indices = set()
    for vendor, group in df.groupby("vendor"):
        idxs = group.index.tolist()
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                ri, rj = df.loc[idxs[i]], df.loc[idxs[j]]
                day_diff = abs((rj["date"] - ri["date"]).days)
                amt_diff = abs(ri["amount"] - rj["amount"]) / max(ri["amount"], 1)
                if day_diff <= day_window and amt_diff <= amount_tolerance:
                    if ri["date"] != rj["date"] or ri["amount"] != rj["amount"]:
                        flagged_indices.update([idxs[i], idxs[j]])
    return df.loc[list(flagged_indices)].copy()


def detect_split_billing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return rows where a vendor submits SPLIT_MIN_COUNT+ invoices
    within SPLIT_WINDOW_DAYS days.
    """
    df = df.sort_values(["vendor", "date"]).reset_index(drop=True)
    flagged = []
    for vendor, group in df.groupby("vendor"):
        group = group.sort_values("date")
        dates = group["date"].tolist()
        for i, anchor in enumerate(dates):
            window_end = anchor + pd.Timedelta(days=SPLIT_WINDOW_DAYS)
            in_window = group[(group["date"] >= anchor) & (group["date"] <= window_end)]
            if len(in_window) >= SPLIT_MIN_COUNT:
                flagged.extend(in_window.index.tolist())
    return df.loc[list(set(flagged))].copy()


def detect_threshold_avoidance(df: pd.DataFrame) -> pd.DataFrame:
    """Return invoices that fall just below the approval threshold."""
    lower = APPROVAL_THRESHOLD - THRESHOLD_BAND
    return df[(df["amount"] >= lower) & (df["amount"] < APPROVAL_THRESHOLD)].copy()


def detect_ghost_vendors(df: pd.DataFrame, known_vendors: list = None) -> pd.DataFrame:
    """
    Return invoices from vendors who appear in fewer than 3 invoices total.
    """
    freq = df["vendor"].value_counts()
    rare = freq[freq < 3].index.tolist()
    if known_vendors:
        rare = [v for v in rare if v not in known_vendors]
    return df[df["vendor"].isin(rare)].copy()


def build_invoice_risk_report(df: pd.DataFrame) -> dict:
    """Run all detection passes and return a consolidated risk report dict."""
    exact_dups = detect_exact_duplicates(df)
    near_dups  = detect_near_duplicates(df)
    splits     = detect_split_billing(df)
    threshold  = detect_threshold_avoidance(df)
    ghosts     = detect_ghost_vendors(df)

    all_flagged = pd.concat([exact_dups, near_dups, splits, threshold, ghosts]).drop_duplicates("invoice_id")

    return {
        "total_invoices":       len(df),
        "flagged_count":        len(all_flagged),
        "exact_duplicates":     exact_dups.to_dict("records"),
        "near_duplicates":      near_dups.to_dict("records"),
        "split_billing":        splits.to_dict("records"),
        "threshold_avoidance":  threshold.to_dict("records"),
        "ghost_vendors":        ghosts.to_dict("records"),
        "total_flagged_amount": float(all_flagged["amount"].sum()),
    }
