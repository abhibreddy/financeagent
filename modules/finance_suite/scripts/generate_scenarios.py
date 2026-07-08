"""
generate_scenarios.py — emit the 10-scenario mock fixtures for each report agent.

Deterministic (seeded per scenario) so reruns are byte-stable and tests can rely on them.
Writes modules/finance_suite/data/<agent>.json. Copilot has no fixtures.

Run: python3 -m modules.finance_suite.scripts.generate_scenarios
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data"
VENDORS = ["Acme Supply", "Globex", "Initech", "Umbrella Co", "Wayne Ind", "Stark LLC", "Soylent", "Hooli"]
CUSTOMERS = ["Northwind", "Contoso", "Fabrikam", "Adventure Works", "Tailspin", "Wingtip", "Proseware", "Litware"]


def _rng(agent, i):
    return random.Random(f"{agent}-{i}")


# ── AP ────────────────────────────────────────────────────────────────────────
AP_SCENARIOS = [
    ("overdue-vendor", "Overdue vendor", "Several bills well past due from one vendor."),
    ("early-pay-discount", "Early-pay discount", "Current bills offering 2% early-payment discounts."),
    ("duplicate-po", "Duplicate PO", "Two identical bills from the same vendor — possible double pay."),
    ("disputed-bill", "Disputed bill", "A large bill under dispute, payment on hold."),
    ("partial-payment", "Partial payment", "Bills partially paid, small balances remaining."),
    ("credit-memo", "Credit memo", "A vendor credit offsets outstanding bills."),
    ("fx-bill", "FX bill", "A foreign-currency bill converted to USD."),
    ("recurring-subscription", "Recurring subscription", "Steady monthly software subscriptions."),
    ("large-capex", "Large capex", "One very large capital-equipment bill."),
    ("vendor-on-hold", "Vendor on hold", "All bills from a vendor flagged on hold."),
]


def gen_ap():
    out = []
    for i, (sid, name, desc) in enumerate(AP_SCENARIOS):
        r = _rng("ap", i)
        bills = []
        n = r.randint(4, 7)
        for j in range(n):
            vendor = r.choice(VENDORS)
            amount = round(r.uniform(500, 8000), 2)
            due = r.choice([15, 30, -10, -45, -70, 5])
            disc = 2 if sid == "early-pay-discount" and j < 3 else 0
            if sid == "overdue-vendor":
                vendor, due = "Globex", r.choice([-20, -55, -80])
            if sid == "large-capex" and j == 0:
                amount = 125000.0
            bills.append({"vendor": vendor, "invoice_id": f"AP-{i}{j:02d}", "amount": amount,
                          "due_in_days": due, "discount_pct": disc})
        if sid == "duplicate-po":
            bills.append(dict(bills[0], invoice_id="AP-DUP"))
        out.append({"id": sid, "name": name, "description": desc, "dataset": {"bills": bills}})
    return out


# ── AR ────────────────────────────────────────────────────────────────────────
AR_SCENARIOS = [
    ("overdue-customer", "Overdue customer", "A customer with multiple badly overdue invoices."),
    ("dispute", "Dispute", "An invoice disputed by the customer."),
    ("early-pay-taken", "Early-pay taken", "Customer paid early to take a discount."),
    ("partial-payment", "Partial payment", "Invoices partly settled."),
    ("credit-downgrade", "Credit downgrade", "A customer's credit was downgraded; exposure at risk."),
    ("promise-to-pay", "Promise to pay", "Customer promised payment on overdue balances."),
    ("write-off-candidate", "Write-off candidate", "Very old invoices likely uncollectable."),
    ("new-customer", "New customer", "First invoices to a new account."),
    ("seasonal-spike", "Seasonal spike", "A surge of invoices from seasonal demand."),
    ("contra", "Contra account", "Customer is also a vendor — contra balance."),
]


def gen_ar():
    out = []
    for i, (sid, name, desc) in enumerate(AR_SCENARIOS):
        r = _rng("ar", i)
        inv = []
        n = r.randint(4, 7)
        for j in range(n):
            cust = r.choice(CUSTOMERS)
            amount = round(r.uniform(800, 12000), 2)
            due = r.choice([20, 10, -15, -50, -90, 30])
            disputed = (sid == "dispute" and j == 0)
            if sid == "overdue-customer":
                cust, due = "Contoso", r.choice([-30, -65, -95])
            if sid == "write-off-candidate":
                due = r.choice([-120, -150, -200])
            inv.append({"customer": cust, "invoice_id": f"AR-{i}{j:02d}", "amount": amount,
                        "due_in_days": due, "disputed": disputed})
        out.append({"id": sid, "name": name, "description": desc, "dataset": {"invoices": inv}})
    return out


# ── Cash Flow ───────────────────────────────────────────────────────────────
CF_SCENARIOS = [
    ("healthy-runway", "Healthy runway", "Steady inflows keep cash positive all quarter."),
    ("cash-crunch", "Cash crunch", "Outflows exceed inflows; cash goes negative."),
    ("receivable-delay", "Receivable delay", "A big receivable slips several weeks."),
    ("big-capex", "Big capex", "A large one-off capital outflow."),
    ("seasonal-dip", "Seasonal dip", "Inflows dip mid-quarter then recover."),
    ("loan-drawdown", "Loan drawdown", "A financing inflow boosts liquidity."),
    ("tax-payment", "Tax payment", "A quarterly tax outflow."),
    ("payroll-spike", "Payroll spike", "A bonus-driven payroll spike."),
    ("fx-swing", "FX swing", "Currency movement dents net inflows."),
    ("one-time-inflow", "One-time inflow", "A large one-off customer prepayment."),
]


def gen_cf():
    out = []
    for i, (sid, name, desc) in enumerate(CF_SCENARIOS):
        r = _rng("cf", i)
        opening = round(r.uniform(80000, 200000), 2)
        base_in = r.uniform(30000, 60000)
        base_out = r.uniform(30000, 55000)
        weeks = []
        for w in range(1, 14):
            inflow = round(base_in * r.uniform(0.8, 1.2), 2)
            outflow = round(base_out * r.uniform(0.8, 1.2), 2)
            if sid == "cash-crunch":
                outflow = round(base_out * 1.6, 2)
            if sid == "big-capex" and w == 6:
                outflow += 150000
            if sid == "loan-drawdown" and w == 3:
                inflow += 200000
            if sid == "tax-payment" and w == 9:
                outflow += 90000
            if sid == "payroll-spike" and w == 7:
                outflow += 70000
            if sid == "receivable-delay" and w in (2, 3):
                inflow = round(base_in * 0.3, 2)
            if sid == "one-time-inflow" and w == 4:
                inflow += 180000
            weeks.append({"week": w, "inflow": inflow, "outflow": outflow})
        out.append({"id": sid, "name": name, "description": desc,
                    "dataset": {"opening_cash": opening, "weeks": weeks}})
    return out


# ── Reconciliation ────────────────────────────────────────────────────────────
RC_SCENARIOS = [
    ("clean", "Clean", "Bank and ledger fully agree."),
    ("timing-diff", "Timing difference", "An entry booked in different periods."),
    ("missing-bank", "Missing bank txn", "A ledger entry with no matching bank line."),
    ("missing-ledger", "Missing ledger entry", "A bank line not yet booked to the ledger."),
    ("amount-mismatch", "Amount mismatch", "Same item, different amounts."),
    ("duplicate", "Duplicate", "A transaction recorded twice."),
    ("fx-rounding", "FX rounding", "Small currency-rounding differences."),
    ("unbooked-fee", "Unbooked fee", "A bank fee not in the ledger."),
    ("transposed-digits", "Transposed digits", "A keying error (e.g. 1290 vs 1920)."),
    ("unidentified-deposit", "Unidentified deposit", "A bank deposit with no ledger source."),
]


def gen_rc():
    out = []
    for i, (sid, name, desc) in enumerate(RC_SCENARIOS):
        r = _rng("rc", i)
        items = []
        for j in range(6):
            amt = round(r.uniform(100, 5000), 2)
            items.append({"ref": f"RC-{i}{j:02d}", "bank_amount": amt, "ledger_amount": amt, "type": "matched"})
        if sid == "timing-diff":
            items[1].update(type="timing", ledger_amount=None)
        elif sid == "missing-bank":
            items[1].update(type="missing_bank", bank_amount=None)
        elif sid == "missing-ledger":
            items[1].update(type="missing_ledger", ledger_amount=None)
        elif sid == "amount-mismatch":
            items[1].update(type="amount_mismatch", ledger_amount=round(items[1]["bank_amount"] + 250, 2))
        elif sid == "duplicate":
            items.append(dict(items[0], ref="RC-DUP", type="duplicate"))
            items[-1]["ledger_amount"] = None
        elif sid == "fx-rounding":
            items[1].update(type="fx_rounding", ledger_amount=round(items[1]["bank_amount"] + 0.03, 2))
        elif sid == "unbooked-fee":
            items[1].update(type="unbooked_fee", ledger_amount=None, bank_amount=35.0)
        elif sid == "transposed-digits":
            items[1].update(type="transposed", ledger_amount=1920.0, bank_amount=1290.0)
        elif sid == "unidentified-deposit":
            items[1].update(type="unidentified_deposit", ledger_amount=None)
        out.append({"id": sid, "name": name, "description": desc, "dataset": {"items": items}})
    return out


# ── Financial Insights ────────────────────────────────────────────────────────
IN_SCENARIOS = [
    ("margin-compression", "Margin compression", "Rising COGS squeezes gross margin.", dict(revenue=1_000_000, cogs=720_000, opex=200_000, prior_revenue=980_000, budget_revenue=1_020_000)),
    ("revenue-growth", "Revenue growth", "Strong top-line growth vs prior period.", dict(revenue=1_300_000, cogs=650_000, opex=300_000, prior_revenue=1_000_000, budget_revenue=1_150_000)),
    ("expense-spike", "Expense spike", "Opex jumps on one-off costs.", dict(revenue=1_000_000, cogs=550_000, opex=380_000, prior_revenue=1_010_000, budget_revenue=1_000_000)),
    ("budget-variance", "Budget variance", "Revenue lands well under budget.", dict(revenue=850_000, cogs=500_000, opex=250_000, prior_revenue=880_000, budget_revenue=1_050_000)),
    ("opex-ratio", "Opex ratio", "Opex as a share of revenue creeps up.", dict(revenue=1_100_000, cogs=600_000, opex=350_000, prior_revenue=1_090_000, budget_revenue=1_100_000)),
    ("gross-margin-trend", "Gross-margin trend", "Gross margin improves period over period.", dict(revenue=1_200_000, cogs=600_000, opex=300_000, prior_revenue=1_150_000, budget_revenue=1_180_000)),
    ("cash-conversion", "Cash-conversion cycle", "Working-capital efficiency snapshot.", dict(revenue=1_050_000, cogs=580_000, opex=260_000, prior_revenue=1_040_000, budget_revenue=1_050_000)),
    ("dso-dpo", "DSO/DPO", "Receivable and payable days balance.", dict(revenue=990_000, cogs=560_000, opex=250_000, prior_revenue=1_000_000, budget_revenue=1_000_000)),
    ("working-capital", "Working capital", "Working-capital position review.", dict(revenue=1_020_000, cogs=590_000, opex=240_000, prior_revenue=1_005_000, budget_revenue=1_010_000)),
    ("cohort-churn", "Cohort churn", "Churn drags revenue below prior period.", dict(revenue=920_000, cogs=520_000, opex=250_000, prior_revenue=1_010_000, budget_revenue=980_000)),
]


def gen_in():
    return [{"id": sid, "name": name, "description": desc, "dataset": ds}
            for (sid, name, desc, ds) in IN_SCENARIOS]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"ap": gen_ap(), "ar": gen_ar(), "cashflow": gen_cf(),
             "reconciliation": gen_rc(), "insights": gen_in()}
    for agent, scenarios in files.items():
        assert len(scenarios) == 10, f"{agent} must have 10 scenarios, has {len(scenarios)}"
        path = OUT / f"{agent}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(scenarios, fh, indent=2)
        print(f"wrote {path} ({len(scenarios)} scenarios)")


if __name__ == "__main__":
    main()
