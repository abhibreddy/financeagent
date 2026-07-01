"""
trading_dashboard.py — portfolio overview: metrics, positions, exposure & price charts.
Mirrors the finance Dashboard's metric/card/Plotly patterns.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.trading.utils import (
    load_positions, load_prices,
    compute_portfolio_metrics, compute_exposure, compute_risk_metrics,
)


@st.cache_data
def _load():
    return load_positions(), load_prices()


positions, prices = _load()
metrics = compute_portfolio_metrics(positions)
exposure = compute_exposure(positions)
risk = compute_risk_metrics(prices, positions)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">📈</div>
  <div>
    <div class="fd-title">Trading</div>
    <div class="fd-sub">Portfolio Analytics & Risk</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Summary metrics ───────────────────────────────────────────────────────────
_lvl_color = {"High": "red", "Medium": "", "Low": "green"}
pnl_color = "green" if metrics["unrealized_pnl"] >= 0 else "red"
conc_color = _lvl_color.get(exposure["concentration_level"], "")
risk_color = _lvl_color.get(risk["risk_level"], "")

st.markdown(f"""
<div class="metric-row">
  <div class="metric-box">
    <div class="label">Market Value</div>
    <div class="value">${metrics['total_market_value']:,.0f}</div>
  </div>
  <div class="metric-box">
    <div class="label">Unrealized P&L</div>
    <div class="value {pnl_color}">${metrics['unrealized_pnl']:,.0f}</div>
  </div>
  <div class="metric-box">
    <div class="label">Unrealized %</div>
    <div class="value {pnl_color}">{metrics['unrealized_pnl_pct']}%</div>
  </div>
  <div class="metric-box">
    <div class="label">Concentration</div>
    <div class="value {conc_color}">{exposure['concentration_level']}</div>
  </div>
  <div class="metric-box">
    <div class="label">Risk Score</div>
    <div class="value {risk_color}">{risk['risk_score']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sector exposure chart ─────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Sector Exposure</div>', unsafe_allow_html=True)
sector = exposure["sector_exposure"]
fig = go.Figure(go.Bar(
    x=list(sector.values()), y=list(sector.keys()), orientation="h",
    marker_color="#4f8cff",
))
fig.update_layout(
    height=280, margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="% of portfolio", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, width="stretch")

# ── Positions table ───────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Positions</div>', unsafe_allow_html=True)
p = positions.copy()
p["market_value"] = (p["quantity"] * p["current_price"]).round(2)
p["unrealized_pnl"] = ((p["current_price"] - p["avg_cost"]) * p["quantity"]).round(2)
p["weight_%"] = p["ticker"].map(metrics["weights"])
st.dataframe(
    p[["ticker", "sector", "asset_class", "quantity", "avg_cost", "current_price",
       "market_value", "unrealized_pnl", "weight_%"]],
    width="stretch", hide_index=True,
)

# ── Price history ─────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Price History</div>', unsafe_allow_html=True)
tickers = positions["ticker"].tolist()
pick = st.selectbox("Ticker", tickers)
grp = prices[prices["ticker"] == pick].sort_values("date")
line = go.Figure(go.Scatter(x=grp["date"], y=grp["close"], mode="lines", line=dict(color="#4f8cff")))
line.update_layout(
    height=300, margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="Close", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(line, width="stretch")
