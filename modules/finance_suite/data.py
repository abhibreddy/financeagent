"""
data.py — deterministic report builders for the Finance AI Suite.

Each build_<agent>_report(scenario) is a PURE function over scenario["dataset"]:
same input -> same dict, no LLM, no network, no clock. These reports ARE the ground
truth. The engine feeds a report into the LLM audit/synthesis stages, and verify_report()
recomputes it to catch any tampering (the generic analogue of the fraud agent's
_verify_data_summary hallucination guard).

Datasets use `due_in_days` (relative to "today", negative = overdue) instead of absolute
dates so every metric is deterministic and clock-independent.
"""
from __future__ import annotations

import pandas as pd


def _round(x, n=2):
    return round(float(x), n)


# ── AP: Accounts Payable ──────────────────────────────────────────────────────
def build_ap_report(scenario: dict) -> dict:
    bills = pd.DataFrame(scenario["dataset"]["bills"])
    total = _round(bills["amount"].sum())

    def _bucket(row):
        d = row["due_in_days"]
        if d >= 0:
            return "current"
        d = -d
        if d <= 30:
            return "d1_30"
        if d <= 60:
            return "d31_60"
        return "d60_plus"

    bills = bills.assign(bucket=bills.apply(_bucket, axis=1))
    aging = {b: _round(bills.loc[bills["bucket"] == b, "amount"].sum())
             for b in ("current", "d1_30", "d31_60", "d60_plus")}

    overdue = bills[bills["due_in_days"] < 0]
    # Early-pay discount still available: discount offered AND not yet past the discount window.
    disc = bills[(bills.get("discount_pct", 0) > 0) & (bills["due_in_days"] >= 0)]
    early_pay_savings = _round((disc["amount"] * disc.get("discount_pct", 0) / 100).sum()) if not disc.empty else 0.0
    dup = bills.groupby(["vendor", "amount"]).size()
    duplicate_po_risk = int((dup > 1).sum())

    return {
        "total_outstanding": total,
        "aging": aging,
        "overdue_count": int(len(overdue)),
        "overdue_amount": _round(overdue["amount"].sum()),
        "early_pay_savings": early_pay_savings,
        "duplicate_po_risk": duplicate_po_risk,
        "bill_count": int(len(bills)),
    }


# ── AR: Accounts Receivable ───────────────────────────────────────────────────
def build_ar_report(scenario: dict) -> dict:
    inv = pd.DataFrame(scenario["dataset"]["invoices"])
    total = _round(inv["amount"].sum())
    overdue = inv[inv["due_in_days"] < 0]
    disputed = inv[inv.get("disputed", False) == True]  # noqa: E712 — pandas boolean mask
    at_risk = inv[(inv.get("disputed", False) == True) | (inv["due_in_days"] < -60)]  # noqa: E712

    # Weighted DSO proxy: amount-weighted average of days outstanding (overdue -> positive age).
    ages = (-inv["due_in_days"]).clip(lower=0)
    dso = _round((ages * inv["amount"]).sum() / inv["amount"].sum()) if inv["amount"].sum() else 0.0

    dunning = (
        overdue.groupby("customer")["amount"].sum().sort_values(ascending=False)
        .head(3).round(2).to_dict()
    )

    return {
        "total_receivable": total,
        "overdue_amount": _round(overdue["amount"].sum()),
        "at_risk_amount": _round(at_risk["amount"].sum()),
        "disputed_count": int(len(disputed)),
        "dso_days": dso,
        "dunning_priority": {k: _round(v) for k, v in dunning.items()},
        "invoice_count": int(len(inv)),
    }


# ── Cash Flow: 13-week forecast ───────────────────────────────────────────────
def build_cashflow_report(scenario: dict) -> dict:
    ds = scenario["dataset"]
    opening = float(ds["opening_cash"])
    weeks = pd.DataFrame(ds["weeks"])
    weeks = weeks.assign(net=weeks["inflow"] - weeks["outflow"])
    weeks = weeks.assign(cumulative=opening + weeks["net"].cumsum())

    min_cash = _round(weeks["cumulative"].min())
    negative_weeks = weeks[weeks["cumulative"] < 0]
    runway_weeks = int(negative_weeks["week"].iloc[0] - 1) if not negative_weeks.empty else int(len(weeks))

    return {
        "opening_cash": _round(opening),
        "total_inflow": _round(weeks["inflow"].sum()),
        "total_outflow": _round(weeks["outflow"].sum()),
        "ending_cash": _round(weeks["cumulative"].iloc[-1]),
        "min_cash": min_cash,
        "runway_weeks": runway_weeks,
        "cash_crunch": bool(min_cash < 0),
        "weeks_count": int(len(weeks)),
    }


# ── Reconciliation: bank vs ledger ────────────────────────────────────────────
def build_reconciliation_report(scenario: dict) -> dict:
    items = pd.DataFrame(scenario["dataset"]["items"])
    # A break = bank and ledger amounts disagree (missing side stored as null -> NaN != number).
    def _is_break(row):
        b, l = row.get("bank_amount"), row.get("ledger_amount")
        return not (pd.notna(b) and pd.notna(l) and float(b) == float(l))

    items = items.assign(is_break=items.apply(_is_break, axis=1))
    breaks = items[items["is_break"]]
    total = int(len(items))
    matched = total - int(len(breaks))
    by_type = breaks.groupby("type").size().to_dict() if not breaks.empty else {}
    break_amount = _round(
        breaks.apply(lambda r: abs(float(r.get("bank_amount") or 0) - float(r.get("ledger_amount") or 0)), axis=1).sum()
    ) if not breaks.empty else 0.0

    return {
        "total_items": total,
        "matched": matched,
        "break_count": int(len(breaks)),
        "match_rate_pct": _round(100 * matched / total if total else 100.0),
        "break_amount": break_amount,
        "breaks_by_type": {k: int(v) for k, v in by_type.items()},
    }


# ── Financial Insights: KPI / variance ────────────────────────────────────────
def build_insights_report(scenario: dict) -> dict:
    d = scenario["dataset"]
    rev, cogs, opex = float(d["revenue"]), float(d["cogs"]), float(d["opex"])
    prior_rev = float(d.get("prior_revenue", rev))
    budget_rev = float(d.get("budget_revenue", rev))
    gross = rev - cogs
    net = gross - opex

    return {
        "revenue": _round(rev),
        "gross_margin_pct": _round(100 * gross / rev if rev else 0),
        "net_margin_pct": _round(100 * net / rev if rev else 0),
        "opex_ratio_pct": _round(100 * opex / rev if rev else 0),
        "revenue_growth_pct": _round(100 * (rev - prior_rev) / prior_rev if prior_rev else 0),
        "budget_variance_pct": _round(100 * (rev - budget_rev) / budget_rev if budget_rev else 0),
    }


REPORT_BUILDERS = {
    "ap": build_ap_report,
    "ar": build_ar_report,
    "cashflow": build_cashflow_report,
    "reconciliation": build_reconciliation_report,
    "insights": build_insights_report,
}


def build_report(agent_key: str, scenario: dict) -> dict:
    """Dispatch to the agent's deterministic report builder."""
    builder = REPORT_BUILDERS.get(agent_key)
    if builder is None:
        raise ValueError(f"No report builder for agent '{agent_key}'")
    return builder(scenario)


def render_report(agent_key: str, report: dict) -> str:
    """Flatten a report dict into readable text for the LLM stages and Streamlit display."""
    lines = [f"{agent_key.upper()} REPORT"]
    for k, v in report.items():
        label = k.replace("_", " ").title()
        if isinstance(v, dict):
            inner = ", ".join(f"{ik}={iv}" for ik, iv in v.items()) or "none"
            lines.append(f"- {label}: {inner}")
        else:
            lines.append(f"- {label}: {v}")
    return "\n".join(lines)


def verify_report(agent_key: str, report: dict, scenario: dict) -> str:
    """
    Recompute the deterministic report and diff every scalar field against the passed
    report. VERIFIED when they match; DISCREPANCIES (with actual values) when tampered.
    Mirrors modules/finance/agent.py::_verify_data_summary as a generic ground-truth guard.
    """
    actual = build_report(agent_key, scenario)
    discrepancies = []
    for field, actual_val in actual.items():
        if isinstance(actual_val, dict):
            continue  # compare scalar fields only
        claimed_val = report.get(field)
        if claimed_val is None:
            discrepancies.append(f"  - {field}: missing from report (actual {actual_val})")
        elif str(claimed_val) != str(actual_val):
            discrepancies.append(f"  - {field}: claimed {claimed_val}, actual {actual_val} ← MISMATCH")

    if discrepancies:
        return (
            "GROUND TRUTH DISCREPANCIES — report values do not match a fresh recompute. "
            "Treat these as errors and use the actual values:\n" + "\n".join(discrepancies)
        )

    scalars = {k: v for k, v in actual.items() if not isinstance(v, dict)}
    summary = ", ".join(f"{k}={v}" for k, v in scalars.items())
    return f"GROUND TRUTH VERIFIED for {agent_key}: {summary}. All values match a fresh recompute."
