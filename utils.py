import pandas as pd
import sqlite3
from datetime import timedelta
from pathlib import Path

VELOCITY_THRESHOLD = 5
DB_PATH            = "fraudguard.db"


# ── Data loading ──────────────────────────────────────────────────────────────
def load_data() -> tuple:
    txns = pd.concat([
        pd.read_csv("synthetictables/transactions.csv",  parse_dates=["timestamp"]),
        pd.read_csv("synthetictables/transactions2.csv", parse_dates=["timestamp"]),
    ]).reset_index(drop=True)
    accounts = pd.concat([
        pd.read_csv("synthetictables/accounts.csv"),
        pd.read_csv("synthetictables/accounts2.csv"),
    ]).reset_index(drop=True)
    return txns, accounts


def load_invoice_data() -> tuple:
    invoices = pd.read_csv("synthetictables/invoices.csv", parse_dates=["submitted_date"])
    vendors  = pd.read_csv("synthetictables/vendors.csv")
    return invoices, vendors


# ── Velocity computation ──────────────────────────────────────────────────────
def compute_velocity(acc_txns: pd.DataFrame) -> dict:
    if acc_txns.empty:
        return {
            "max_velocity": 0, "peak_window": (None, None),
            "geo_flags": 0, "total_amount": 0.0,
            "fraud_types": [], "risk_level": "Low", "risk_score": 0,
        }

    acc_txns = acc_txns.sort_values("timestamp")

    def txns_in_window(t):
        ws = t - timedelta(minutes=5)
        return ((acc_txns["timestamp"] >= ws) & (acc_txns["timestamp"] <= t)).sum()

    counts       = acc_txns["timestamp"].apply(txns_in_window)
    max_velocity = int(counts.max())
    peak_end_ts  = acc_txns.iloc[counts.argmax()]["timestamp"]
    peak_start_ts = peak_end_ts - timedelta(minutes=5)

    geo_flags    = int(acc_txns["geo_flag"].sum())
    total_amount = round(acc_txns["amount"].sum(), 2)
    fraud_types  = [ft for ft in acc_txns["fraud_type"].dropna().unique().tolist() if ft]

    score  = 0
    score += min(max_velocity / VELOCITY_THRESHOLD * 40, 60)
    score += min(geo_flags * 10, 30)
    score += 10 if acc_txns["is_fraud"].any() else 0
    risk_score = min(int(score), 100)

    if risk_score >= 60 or max_velocity >= 15 or geo_flags >= 3:
        risk_level = "High"
    elif risk_score >= 25 or max_velocity >= VELOCITY_THRESHOLD or geo_flags > 0:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "max_velocity":  max_velocity,
        "peak_window":   (peak_start_ts, peak_end_ts),
        "geo_flags":     geo_flags,
        "total_amount":  total_amount,
        "fraud_types":   fraud_types,
        "risk_level":    risk_level,
        "risk_score":    risk_score,
    }


def build_alert_queue(txns: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
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


# ── Invoice fraud helpers ─────────────────────────────────────────────────────
def analyze_invoice(invoice_id: str, invoices: pd.DataFrame, vendors: pd.DataFrame) -> dict:
    inv_row = invoices[invoices["invoice_id"] == invoice_id]
    if inv_row.empty:
        return {}

    inv    = inv_row.iloc[0]
    vendor_row = vendors[vendors["vendor_id"] == inv["vendor_id"]]
    vendor = vendor_row.iloc[0] if not vendor_row.empty else None

    signals = []
    score   = 0

    if pd.notna(inv.get("duplicate_of")) and inv["duplicate_of"]:
        signals.append({
            "type":   "danger",
            "icon":   "📄",
            "title":  "Duplicate invoice detected",
            "detail": "This invoice appears to be a resubmission of " + str(inv["duplicate_of"]) + ". Duplicate invoices are a common payment fraud vector.",
        })
        score += 45

    if not inv["po_match"]:
        signals.append({
            "type":   "danger",
            "icon":   "🔍",
            "title":  "No purchase order match",
            "detail": "Invoice has no corresponding approved PO. Phantom billing often bypasses PO controls.",
        })
        score += 20

    if inv["amount_altered"] and pd.notna(inv.get("original_amount")):
        pct = round((inv["amount"] - inv["original_amount"]) / inv["original_amount"] * 100, 1)
        signals.append({
            "type":   "danger",
            "icon":   "✏️",
            "title":  "Amount appears altered",
            "detail": "Invoice amount ${:,.2f} is {:.1f}% above original PO amount of ${:,.2f}.".format(
                inv["amount"], pct, inv["original_amount"]
            ),
        })
        score += 30

    if inv["bank_changed"]:
        signals.append({
            "type":   "danger",
            "icon":   "🏦",
            "title":  "Payment bank account changed",
            "detail": "Vendor bank account updated within 48h of invoice submission — high-confidence BEC or insider manipulation signal.",
        })
        score += 30

    if vendor is not None:
        if vendor["is_shell"]:
            signals.append({
                "type":   "danger",
                "icon":   "🏢",
                "title":  "Possible shell company",
                "detail": "Vendor address is a " + str(vendor["address_type"]) + " in " + str(vendor["state"]) + " — common shell company registration pattern.",
            })
            score += 30

        if vendor["days_registered"] < 30:
            signals.append({
                "type":   "warning",
                "icon":   "📅",
                "title":  "New vendor",
                "detail": "Vendor registered only " + str(int(vendor["days_registered"])) + " days ago. Large first invoice is elevated risk.",
            })
            score += 20

        if not vendor["ein_verified"]:
            signals.append({
                "type":   "warning",
                "icon":   "🪪",
                "title":  "EIN not verified",
                "detail": "Vendor EIN could not be matched against IRS business registry.",
            })
            score += 15

        if not vendor["kyc_verified"]:
            signals.append({
                "type":   "warning",
                "icon":   "⚠️",
                "title":  "KYC not completed",
                "detail": "Vendor onboarding KYC checks have not been completed.",
            })
            score += 10

        if vendor["prior_invoices"] > 0 and inv["amount"] > vendor["avg_invoice_amt"] * 3:
            signals.append({
                "type":   "warning",
                "icon":   "💰",
                "title":  "Amount far above vendor average",
                "detail": "Invoice is {:.1f}× above vendor's average of ${:,.2f}.".format(
                    inv["amount"] / vendor["avg_invoice_amt"], vendor["avg_invoice_amt"]
                ),
            })
            score += 10

    risk_score = min(int(score), 100)
    risk_level = "High" if risk_score >= 60 else "Medium" if risk_score >= 25 else "Low"

    return {
        "invoice":    inv,
        "vendor":     vendor,
        "signals":    signals,
        "risk_score": risk_score,
        "risk_level": risk_level,
    }


def build_invoice_queue(invoices: pd.DataFrame, vendors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, inv in invoices.iterrows():
        result = analyze_invoice(inv["invoice_id"], invoices, vendors)
        if not result or result["risk_level"] not in ("High", "Medium"):
            continue
        rows.append({
            "invoice_id":   inv["invoice_id"],
            "vendor_name":  inv["vendor_name"],
            "category":     inv["category"],
            "amount":       inv["amount"],
            "submitted":    inv["submitted_date"].date().isoformat() if pd.notna(inv["submitted_date"]) else "",
            "fraud_type":   inv["fraud_type"] if pd.notna(inv["fraud_type"]) else "flagged",
            "risk_level":   result["risk_level"],
            "risk_score":   result["risk_score"],
            "signal_count": len(result["signals"]),
            "status":       inv["status"],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("risk_score", ascending=False).reset_index(drop=True)


# ── SQLite ────────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS alert_decisions (
            account_id  TEXT PRIMARY KEY,
            decision    TEXT,
            analyst     TEXT,
            notes       TEXT,
            decided_at  TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS invoice_decisions (
            invoice_id  TEXT PRIMARY KEY,
            decision    TEXT,
            analyst     TEXT,
            notes       TEXT,
            decided_at  TEXT
        )
    """)
    con.commit()
    con.close()


def get_decisions() -> dict:
    init_db()
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT * FROM alert_decisions").fetchall()
    con.close()
    cols = ["account_id", "decision", "analyst", "notes", "decided_at"]
    return {r[0]: dict(zip(cols, r)) for r in rows}


def get_invoice_decisions() -> dict:
    init_db()
    con  = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT * FROM invoice_decisions").fetchall()
    con.close()
    cols = ["invoice_id", "decision", "analyst", "notes", "decided_at"]
    return {r[0]: dict(zip(cols, r)) for r in rows}


def save_decision(account_id: str, decision: str, analyst: str, notes: str):
    init_db()
    from datetime import datetime
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO alert_decisions (account_id, decision, analyst, notes, decided_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            decision=excluded.decision, analyst=excluded.analyst,
            notes=excluded.notes, decided_at=excluded.decided_at
    """, (account_id, decision, analyst, notes, datetime.now().isoformat()))
    con.commit()
    con.close()


def save_invoice_decision(invoice_id: str, decision: str, analyst: str, notes: str):
    init_db()
    from datetime import datetime
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        INSERT INTO invoice_decisions (invoice_id, decision, analyst, notes, decided_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(invoice_id) DO UPDATE SET
            decision=excluded.decision, analyst=excluded.analyst,
            notes=excluded.notes, decided_at=excluded.decided_at
    """, (invoice_id, decision, analyst, notes, datetime.now().isoformat()))
    con.commit()
    con.close()