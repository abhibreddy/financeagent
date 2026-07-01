"""
home.py — ERP landing page.

The default screen: two module cards (Finance + Trading), each listing its functions as
links that jump straight into the relevant page. Rendered inside app.py's st.navigation, so
it sets no page config and injects no CSS itself.
"""
import streamlit as st

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🏢</div>
  <div>
    <div class="fd-title">RT ERP</div>
    <div class="fd-sub">Choose a module to get started</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Module definitions ──────────────────────────────────────────────────────────
FINANCE = {
    "icon": "🛡️",
    "title": "Finance Agent",
    "desc": "Real-time fraud detection: alert triage, conversational investigation, and invoice fraud scanning.",
    "functions": [
        ("🏠", "Dashboard", "modules/finance/pages/dashboard.py"),
        ("🚨", "Alert Queue", "modules/finance/pages/alert_queue.py"),
        ("🤖", "Agent Chat", "modules/finance/pages/agent_chat.py"),
        ("🧾", "Invoice Fraud", "modules/finance/pages/invoice_fraud.py"),
    ],
}

TRADING = {
    "icon": "📈",
    "title": "Trading Agent",
    "desc": "Portfolio analytics, a multi-agent portfolio analyst, and FinGPT-style single-stock forecasting.",
    "functions": [
        ("📈", "Trading Dashboard", "modules/trading/pages/trading_dashboard.py"),
        ("🤖", "Portfolio Agent", "modules/trading/pages/trading_agent_chat.py"),
        ("🔮", "Stock Forecaster", "modules/trading/pages/stock_forecaster.py"),
    ],
}


def _render_card(mod: dict):
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="feat-card-icon">{mod['icon']}</div>
            <div class="feat-card-title">{mod['title']}</div>
            <div class="feat-card-desc">{mod['desc']}</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sec-label">Functions</div>', unsafe_allow_html=True)
        for icon, label, path in mod["functions"]:
            st.page_link(path, label=f"{icon}  {label}", width="stretch")


col_finance, col_trading = st.columns(2, gap="large")
with col_finance:
    _render_card(FINANCE)
with col_trading:
    _render_card(TRADING)
