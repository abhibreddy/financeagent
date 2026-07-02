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
    "url": "/finance-dashboard",
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
    "url": "/trading-dashboard",
    "functions": [
        ("📈", "Trading Dashboard", "modules/trading/pages/trading_dashboard.py"),
        ("🤖", "Portfolio Agent", "modules/trading/pages/trading_agent_chat.py"),
        ("🔮", "Stock Forecaster", "modules/trading/pages/stock_forecaster.py"),
    ],
}


def _card_html(mod: dict) -> str:
    """The entire card is one clickable anchor linking to the module dashboard."""
    fns = "".join(
        f'<div class="home-card-fn">{icon}&nbsp;&nbsp;{label}</div>'
        for icon, label, _ in mod["functions"]
    )
    return f"""
    <a class="home-card" href="{mod['url']}" target="_self">
      <div class="home-card-icon">{mod['icon']}</div>
      <div class="home-card-title">{mod['title']}</div>
      <div class="home-card-desc">{mod['desc']}</div>
      <div class="home-card-fn-label">FUNCTIONS</div>
      {fns}
    </a>
    """


col_finance, col_trading = st.columns(2, gap="large")
with col_finance:
    st.markdown(_card_html(FINANCE), unsafe_allow_html=True)
with col_trading:
    st.markdown(_card_html(TRADING), unsafe_allow_html=True)
