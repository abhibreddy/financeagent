# FraudGuard v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade FraudGuard from a single-agent dark-theme Streamlit app to a multi-agent fraud detection platform with invoice fraud detection, multi-account comparison, a modern light-theme UI, and a 3-stage agent pipeline that eliminates hallucinations.

**Architecture:** Four phases ship independently: (1) CSS/UI overhaul to light theme with sidebar nav matching the reference design; (2) multi-account side-by-side comparison view; (3) invoice fraud detection with synthetic data and a dedicated multi-agent pipeline; (4) refactor velocity fraud agent into DataAgent → AuditAgent → SynthesisAgent chain.

**Tech Stack:** Streamlit, LangGraph, langchain-ollama (qwen2.5), Langfuse v2, Pandas, Plotly, SQLite, Python 3.11+

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `css/style.css` | Rewrite | Light theme — all card, badge, layout, chart styles |
| `account_lookup.py` | Modify | Add multi-account comparison tab |
| `pages/alert_queue.py` | Modify | Update to use new light-theme CSS classes |
| `pages/2_Agent_Chat.py` | Modify | Connect to multi-agent pipeline, render Plotly charts |
| `utils.py` | Modify | Add `load_invoices()`, invoice risk helpers |
| `agent.py` | Rewrite | Replace single agent with DataAgent → AuditAgent → SynthesisAgent |
| `invoice_agent.py` | Create | Invoice fraud 3-stage multi-agent system |
| `pages/3_Invoice_Fraud.py` | Create | Invoice fraud detection Streamlit page |
| `synthetictables/invoices.csv` | Create | Synthetic invoice data with embedded fraud patterns |
| `tests/test_utils.py` | Create | Unit tests for velocity + invoice utils |
| `tests/test_invoice_agent.py` | Create | Unit tests for invoice fraud detection tools |

---

## Phase 1: UI Overhaul

### Task 1: Rewrite CSS for light theme

**Files:**
- Modify: `css/style.css`

Reference design characteristics:
- White background (`#ffffff`) with off-white app background (`#f7f7f5`)
- Cards: white bg, 1px `#e8e8e8` border, subtle `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`
- Typography: system-ui / Inter stack, dark `#1a1a1a` text, muted `#6b7280` labels
- Colored badge pills: blue `#dbeafe`/`#1d4ed8`, yellow `#fef3c7`/`#d97706`, green `#dcfce7`/`#16a34a`, purple `#ede9fe`/`#7c3aed`
- Sidebar: white bg, `#f3f4f6` active item highlight
- Metric values: large bold `32px`, colored for status

- [ ] **Step 1: Replace `css/style.css` entirely**

```css
/* ── Reset & base ─────────────────────────────────────────────────────────── */
* { box-sizing: border-box; }

[data-testid="stAppViewContainer"] {
    background: #f7f7f5 !important;
}
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e8e8e8 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #374151;
    font-size: 13px;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}
.stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
}
h1, h2, h3 { color: #111827; }

/* ── Header ───────────────────────────────────────────────────────────────── */
.fd-header {
    display: flex; align-items: center; gap: 14px;
    padding: 20px 0 16px;
    border-bottom: 1px solid #e8e8e8;
    margin-bottom: 20px;
}
.fd-icon { font-size: 28px; }
.fd-title { font-size: 20px; font-weight: 700; color: #111827; }
.fd-sub   { font-size: 12px; color: #6b7280; margin-top: 2px; }

/* ── Section label ────────────────────────────────────────────────────────── */
.sec-label {
    font-size: 11px; font-weight: 600; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.07em;
    margin: 20px 0 10px;
}

/* ── Metric cards ─────────────────────────────────────────────────────────── */
.metric-row {
    display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;
}
.metric-box {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 10px;
    padding: 16px 20px;
    flex: 1; min-width: 120px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.metric-box .label {
    font-size: 11px; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.metric-box .value {
    font-size: 28px; font-weight: 700; color: #111827;
}
.metric-box .value.red    { color: #dc2626; }
.metric-box .value.green  { color: #16a34a; }
.metric-box .value.yellow { color: #d97706; }

/* ── Badges ───────────────────────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 2px 8px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
}
.b-block { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }
.b-flag  { background: #fef3c7; color: #d97706; border: 1px solid #fcd34d; }
.b-ok    { background: #dcfce7; color: #16a34a; border: 1px solid #86efac; }
.b-info  { background: #ede9fe; color: #7c3aed; border: 1px solid #c4b5fd; }
.b-blue  { background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd; }

/* ── Account info card ────────────────────────────────────────────────────── */
.acc-info {
    background: #ffffff; border: 1px solid #e8e8e8;
    border-radius: 10px; padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.acc-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 0; border-bottom: 1px solid #f3f4f6;
}
.acc-row:last-child { border-bottom: none; }
.acc-key { font-size: 12px; color: #6b7280; }
.acc-val { font-size: 13px; color: #111827; font-weight: 500; }

/* ── Verdict card ─────────────────────────────────────────────────────────── */
.verdict-card {
    border-radius: 10px; padding: 18px 20px; margin: 16px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.verdict-high   { background: #fff1f2; border: 1px solid #fca5a5; }
.verdict-medium { background: #fffbeb; border: 1px solid #fcd34d; }
.verdict-low    { background: #f0fdf4; border: 1px solid #86efac; }
.verdict-label  { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7280; margin-bottom: 6px; }
.verdict-main   { font-size: 18px; font-weight: 700; color: #111827; margin-bottom: 6px; }
.verdict-detail { font-size: 13px; color: #374151; line-height: 1.6; }

/* ── Agent signal alerts ──────────────────────────────────────────────────── */
.agent-alert {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 12px 16px; border-radius: 8px; font-size: 13px;
    line-height: 1.6; margin-bottom: 8px;
}
.agent-alert.danger  { background: #fff1f2; border: 1px solid #fca5a5; color: #374151; }
.agent-alert.warning { background: #fffbeb; border: 1px solid #fcd34d; color: #374151; }

/* ── Transaction timeline ─────────────────────────────────────────────────── */
.tl-wrap { display: flex; flex-direction: column; gap: 0; }
.tl-row {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 12px; font-size: 12px; color: #374151;
    border-bottom: 1px solid #f3f4f6;
    background: #ffffff;
}
.tl-row:first-child { border-radius: 8px 8px 0 0; border: 1px solid #e8e8e8; }
.tl-row:last-child  { border-radius: 0 0 8px 8px; border: 1px solid #e8e8e8; border-top: none; }
.tl-row:not(:first-child):not(:last-child) { border-left: 1px solid #e8e8e8; border-right: 1px solid #e8e8e8; }
.tl-time { color: #6b7280; min-width: 90px; font-family: monospace; }
.tl-amt  { font-weight: 600; color: #111827; min-width: 80px; }
.tl-type { color: #374151; min-width: 100px; }
.tl-city { color: #6b7280; flex: 1; }

/* ── Agent status chips (sidebar) ─────────────────────────────────────────── */
.agent-status-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 8px; border-radius: 6px; margin-bottom: 4px;
    font-size: 12px; color: #374151;
}
.agent-status-row:hover { background: #f3f4f6; }
.agent-dot {
    width: 7px; height: 7px; border-radius: 50%;
    flex-shrink: 0;
}
.agent-dot.online  { background: #16a34a; }
.agent-dot.busy    { background: #d97706; }
.agent-dot.offline { background: #9ca3af; }

/* ── Invoice fraud cards ──────────────────────────────────────────────────── */
.invoice-card {
    background: #ffffff; border: 1px solid #e8e8e8;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.invoice-card.flagged { border-color: #fca5a5; background: #fff8f8; }
.invoice-card.duplicate { border-color: #fcd34d; background: #fffdf0; }

/* ── Chat bubbles ─────────────────────────────────────────────────────────── */
.chat-bubble {
    padding: 12px 16px; border-radius: 10px; font-size: 13px;
    line-height: 1.7; margin-bottom: 8px; max-width: 88%;
}
.chat-user {
    background: #eff6ff; border: 1px solid #bfdbfe;
    color: #1e40af; margin-left: auto; text-align: right;
}
.chat-agent {
    background: #ffffff; border: 1px solid #e8e8e8; color: #111827;
}
.chat-label {
    font-size: 10px; color: #6b7280; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 4px;
}
.chat-label-right { text-align: right; }
.tool-chip {
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 10px; font-weight: 600; margin: 2px;
    background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
}
.langfuse-link {
    font-size: 11px; color: #6b7280; text-align: right; padding: 4px 0 12px;
}
.langfuse-link a { color: #2563eb; text-decoration: none; }
.langfuse-link a:hover { text-decoration: underline; }
.suggestion-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 1rem; }
.empty-state {
    text-align: center; padding: 3rem 1rem; color: #6b7280; font-size: 13px;
}
.empty-state .icon { font-size: 40px; margin-bottom: 12px; }

/* ── Multi-agent step indicator ───────────────────────────────────────────── */
.agent-pipeline {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 14px; background: #f9fafb; border: 1px solid #e8e8e8;
    border-radius: 8px; margin-bottom: 10px; font-size: 12px;
}
.pipeline-step {
    padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600;
}
.pipeline-step.data     { background: #dbeafe; color: #1d4ed8; }
.pipeline-step.audit    { background: #fef3c7; color: #d97706; }
.pipeline-step.synth    { background: #dcfce7; color: #16a34a; }
.pipeline-step.active   { animation: pulse 1.5s infinite; }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.6; }
}
.pipeline-arrow { color: #9ca3af; font-size: 14px; }

/* ── Comparison grid (multi-account) ──────────────────────────────────────── */
.compare-header {
    font-size: 13px; font-weight: 600; color: #111827;
    padding: 8px 0 4px; border-bottom: 2px solid #e8e8e8; margin-bottom: 10px;
}
```

- [ ] **Step 2: Verify CSS loads without error**

```bash
cd "/Users/nirvahnthakur/Library/Mobile Documents/com~apple~CloudDocs/Work RT/financeagent"
python3 -c "
with open('css/style.css') as f:
    content = f.read()
assert 'fd-header' in content
assert 'metric-box' in content
assert 'invoice-card' in content
assert 'agent-pipeline' in content
print('CSS OK — classes verified')
"
```

Expected: `CSS OK — classes verified`

- [ ] **Step 3: Update Streamlit config for light theme**

Create `.streamlit/config.toml`:
```toml
[theme]
base = "light"
backgroundColor = "#f7f7f5"
secondaryBackgroundColor = "#ffffff"
textColor = "#111827"
font = "sans serif"
```

- [ ] **Step 4: Commit**

```bash
git add css/style.css .streamlit/config.toml
git commit -m "feat: light theme CSS overhaul matching reference dashboard design"
```

---

### Task 2: Update existing pages to use light-theme classes

**Files:**
- Modify: `account_lookup.py` lines 6-14 (page config + header)
- Modify: `pages/alert_queue.py` lines 8-15 (page config)
- Modify: `pages/2_Agent_Chat.py` lines 14-58 (remove inline dark CSS, update header)

- [ ] **Step 1: Update `account_lookup.py` page config**

Replace the `st.set_page_config` and header block (lines 6-38):
```python
st.set_page_config(
    page_title="FraudGuard — Account Lookup",
    page_icon="🛡️",
    layout="wide",   # change centered → wide
)
```

And update the header HTML to use new light classes (no changes needed — `.fd-header` CSS now covers it).

- [ ] **Step 2: Add sidebar agent status panel to `account_lookup.py`**

Add this block after the CSS load (line 14):
```python
with st.sidebar:
    st.markdown("### 🛡️ FraudGuard")
    st.caption("Fraud Detection Platform")
    st.divider()
    st.markdown("**Agents**")
    agents = [
        ("🔍", "Velocity Agent",  "online"),
        ("🧾", "Invoice Agent",   "online"),
        ("🔎", "Audit Agent",     "online"),
        ("📊", "Synthesis Agent", "online"),
    ]
    for icon, name, status in agents:
        dot_class = f"agent-dot {status}"
        st.markdown(
            f"<div class='agent-status-row'>{icon} {name}"
            f"<span style='flex:1'></span>"
            f"<span class='agent-dot {dot_class}'></span></div>",
            unsafe_allow_html=True
        )
    st.divider()
    st.page_link("account_lookup.py",       label="🔍 Account Lookup",  )
    st.page_link("pages/alert_queue.py",    label="🚨 Alert Queue",     )
    st.page_link("pages/2_Agent_Chat.py",   label="🤖 Agent Chat",      )
```

- [ ] **Step 3: Remove inline dark CSS from `pages/2_Agent_Chat.py`**

Delete lines 24-58 (the `<style>` block with `.chat-bubble`, `.chat-user` etc.) — these are now in `style.css`.

- [ ] **Step 4: Commit**

```bash
git add account_lookup.py pages/alert_queue.py pages/2_Agent_Chat.py
git commit -m "feat: apply light theme to all pages, add sidebar agent status"
```

---

## Phase 2: Multi-Account Comparison

### Task 3: Write tests for multi-account comparison utilities

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Create test file**

```python
# tests/test_utils.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest
from utils import compute_velocity, compare_accounts

# ── Fixtures ──────────────────────────────────────────────────────────────────
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

# ── compute_velocity ──────────────────────────────────────────────────────────
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
    txns = _make_txns("ACC-002", ["2024-01-01 10:00", "2024-01-01 10:01", "2024-01-01 10:02"],
                      geo_flags=[True, True, True])
    result = compute_velocity(txns)
    assert result["geo_flags"] == 3
    assert result["risk_level"] == "High"

# ── compare_accounts ──────────────────────────────────────────────────────────
def test_compare_accounts_returns_list():
    from utils import load_data
    txns, accounts = load_data()
    # pick first two account IDs
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
    assert result == [] or result[0].get("error") is not None
```

- [ ] **Step 2: Run tests — expect failures on `compare_accounts`**

```bash
cd "/Users/nirvahnthakur/Library/Mobile Documents/com~apple~CloudDocs/Work RT/financeagent"
python3 -m pytest tests/test_utils.py -v 2>&1 | head -40
```

Expected: `compare_accounts` import fails, velocity tests pass.

- [ ] **Step 3: Add `compare_accounts` to `utils.py`**

Append to `utils.py`:
```python
def compare_accounts(account_ids: list[str], txns: pd.DataFrame, accounts: pd.DataFrame) -> list[dict]:
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
```

- [ ] **Step 4: Run tests — all should pass**

```bash
python3 -m pytest tests/test_utils.py -v
```

Expected: All green.

- [ ] **Step 5: Commit**

```bash
git add utils.py tests/__init__.py tests/test_utils.py
git commit -m "feat: add compare_accounts utility + tests"
```

---

### Task 4: Multi-account comparison UI

**Files:**
- Modify: `account_lookup.py` — add "Compare Accounts" tab

- [ ] **Step 1: Add tab layout to `account_lookup.py`**

Replace the search section (everything from `# ── Search ──` to end of file) with:
```python
tab1, tab2 = st.tabs(["🔍 Single Account", "⚖️ Compare Accounts"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SINGLE ACCOUNT (existing code, paste unchanged below here)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        query = st.text_input("Account ID", placeholder="e.g. ACC-00042", label_visibility="collapsed")
    with col_btn:
        st.button("Look Up", type="primary", use_container_width=True)

    st.caption(f"🔴 {len(flagged_ids)} flagged accounts detected — try one:")
    picked = st.selectbox("Quick pick", ["—"] + flagged_ids, label_visibility="collapsed")
    if picked != "—":
        query = picked

    # ... (all existing lookup/display code goes here unchanged) ...

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARE ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-label">Select 2–4 accounts to compare</div>', unsafe_allow_html=True)
    all_ids = sorted(txns["account_id"].unique().tolist())
    selected_ids = st.multiselect(
        "Accounts",
        options=all_ids,
        default=flagged_ids[:3] if len(flagged_ids) >= 3 else flagged_ids,
        max_selections=4,
        label_visibility="collapsed",
    )

    if len(selected_ids) < 2:
        st.info("Select at least 2 accounts to compare.")
        st.stop()

    from utils import compare_accounts
    comparisons = compare_accounts(selected_ids, txns, accounts)

    if not comparisons:
        st.warning("No data found for selected accounts.")
        st.stop()

    # ── Side-by-side metric cards ─────────────────────────────────────────────
    st.markdown('<div class="sec-label">Risk Summary</div>', unsafe_allow_html=True)
    cols = st.columns(len(comparisons))
    for i, c in enumerate(comparisons):
        with cols[i]:
            risk_color = "red" if c["risk_level"] == "High" else ("yellow" if c["risk_level"] == "Medium" else "green")
            risk_icon  = "🔴" if c["risk_level"] == "High" else ("🟡" if c["risk_level"] == "Medium" else "🟢")
            st.markdown(f"""
            <div class="acc-info">
              <div class="compare-header">{risk_icon} {c['account_id']}</div>
              <div class="acc-row"><span class="acc-key">Customer</span><span class="acc-val">{c['customer']}</span></div>
              <div class="acc-row"><span class="acc-key">Risk score</span>
                <span class="acc-val" style="color:{'#dc2626' if risk_color=='red' else '#d97706' if risk_color=='yellow' else '#16a34a'};font-weight:700;font-size:18px">{c['risk_score']}</span></div>
              <div class="acc-row"><span class="acc-key">Max velocity</span><span class="acc-val">{c['max_velocity']} txns/5min</span></div>
              <div class="acc-row"><span class="acc-key">Geo flags</span><span class="acc-val">{c['geo_flags']}</span></div>
              <div class="acc-row"><span class="acc-key">Total amount</span><span class="acc-val">${c['total_amount']:,.2f}</span></div>
              <div class="acc-row"><span class="acc-key">KYC</span><span class="acc-val">{'✅' if c['kyc_verified'] else '❌ Unverified'}</span></div>
              <div class="acc-row"><span class="acc-key">Dormant</span><span class="acc-val">{'⚠️ Yes' if c['is_dormant'] else 'No'}</span></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Comparative velocity bar chart (Plotly) ───────────────────────────────
    st.markdown('<div class="sec-label">Velocity Comparison</div>', unsafe_allow_html=True)
    import plotly.graph_objects as go
    bar_colors = ["#dc2626" if c["risk_level"] == "High" else "#d97706" if c["risk_level"] == "Medium" else "#16a34a" for c in comparisons]
    fig = go.Figure(data=[
        go.Bar(
            x=[c["account_id"] for c in comparisons],
            y=[c["max_velocity"] for c in comparisons],
            marker_color=bar_colors,
            text=[f'{c["max_velocity"]} txns' for c in comparisons],
            textposition="outside",
        )
    ])
    fig.add_hline(y=5, line_dash="dash", line_color="#6b7280",
                  annotation_text="Threshold (5)", annotation_position="right")
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#374151"),
        yaxis=dict(title="Max txns / 5 min", gridcolor="#f3f4f6"),
        xaxis=dict(gridcolor="#f3f4f6"),
        height=300, margin=dict(t=20, b=20),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Risk score comparison bar chart ───────────────────────────────────────
    st.markdown('<div class="sec-label">Risk Score Comparison</div>', unsafe_allow_html=True)
    fig2 = go.Figure(data=[
        go.Bar(
            x=[c["account_id"] for c in comparisons],
            y=[c["risk_score"] for c in comparisons],
            marker_color=bar_colors,
            text=[str(c["risk_score"]) for c in comparisons],
            textposition="outside",
        )
    ])
    fig2.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", color="#374151"),
        yaxis=dict(title="Risk Score (0–100)", range=[0, 110], gridcolor="#f3f4f6"),
        height=280, margin=dict(t=20, b=20),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)
```

- [ ] **Step 2: Verify plotly is installed**

```bash
python3 -c "import plotly; print('plotly', plotly.__version__)"
```

If missing: `pip install plotly`

- [ ] **Step 3: Commit**

```bash
git add account_lookup.py
git commit -m "feat: multi-account comparison tab with side-by-side metrics and Plotly charts"
```

---

## Phase 3: Invoice Fraud Agent

### Task 5: Generate synthetic invoice data

**Files:**
- Create: `synthetictables/invoices.csv`
- Create: `scripts/generate_invoices.py`

- [ ] **Step 1: Create invoice generator script**

```python
# scripts/generate_invoices.py
"""
Generates synthetic invoice data with embedded fraud patterns:
- Exact duplicates (same vendor + amount + date)
- Near-duplicates (same amount, slightly different date)
- Split billing (many small invoices from one vendor in a week)
- Round-number clustering (amounts just below $10k approval threshold)
- Ghost vendors (vendor appears only in flagged invoices)
"""
import pandas as pd
import random

random.seed(42)

VENDORS = [
    "Apex Office Supplies", "Metro Consulting LLC", "CloudHost Pro",
    "DataSec Partners", "TechFix Services", "GreenLeaf Catering",
    "Premier Logistics", "Sigma Analytics", "BlueStar Events",
]

GHOST_VENDOR = "Phantom Solutions LLC"  # fraud-only vendor
CATEGORIES   = ["IT Services", "Office Supplies", "Consulting", "Logistics", "Catering", "Software"]
DEPARTMENTS  = ["Finance", "Operations", "IT", "HR", "Marketing"]

rows = []
invoice_num = 1000

def make_invoice(vendor, amount, date, dept, category, is_dup=False, is_split=False,
                 is_ghost=False, is_threshold=False, fraud_type=None):
    global invoice_num
    row = {
        "invoice_id":    f"INV-{invoice_num:05d}",
        "vendor":        vendor,
        "amount":        round(amount, 2),
        "date":          date,
        "department":    dept,
        "category":      category,
        "approver":      random.choice(["J.Smith", "A.Patel", "M.Chen", "R.Kumar"]),
        "is_duplicate":  is_dup,
        "is_split":      is_split,
        "is_ghost":      is_ghost,
        "is_threshold":  is_threshold,
        "fraud_type":    fraud_type or "",
    }
    invoice_num += 1
    return row

# ── Normal invoices ──────────────────────────────────────────────────────────
dates = pd.date_range("2024-01-01", periods=90).strftime("%Y-%m-%d").tolist()
for _ in range(80):
    rows.append(make_invoice(
        vendor=random.choice(VENDORS),
        amount=round(random.uniform(200, 8000), 2),
        date=random.choice(dates),
        dept=random.choice(DEPARTMENTS),
        category=random.choice(CATEGORIES),
    ))

# ── Fraud Pattern 1: Exact duplicates ────────────────────────────────────────
dup_invoice = make_invoice("Metro Consulting LLC", 4750.00, "2024-02-14",
                           "Finance", "Consulting")
rows.append(dup_invoice)
dup_copy = dup_invoice.copy()
dup_copy["invoice_id"] = f"INV-{invoice_num:05d}"
dup_copy["is_duplicate"] = True
dup_copy["fraud_type"] = "exact_duplicate"
invoice_num += 1
rows.append(dup_copy)

# ── Fraud Pattern 2: Near-duplicate (1-day date drift) ───────────────────────
rows.append(make_invoice("Apex Office Supplies", 3200.00, "2024-03-05",
                         "Operations", "Office Supplies"))
rows.append(make_invoice("Apex Office Supplies", 3200.00, "2024-03-06",
                         "Operations", "Office Supplies",
                         is_dup=True, fraud_type="near_duplicate"))

# ── Fraud Pattern 3: Split billing (8 × ~$1200 in one week) ──────────────────
for i in range(8):
    d = pd.Timestamp("2024-04-01") + pd.Timedelta(days=i % 5)
    rows.append(make_invoice("Sigma Analytics", round(random.uniform(1100, 1300), 2),
                             d.strftime("%Y-%m-%d"), "IT", "IT Services",
                             is_split=True, fraud_type="split_billing"))

# ── Fraud Pattern 4: Just-below-threshold invoices ───────────────────────────
for _ in range(5):
    rows.append(make_invoice(
        vendor=random.choice(VENDORS),
        amount=round(random.uniform(9700, 9999), 2),
        date=random.choice(dates[:30]),
        dept="Finance", category="Consulting",
        is_threshold=True, fraud_type="threshold_avoidance",
    ))

# ── Fraud Pattern 5: Ghost vendor ────────────────────────────────────────────
for _ in range(4):
    rows.append(make_invoice(
        vendor=GHOST_VENDOR,
        amount=round(random.uniform(5000, 15000), 2),
        date=random.choice(dates[60:]),
        dept="Operations", category="Consulting",
        is_ghost=True, fraud_type="ghost_vendor",
    ))

df = pd.DataFrame(rows)
df.to_csv("synthetictables/invoices.csv", index=False)
print(f"Generated {len(df)} invoices ({df['fraud_type'].ne('').sum()} flagged)")
```

- [ ] **Step 2: Run the generator**

```bash
cd "/Users/nirvahnthakur/Library/Mobile Documents/com~apple~CloudDocs/Work RT/financeagent"
mkdir -p scripts
python3 scripts/generate_invoices.py
```

Expected: `Generated N invoices (X flagged)`

- [ ] **Step 3: Verify CSV**

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('synthetictables/invoices.csv')
print(df.shape)
print(df['fraud_type'].value_counts())
print(df.dtypes)
"
```

Expected: Columns `invoice_id, vendor, amount, date, department, category, approver, is_duplicate, is_split, is_ghost, is_threshold, fraud_type`

- [ ] **Step 4: Commit**

```bash
git add synthetictables/invoices.csv scripts/generate_invoices.py
git commit -m "feat: synthetic invoice dataset with 5 embedded fraud patterns"
```

---

### Task 6: Invoice fraud detection utilities + tests

**Files:**
- Modify: `utils.py` — add invoice detection functions
- Modify: `tests/test_utils.py` — add invoice tests

- [ ] **Step 1: Add invoice detection functions to `utils.py`**

Append to `utils.py`:
```python
# ── Invoice fraud detection ────────────────────────────────────────────────────
APPROVAL_THRESHOLD = 10_000.0  # invoices ≥ this require extra approval
THRESHOLD_BAND     = 500.0     # flag invoices within this amount below threshold
SPLIT_WINDOW_DAYS  = 7
SPLIT_MIN_COUNT    = 4


def load_invoices() -> pd.DataFrame:
    df = pd.read_csv("synthetictables/invoices.csv", parse_dates=["date"])
    return df


def detect_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return rows that share the same vendor + amount + date as another row.
    Both the original and the duplicate are returned.
    """
    key = ["vendor", "amount", "date"]
    counts = df.groupby(key)["invoice_id"].transform("count")
    return df[counts > 1].copy()


def detect_near_duplicates(df: pd.DataFrame, amount_tolerance: float = 0.01,
                            day_window: int = 3) -> pd.DataFrame:
    """
    Return rows where the same vendor billed a very similar amount within `day_window` days.
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
                    # Skip if exact duplicate (same date + amount)
                    if ri["date"] != rj["date"] or ri["amount"] != rj["amount"]:
                        flagged_indices.update([idxs[i], idxs[j]])
    return df.loc[list(flagged_indices)].copy()


def detect_split_billing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return rows where a vendor submits SPLIT_MIN_COUNT+ invoices
    within SPLIT_WINDOW_DAYS days, suggesting invoice splitting to avoid
    approval thresholds.
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


def detect_ghost_vendors(df: pd.DataFrame, known_vendors: list[str] | None = None) -> pd.DataFrame:
    """
    Return invoices from vendors who appear in fewer than 3 invoices total.
    These low-frequency vendors may be fictitious (ghost vendors).
    If known_vendors list is provided, exclude vendors on that whitelist.
    """
    freq = df["vendor"].value_counts()
    rare = freq[freq < 3].index.tolist()
    if known_vendors:
        rare = [v for v in rare if v not in known_vendors]
    return df[df["vendor"].isin(rare)].copy()


def build_invoice_risk_report(df: pd.DataFrame) -> dict:
    """
    Run all detection passes and return a consolidated risk report dict.
    """
    exact_dups  = detect_exact_duplicates(df)
    near_dups   = detect_near_duplicates(df)
    splits      = detect_split_billing(df)
    threshold   = detect_threshold_avoidance(df)
    ghosts      = detect_ghost_vendors(df)

    all_flagged = pd.concat([exact_dups, near_dups, splits, threshold, ghosts]).drop_duplicates("invoice_id")

    return {
        "total_invoices":    len(df),
        "flagged_count":     len(all_flagged),
        "exact_duplicates":  exact_dups.to_dict("records"),
        "near_duplicates":   near_dups.to_dict("records"),
        "split_billing":     splits.to_dict("records"),
        "threshold_avoidance": threshold.to_dict("records"),
        "ghost_vendors":     ghosts.to_dict("records"),
        "total_flagged_amount": float(all_flagged["amount"].sum()),
    }
```

- [ ] **Step 2: Add invoice tests to `tests/test_utils.py`**

Append:
```python
# ── Invoice fraud detection ────────────────────────────────────────────────────
from utils import (
    detect_exact_duplicates, detect_near_duplicates, detect_split_billing,
    detect_threshold_avoidance, detect_ghost_vendors, build_invoice_risk_report,
)

def _make_invoices(rows):
    return pd.DataFrame(rows, columns=["invoice_id", "vendor", "amount", "date"])

def test_detect_exact_duplicates():
    df = pd.DataFrame([
        {"invoice_id": "INV-001", "vendor": "ACME", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-002", "vendor": "ACME", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")},
        {"invoice_id": "INV-003", "vendor": "ACME", "amount": 2000.0, "date": pd.Timestamp("2024-01-01")},
    ])
    result = detect_exact_duplicates(df)
    assert len(result) == 2
    assert set(result["invoice_id"]) == {"INV-001", "INV-002"}

def test_detect_exact_duplicates_none():
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
    df = pd.DataFrame([
        {"invoice_id": f"INV-{i:03d}", "vendor": "BigCo", "amount": 1000.0, "date": pd.Timestamp("2024-01-01")}
        for i in range(5)
    ] + [
        {"invoice_id": "INV-099", "vendor": "Ghost LLC", "amount": 5000.0, "date": pd.Timestamp("2024-01-01")},
    ])
    result = detect_ghost_vendors(df)
    assert len(result) == 1
    assert result.iloc[0]["vendor"] == "Ghost LLC"

def test_build_invoice_risk_report_structure():
    df = pd.read_csv("synthetictables/invoices.csv", parse_dates=["date"])
    report = build_invoice_risk_report(df)
    assert "total_invoices" in report
    assert "flagged_count" in report
    assert report["flagged_count"] > 0  # synthetic data has known fraud
    assert isinstance(report["exact_duplicates"], list)
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest tests/test_utils.py -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add utils.py tests/test_utils.py
git commit -m "feat: invoice fraud detection utilities (5 detection passes) + tests"
```

---

### Task 7: Invoice fraud multi-agent system

**Files:**
- Create: `invoice_agent.py`
- Create: `tests/test_invoice_agent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_invoice_agent.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_invoice_agent_imports():
    from invoice_agent import run_invoice_agent
    assert callable(run_invoice_agent)

def test_invoice_agent_returns_tuple():
    """Smoke test: agent returns (str, list) without crashing when Ollama is unavailable."""
    # We mock the LLM call so this test passes without Ollama running.
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.content = "Found 2 duplicate invoices."
    mock_response.tool_calls = []

    with patch("invoice_agent.ChatOllama") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        from invoice_agent import run_invoice_agent
        result = run_invoice_agent(
            messages=[{"role": "user", "content": "Check for duplicates"}],
            session_id="test-session",
            analyst="tester",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        response_text, updated_msgs = result
        assert isinstance(response_text, str)
        assert isinstance(updated_msgs, list)
```

- [ ] **Step 2: Run test — expect ImportError**

```bash
python3 -m pytest tests/test_invoice_agent.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'invoice_agent'`

- [ ] **Step 3: Create `invoice_agent.py`**

```python
"""
invoice_agent.py — 3-stage multi-agent pipeline for invoice fraud detection.

Stage 1 — DataAgent:   Pulls invoice data and runs detection passes.
Stage 2 — AuditAgent:  Reviews findings for false positives / reasoning errors.
Stage 3 — SynthAgent:  Produces a concise, analyst-ready summary.

Each stage is a separate LLM call with a focused system prompt, reducing
hallucinations compared to a single all-in-one agent.
"""
import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langfuse import Langfuse

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_invoice_summary() -> str:
    """
    Load all invoices and return summary statistics:
    total count, total spend, vendor breakdown, date range.
    Call this first to understand the dataset scope.
    """
    from utils import load_invoices
    df = load_invoices()
    return json.dumps({
        "total_invoices": len(df),
        "total_amount":   round(float(df["amount"].sum()), 2),
        "date_range":     [str(df["date"].min().date()), str(df["date"].max().date())],
        "vendor_count":   int(df["vendor"].nunique()),
        "top_vendors":    df["vendor"].value_counts().head(5).to_dict(),
        "departments":    df["department"].value_counts().to_dict(),
    })


@tool
def find_duplicate_invoices() -> str:
    """
    Detect exact and near-duplicate invoices (same vendor + same/similar amount
    within a short date window). Returns flagged invoice pairs.
    """
    from utils import load_invoices, detect_exact_duplicates, detect_near_duplicates
    df = load_invoices()
    exact = detect_exact_duplicates(df)
    near  = detect_near_duplicates(df)

    return json.dumps({
        "exact_duplicates": exact[["invoice_id", "vendor", "amount", "date"]].assign(
            date=exact["date"].astype(str)).to_dict("records"),
        "near_duplicates":  near[["invoice_id", "vendor", "amount", "date"]].assign(
            date=near["date"].astype(str)).to_dict("records"),
        "total_duplicate_exposure": round(float(exact["amount"].sum()), 2),
    })


@tool
def find_split_billing() -> str:
    """
    Detect invoice splitting: a vendor submitting many small invoices in a short
    window to stay below the approval threshold. Returns flagged vendor/invoice groups.
    """
    from utils import load_invoices, detect_split_billing
    df = load_invoices()
    splits = detect_split_billing(df)
    if splits.empty:
        return json.dumps({"split_groups": [], "total_exposure": 0.0})
    groups = splits.groupby("vendor").agg(
        invoice_count=("invoice_id", "count"),
        total_amount=("amount", "sum"),
        date_range=("date", lambda x: [str(x.min().date()), str(x.max().date())]),
    ).reset_index()
    return json.dumps({
        "split_groups": groups.to_dict("records"),
        "total_exposure": round(float(splits["amount"].sum()), 2),
    })


@tool
def find_threshold_avoidance() -> str:
    """
    Find invoices just below the $10,000 approval threshold.
    A cluster of such invoices from one vendor is a strong fraud signal.
    """
    from utils import load_invoices, detect_threshold_avoidance
    df = load_invoices()
    flagged = detect_threshold_avoidance(df)
    return json.dumps({
        "invoices":        flagged[["invoice_id", "vendor", "amount", "date"]].assign(
            date=flagged["date"].astype(str)).to_dict("records"),
        "unique_vendors":  int(flagged["vendor"].nunique()),
        "total_exposure":  round(float(flagged["amount"].sum()), 2),
    })


@tool
def find_ghost_vendors() -> str:
    """
    Identify vendors who appear in very few invoices — potential ghost/fictitious
    vendors used to divert funds.
    """
    from utils import load_invoices, detect_ghost_vendors
    df = load_invoices()
    ghosts = detect_ghost_vendors(df)
    return json.dumps({
        "ghost_vendors":   ghosts[["invoice_id", "vendor", "amount", "date"]].assign(
            date=ghosts["date"].astype(str)).to_dict("records"),
        "vendor_names":    ghosts["vendor"].unique().tolist(),
        "total_exposure":  round(float(ghosts["amount"].sum()), 2),
    })


INVOICE_TOOLS = [
    get_invoice_summary,
    find_duplicate_invoices,
    find_split_billing,
    find_threshold_avoidance,
    find_ghost_vendors,
]

# ── Agent state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ── System prompts ────────────────────────────────────────────────────────────
DATA_AGENT_PROMPT = """You are the Data Collection Agent for FraudGuard Invoice Analysis.

Your ONLY job is to call tools and collect raw findings. Do not interpret or summarize.

For every invoice audit request:
1. Call get_invoice_summary to understand the dataset
2. Call find_duplicate_invoices
3. Call find_split_billing
4. Call find_threshold_avoidance
5. Call find_ghost_vendors

After all tool calls, output a JSON block with the raw tool results. Do not add commentary."""


AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard Invoice Analysis.

You receive raw data findings from the Data Agent. Your job is to:
1. Check each finding for logical consistency (e.g. are "duplicates" really the same invoice or just similar?)
2. Assign a confidence level (High / Medium / Low) to each fraud pattern found
3. Identify any findings that are likely false positives and explain why
4. Estimate total financial exposure

Output a structured audit review — be skeptical, precise, and cite specific invoice IDs."""


SYNTHESIS_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard Invoice Analysis.

You receive both raw data findings and an audit review. Your job is to produce a clear,
concise executive summary for a financial analyst. Structure your response as:

## Invoice Fraud Analysis Summary

**Risk Level:** [High / Medium / Low]

**Key Findings:**
- [Bullet per confirmed fraud pattern with amounts]

**Confirmed Issues:**
[Specific invoice IDs and amounts for each pattern]

**Recommended Actions:**
1. [Action]
2. [Action]

**Financial Exposure:** $X across N invoices

Be direct. Only include findings the Audit Agent rated as Medium or High confidence."""


def _build_data_agent():
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    ).bind_tools(INVOICE_TOOLS)
    tool_node = ToolNode(INVOICE_TOOLS)

    def call_model(state):
        messages = [SystemMessage(content=DATA_AGENT_PROMPT)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def should_continue(state):
        last = state["messages"][-1]
        return "tools" if (hasattr(last, "tool_calls") and last.tool_calls) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def _build_single_agent(system_prompt: str):
    """Builds a no-tool LLM agent for audit and synthesis stages."""
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )

    def call_model(state):
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


# ── Public run function ───────────────────────────────────────────────────────
def run_invoice_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple[str, list]:
    """
    Run the 3-stage invoice fraud pipeline.
    Stage 1 — DataAgent:  collect tool results
    Stage 2 — AuditAgent: review findings for accuracy
    Stage 3 — SynthAgent: produce analyst-ready summary
    Returns (final_response, updated_messages).
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    trace = langfuse.trace(
        name="invoice-fraud-agent",
        session_id=session_id,
        user_id=analyst,
        input=messages[-1]["content"] if messages else "",
    )

    try:
        # Stage 1 — Data collection
        gen1 = trace.generation(name="data-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=messages[-1]["content"] if messages else "")
        data_agent = _build_data_agent()
        data_result = data_agent.invoke({"messages": lc_messages})
        data_output = data_result["messages"][-1].content
        gen1.end(output=data_output)

        # Stage 2 — Audit
        gen2 = trace.generation(name="audit-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=data_output)
        audit_agent = _build_single_agent(AUDIT_AGENT_PROMPT)
        audit_result = audit_agent.invoke({"messages": [
            HumanMessage(content=f"Data Agent findings:\n\n{data_output}")
        ]})
        audit_output = audit_result["messages"][-1].content
        gen2.end(output=audit_output)

        # Stage 3 — Synthesis
        gen3 = trace.generation(name="synthesis-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=audit_output)
        synth_agent = _build_single_agent(SYNTHESIS_AGENT_PROMPT)
        synth_result = synth_agent.invoke({"messages": [
            HumanMessage(content=(
                f"Original request: {messages[-1]['content'] if messages else ''}\n\n"
                f"Data findings:\n{data_output}\n\n"
                f"Audit review:\n{audit_output}"
            ))
        ]})
        final_response = synth_result["messages"][-1].content
        gen3.end(output=final_response)
        trace.update(output=final_response)

    except Exception as e:
        trace.update(output={"error": str(e)})
        raise
    finally:
        langfuse.flush()

    updated = messages + [{"role": "assistant", "content": final_response}]
    return final_response, updated
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_invoice_agent.py -v
```

Expected: Both tests pass.

- [ ] **Step 5: Commit**

```bash
git add invoice_agent.py tests/test_invoice_agent.py
git commit -m "feat: 3-stage invoice fraud multi-agent pipeline (Data → Audit → Synthesis)"
```

---

### Task 8: Invoice fraud Streamlit page

**Files:**
- Create: `pages/3_Invoice_Fraud.py`

- [ ] **Step 1: Create the page**

```python
"""
pages/3_Invoice_Fraud.py — Invoice fraud detection with multi-agent pipeline.
"""
import streamlit as st
import uuid
import pandas as pd
import plotly.graph_objects as go
from utils import load_invoices, build_invoice_risk_report

st.set_page_config(
    page_title="FraudGuard — Invoice Fraud",
    page_icon="🧾",
    layout="wide",
)

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ FraudGuard")
    st.caption("Fraud Detection Platform")
    st.divider()
    st.markdown("**Agents**")
    agents = [
        ("🔍", "Velocity Agent",  "online"),
        ("🧾", "Invoice Agent",   "online"),
        ("🔎", "Audit Agent",     "online"),
        ("📊", "Synthesis Agent", "online"),
    ]
    for icon, name, status in agents:
        st.markdown(
            f"<div class='agent-status-row'>{icon} {name}"
            f"<span style='flex:1'></span>"
            f"<span class='agent-dot {status}'></span></div>",
            unsafe_allow_html=True
        )
    st.divider()
    analyst_name = st.text_input("Analyst name", placeholder="Your name", value="analyst")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🧾</div>
  <div>
    <div class="fd-title">Invoice Fraud Detection</div>
    <div class="fd-sub">Duplicate detection · Split billing · Ghost vendors · Threshold avoidance</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data + run detection ─────────────────────────────────────────────────
@st.cache_data
def cached_report():
    df = load_invoices()
    return df, build_invoice_risk_report(df)

df, report = cached_report()

# ── Summary metrics ───────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Overview</div>', unsafe_allow_html=True)
st.markdown(
    "<div class='metric-row'>"
    f"<div class='metric-box'><div class='label'>Total Invoices</div><div class='value'>{report['total_invoices']}</div></div>"
    f"<div class='metric-box'><div class='label'>🚩 Flagged</div><div class='value red'>{report['flagged_count']}</div></div>"
    f"<div class='metric-box'><div class='label'>⚠️ Exposure</div><div class='value yellow'>${report['total_flagged_amount']:,.0f}</div></div>"
    f"<div class='metric-box'><div class='label'>Exact Duplicates</div><div class='value red'>{len(report['exact_duplicates'])}</div></div>"
    f"<div class='metric-box'><div class='label'>Ghost Vendors</div><div class='value red'>{len(set(r['vendor'] for r in report['ghost_vendors']))}</div></div>"
    "</div>",
    unsafe_allow_html=True
)

# ── Tabs: Findings + Raw Data + Agent Chat ────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 Findings", "📋 All Invoices", "🤖 Agent Investigation"])

# ── TAB 1: Findings ───────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Spend by vendor donut
        st.markdown('<div class="sec-label">Spend by Vendor</div>', unsafe_allow_html=True)
        vendor_spend = df.groupby("vendor")["amount"].sum().sort_values(ascending=False).head(8)
        fig_donut = go.Figure(data=[go.Pie(
            labels=vendor_spend.index.tolist(),
            values=vendor_spend.values.tolist(),
            hole=0.55,
            marker=dict(colors=["#1d4ed8","#dc2626","#d97706","#16a34a","#7c3aed","#0891b2","#be185d","#92400e"]),
        )])
        fig_donut.update_layout(
            paper_bgcolor="white", height=280, margin=dict(t=10, b=10),
            font=dict(family="Inter, sans-serif", size=11),
            showlegend=True, legend=dict(font=dict(size=10)),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_right:
        # Fraud type breakdown bar
        st.markdown('<div class="sec-label">Fraud Pattern Counts</div>', unsafe_allow_html=True)
        patterns = {
            "Exact Duplicates":   len(report["exact_duplicates"]),
            "Near Duplicates":    len(report["near_duplicates"]),
            "Split Billing":      len(report["split_billing"]),
            "Threshold Avoidance":len(report["threshold_avoidance"]),
            "Ghost Vendors":      len(report["ghost_vendors"]),
        }
        fig_bar = go.Figure(data=[go.Bar(
            x=list(patterns.keys()),
            y=list(patterns.values()),
            marker_color=["#dc2626","#f97316","#d97706","#7c3aed","#0f172a"],
            text=list(patterns.values()),
            textposition="outside",
        )])
        fig_bar.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(gridcolor="#f3f4f6"),
            height=280, margin=dict(t=20, b=20),
            font=dict(family="Inter, sans-serif", color="#374151"),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Findings detail cards
    def _show_finding_section(title, icon, records, badge_class):
        if not records:
            return
        st.markdown(f'<div class="sec-label">{icon} {title} ({len(records)})</div>', unsafe_allow_html=True)
        for r in records[:10]:
            date_str = str(r.get("date", ""))[:10]
            amount   = r.get("amount", 0)
            st.markdown(
                f"<div class='invoice-card flagged'>"
                f"<span class='badge {badge_class}'>{title.upper()}</span>&nbsp;&nbsp;"
                f"<strong>{r.get('invoice_id','')}</strong> · {r.get('vendor','')} · "
                f"<strong>${amount:,.2f}</strong> · {date_str}"
                f"</div>",
                unsafe_allow_html=True
            )

    _show_finding_section("Exact Duplicates",    "🔁", report["exact_duplicates"],    "b-block")
    _show_finding_section("Near Duplicates",     "⚠️", report["near_duplicates"],     "b-flag")
    _show_finding_section("Split Billing",       "✂️", report["split_billing"],       "b-flag")
    _show_finding_section("Threshold Avoidance", "📏", report["threshold_avoidance"], "b-info")
    _show_finding_section("Ghost Vendors",       "👻", report["ghost_vendors"],       "b-block")

# ── TAB 2: All Invoices ───────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sec-label">Invoice Data</div>', unsafe_allow_html=True)
    show_df = df.copy()
    show_df["date"] = show_df["date"].astype(str)
    st.dataframe(
        show_df.style.apply(
            lambda row: ["background-color: #fff8f8" if row["fraud_type"] else "" for _ in row],
            axis=1
        ),
        use_container_width=True, height=500,
    )

# ── TAB 3: Agent Chat ─────────────────────────────────────────────────────────
with tab3:
    if "invoice_messages" not in st.session_state:
        st.session_state.invoice_messages = []
    if "invoice_session_id" not in st.session_state:
        st.session_state.invoice_session_id = str(uuid.uuid4())

    # Render chat history
    for msg in st.session_state.invoice_messages:
        if msg["role"] == "user":
            st.markdown(
                "<div class='chat-label chat-label-right'>You</div>"
                "<div class='chat-bubble chat-user'>" + msg["content"] + "</div>",
                unsafe_allow_html=True
            )
        else:
            content = msg["content"].replace("\n", "<br>")
            st.markdown(
                "<div class='chat-label'>🤖 Invoice Agent</div>"
                "<div class='chat-bubble chat-agent'>" + content + "</div>",
                unsafe_allow_html=True
            )

    # Pipeline indicator
    st.markdown("""
    <div class="agent-pipeline">
      <span class="pipeline-step data">1. Data Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step audit">2. Audit Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step synth">3. Synthesis Agent</span>
    </div>
    """, unsafe_allow_html=True)

    # Suggestions
    SUGGESTIONS = [
        "Find all duplicate invoices",
        "Are there any ghost vendors?",
        "Show split billing patterns",
        "What's the total fraud exposure?",
        "Which invoices avoid the approval threshold?",
    ]
    if not st.session_state.invoice_messages:
        cols = st.columns(len(SUGGESTIONS))
        for i, sug in enumerate(SUGGESTIONS):
            with cols[i]:
                if st.button(sug, key=f"inv_sug_{i}", use_container_width=True):
                    st.session_state.invoice_messages.append({"role": "user", "content": sug})
                    st.session_state._inv_run_agent = sug
                    st.rerun()

    user_input = st.chat_input("Ask the invoice fraud agent...")
    if user_input:
        st.session_state.invoice_messages.append({"role": "user", "content": user_input})
        st.session_state._inv_run_agent = user_input
        st.rerun()

    if hasattr(st.session_state, "_inv_run_agent") and st.session_state._inv_run_agent:
        st.session_state._inv_run_agent = None
        with st.spinner("Running 3-stage analysis (Data → Audit → Synthesis)..."):
            try:
                from invoice_agent import run_invoice_agent
                response, updated = run_invoice_agent(
                    messages=st.session_state.invoice_messages,
                    session_id=st.session_state.invoice_session_id,
                    analyst=analyst_name or "analyst",
                )
                st.session_state.invoice_messages = updated
            except Exception as e:
                err = f"Agent error: {e}. Ensure Ollama is running."
                st.session_state.invoice_messages.append({"role": "assistant", "content": err})
        st.rerun()
```

- [ ] **Step 2: Verify the page syntax**

```bash
python3 -c "
import ast, sys
with open('pages/3_Invoice_Fraud.py') as f:
    source = f.read()
try:
    ast.parse(source)
    print('Syntax OK')
except SyntaxError as e:
    print(f'Syntax error: {e}')
    sys.exit(1)
"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add pages/3_Invoice_Fraud.py
git commit -m "feat: invoice fraud detection page with findings dashboard and agent chat"
```

---

## Phase 4: Multi-Agent Velocity Fraud Pipeline

### Task 9: Refactor `agent.py` to 3-stage pipeline

**Files:**
- Rewrite: `agent.py`

The current single-agent approach lets one LLM call both gather data and reason about it, which causes hallucinations when the model confabulates tool results. The fix is:
- **DataAgent** — calls tools only, outputs raw JSON summary
- **AuditAgent** — no tools, cross-checks data for inconsistencies, rates confidence
- **SynthAgent** — no tools, produces clean analyst-facing response

- [ ] **Step 1: Add a test for the new `run_agent` signature**

In `tests/test_utils.py`, add:
```python
def test_run_agent_returns_tuple():
    """Smoke test: run_agent returns (str, list) shape with mocked LLM."""
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
```

- [ ] **Step 2: Run test — expect it to pass (existing signature matches)**

```bash
python3 -m pytest tests/test_utils.py::test_run_agent_returns_tuple -v
```

- [ ] **Step 3: Rewrite `agent.py` with 3-stage pipeline**

Replace the entire file content:
```python
"""
agent.py — 3-stage multi-agent pipeline for transaction velocity fraud.

Stage 1 — DataAgent:   Calls tools, gathers raw facts. No reasoning.
Stage 2 — AuditAgent:  Reviews DataAgent output. Flags inconsistencies.
Stage 3 — SynthAgent:  Produces clean, analyst-ready response.

This replaces the single-agent design which hallucinated when reasoning
and data collection were combined in one pass.
"""
import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langfuse import Langfuse

load_dotenv()

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)

_txns     = None
_accounts = None

def _load():
    global _txns, _accounts
    if _txns is None:
        _txns     = pd.read_csv("synthetictables/transactions.csv", parse_dates=["timestamp"])
        _accounts = pd.read_csv("synthetictables/accounts.csv")


@tool
def lookup_account(account_id: str) -> str:
    """Look up account details: name, type, home city, KYC status, dormancy, risk tier."""
    _load()
    acc = _accounts[_accounts["account_id"] == account_id.upper()]
    if acc.empty:
        return f"Account {account_id} not found."
    row = acc.iloc[0]
    return json.dumps({
        "account_id":   row["account_id"],
        "customer":     row["customer_name"],
        "account_type": row["account_type"],
        "home_city":    row["home_city"],
        "risk_tier":    row["risk_tier"],
        "kyc_verified": bool(row["kyc_verified"]),
        "is_dormant":   bool(row["is_dormant"]),
        "dormant_days": int(row["dormant_days"]),
        "open_date":    row["open_date"],
    })


@tool
def get_transaction_history(account_id: str, limit: int = 20) -> str:
    """Get most recent transactions with flags. Use to understand activity pattern."""
    _load()
    txns = (
        _txns[_txns["account_id"] == account_id.upper()]
        .sort_values("timestamp", ascending=False)
        .head(limit)
    )
    if txns.empty:
        return f"No transactions found for {account_id}."
    records = []
    for _, row in txns.iterrows():
        records.append({
            "timestamp":     row["timestamp"].strftime("%Y-%m-%d %H:%M"),
            "amount":        round(float(row["amount"]), 2),
            "type":          row["txn_type"],
            "city":          row["city"],
            "merchant":      row["merchant"],
            "status":        row["status"],
            "velocity_flag": bool(row["velocity_flag"]),
            "geo_flag":      bool(row["geo_flag"]),
            "fraud_type":    row["fraud_type"] if pd.notna(row["fraud_type"]) else None,
        })
    return json.dumps(records)


@tool
def analyze_velocity(account_id: str) -> str:
    """Compute velocity analysis: max txns/5min, geo flags, risk score, peak window."""
    _load()
    from utils import compute_velocity
    acc_txns = _txns[_txns["account_id"] == account_id.upper()].copy()
    if acc_txns.empty:
        return f"No transactions found for {account_id}."
    v = compute_velocity(acc_txns)
    peak_start, peak_end = v["peak_window"]
    return json.dumps({
        "account_id":   account_id.upper(),
        "max_velocity": v["max_velocity"],
        "threshold":    5,
        "geo_flags":    v["geo_flags"],
        "total_amount": v["total_amount"],
        "total_txns":   len(acc_txns),
        "fraud_types":  v["fraud_types"],
        "risk_level":   v["risk_level"],
        "risk_score":   v["risk_score"],
        "peak_window": {
            "start": peak_start.strftime("%Y-%m-%d %H:%M") if peak_start else None,
            "end":   peak_end.strftime("%Y-%m-%d %H:%M")   if peak_end   else None,
        },
    })


@tool
def get_similar_flagged_accounts(account_id: str) -> str:
    """Find accounts with fraud in the same time window. Use for coordinated attack detection."""
    _load()
    target_txns = _txns[_txns["account_id"] == account_id.upper()]
    if target_txns.empty:
        return "No transactions found for comparison."
    flagged = target_txns[target_txns["velocity_flag"] | target_txns["geo_flag"]]
    if flagged.empty:
        return "No flagged transactions on this account to compare against."
    window_txns = _txns[
        (_txns["timestamp"] >= flagged["timestamp"].min()) &
        (_txns["timestamp"] <= flagged["timestamp"].max()) &
        (_txns["account_id"] != account_id.upper()) &
        (_txns["is_fraud"] == True)
    ]
    similar = (
        window_txns.groupby("account_id")
        .agg(fraud_txns=("is_fraud", "sum"), cities=("city", lambda x: list(x.unique())))
        .reset_index().head(5)
    )
    if similar.empty:
        return "No similar flagged accounts found in the same time window."
    flag_cities = set(flagged["city"].tolist())
    results = []
    for _, row in similar.iterrows():
        results.append({
            "account_id":   row["account_id"],
            "fraud_txns":   int(row["fraud_txns"]),
            "cities":       row["cities"],
            "city_overlap": list(flag_cities.intersection(set(row["cities"]))),
        })
    return json.dumps(results)


@tool
def record_decision(account_id: str, decision: str, notes: str = "") -> str:
    """Record analyst decision: blocked / cleared / escalated / monitoring."""
    valid = {"blocked", "cleared", "escalated", "monitoring"}
    if decision.lower() not in valid:
        return f"Invalid decision '{decision}'. Must be one of: {', '.join(valid)}."
    from utils import save_decision
    save_decision(account_id.upper(), decision.lower(), "agent", notes)
    return f"Decision recorded: {account_id.upper()} → {decision.lower()}."


TOOLS = [lookup_account, get_transaction_history, analyze_velocity,
         get_similar_flagged_accounts, record_decision]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


DATA_AGENT_PROMPT = """You are the Data Collection Agent for FraudGuard.

Call tools to collect facts. Do NOT reason, interpret, or summarize.
For any account investigation:
1. lookup_account
2. analyze_velocity
3. get_transaction_history
4. If risk is High: get_similar_flagged_accounts
5. If user requests a decision: record_decision

After tool calls, output ONLY the raw data as collected — no interpretation."""


AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard.

You receive raw data from the Data Agent. Your job:
1. Verify every claim is supported by the actual data (no hallucinated numbers)
2. Check velocity counts match the transaction history
3. Confirm geo flags correspond to actual city mismatches
4. Rate each finding: Confirmed / Uncertain / Likely False Positive
5. Note any data gaps that should affect the final recommendation

Be skeptical. If a number doesn't add up, flag it."""


SYNTH_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard.

You receive data findings + an audit review. Produce a concise analyst summary:

## Fraud Investigation: [Account ID]

**Risk Level:** [High / Medium / Low]  
**Recommendation:** [Block / Clear / Escalate / Monitor]

**Key Evidence:**
- [Confirmed finding with specific numbers]

**Caveats:** [Anything the Audit Agent flagged as uncertain]

Be direct. Only cite numbers that appear in the actual data."""


def _build_data_agent():
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    ).bind_tools(TOOLS)
    tool_node = ToolNode(TOOLS)

    def call_model(state):
        messages = [SystemMessage(content=DATA_AGENT_PROMPT)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    def should_continue(state):
        last = state["messages"][-1]
        return "tools" if (hasattr(last, "tool_calls") and last.tool_calls) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def _build_reasoning_agent(system_prompt: str):
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )
    def call_model(state):
        return {"messages": [llm.invoke([SystemMessage(content=system_prompt)] + state["messages"])]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


def run_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple[str, list]:
    """
    Run the 3-stage fraud investigation pipeline.
    Returns (response_text, updated_messages).
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    trace = langfuse.trace(
        name="fraud-agent-run",
        session_id=session_id,
        user_id=analyst,
        input=messages[-1]["content"] if messages else "",
    )

    try:
        # Stage 1: Data collection
        gen1 = trace.generation(name="data-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=messages[-1]["content"] if messages else "")
        data_result = _build_data_agent().invoke({"messages": lc_messages})
        data_output = data_result["messages"][-1].content
        gen1.end(output=data_output)

        # Stage 2: Audit
        gen2 = trace.generation(name="audit-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=data_output)
        audit_result = _build_reasoning_agent(AUDIT_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=f"Data Agent output:\n\n{data_output}")]
        })
        audit_output = audit_result["messages"][-1].content
        gen2.end(output=audit_output)

        # Stage 3: Synthesis
        gen3 = trace.generation(name="synth-agent", model=os.getenv("OLLAMA_MODEL", "qwen2.5"),
                                input=audit_output)
        synth_result = _build_reasoning_agent(SYNTH_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=(
                f"User request: {messages[-1]['content'] if messages else ''}\n\n"
                f"Data findings:\n{data_output}\n\n"
                f"Audit review:\n{audit_output}"
            ))]
        })
        final = synth_result["messages"][-1].content
        gen3.end(output=final)
        trace.update(output=final)

    except Exception as e:
        trace.update(output={"error": str(e)})
        raise
    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}]
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_utils.py -v
```

Expected: All pass (including `test_run_agent_returns_tuple`).

- [ ] **Step 5: Commit**

```bash
git add agent.py
git commit -m "feat: refactor velocity agent to 3-stage Data→Audit→Synthesis pipeline"
```

---

### Task 10: Update Agent Chat page for pipeline visibility

**Files:**
- Modify: `pages/2_Agent_Chat.py`

- [ ] **Step 1: Add pipeline indicator to the chat page**

In `pages/2_Agent_Chat.py`, replace the `with st.spinner(...)` block:
```python
with st.spinner("Running investigation pipeline..."):
    # Show pipeline progress
    pipeline_placeholder = st.empty()
    pipeline_placeholder.markdown("""
    <div class="agent-pipeline">
      <span class="pipeline-step data active">1. Data Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step audit">2. Audit Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step synth">3. Synthesis Agent</span>
    </div>
    """, unsafe_allow_html=True)
    try:
        from agent import run_agent
        response, updated_messages = run_agent(
            messages=st.session_state.messages,
            session_id=st.session_state.session_id,
            analyst=st.session_state.analyst or "analyst",
        )
        st.session_state.messages = updated_messages
        pipeline_placeholder.empty()
    except Exception as e:
        pipeline_placeholder.empty()
        error_msg = (
            "Agent error: " + str(e) +
            ". Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull qwen2.5`)."
        )
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
```

- [ ] **Step 2: Add sidebar nav links to Agent Chat page**

In `pages/2_Agent_Chat.py`, add at the start of the `with st.sidebar:` block:
```python
st.markdown("### 🛡️ FraudGuard")
st.caption("Fraud Detection Platform")
st.divider()
st.page_link("account_lookup.py",        label="🔍 Account Lookup")
st.page_link("pages/alert_queue.py",     label="🚨 Alert Queue")
st.page_link("pages/2_Agent_Chat.py",    label="🤖 Agent Chat")
st.page_link("pages/3_Invoice_Fraud.py", label="🧾 Invoice Fraud")
st.divider()
```

- [ ] **Step 3: Verify syntax**

```bash
python3 -c "
import ast
with open('pages/2_Agent_Chat.py') as f: ast.parse(f.read())
print('Syntax OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add pages/2_Agent_Chat.py
git commit -m "feat: add pipeline stage indicator and nav links to agent chat"
```

---

## Final Verification

- [ ] **Smoke test all pages parse correctly**

```bash
cd "/Users/nirvahnthakur/Library/Mobile Documents/com~apple~CloudDocs/Work RT/financeagent"
for f in account_lookup.py pages/alert_queue.py pages/2_Agent_Chat.py pages/3_Invoice_Fraud.py invoice_agent.py agent.py utils.py; do
    python3 -c "import ast; ast.parse(open('$f').read()); print('OK: $f')"
done
```

Expected: `OK: <file>` for each.

- [ ] **Run full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: All pass.

- [ ] **Verify invoice data exists and is valid**

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('synthetictables/invoices.csv', parse_dates=['date'])
assert df.shape[0] > 0
assert 'fraud_type' in df.columns
print(f'Invoices: {len(df)} rows, {df[\"fraud_type\"].ne(\"\").sum()} flagged')
"
```

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat: FraudGuard v2 — light theme, multi-account comparison, invoice fraud agent, 3-stage pipeline"
```
