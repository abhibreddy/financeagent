"""
stock_forecaster.py — FinGPT-Forecaster-style single-stock outlook (Azure OpenAI).

Reproduces the FinGPT-Forecaster demo flow: pick a ticker, pull recent news + prices +
financials, and get positive developments / potential concerns / a next-week prediction.
Runs one Azure call per forecast (token-lean). Requires FINNHUB_API_KEY in .env.
"""
import streamlit as st

from core.config import FINNHUB_API_KEY

st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🔮</div>
  <div>
    <div class="fd-title">Stock Forecaster</div>
    <div class="fd-sub">FinGPT-Forecaster methodology · powered by Azure OpenAI</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Methodology adapted from AI4Finance-Foundation/FinGPT (FinGPT-Forecaster). "
    "Market data via Finnhub + yfinance; reasoning via Azure OpenAI (no local GPU models)."
)

if not FINNHUB_API_KEY:
    st.warning(
        "**FINNHUB_API_KEY is not set.** Add a free key from "
        "[finnhub.io](https://finnhub.io) to `.env` to enable live forecasting."
    )

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    ticker = st.text_input("Ticker symbol", value="AAPL", placeholder="e.g. AAPL, MSFT, NVDA")
with c2:
    weeks = st.slider("Past weeks", min_value=1, max_value=4, value=2,
                      help="More weeks = more news context = more input tokens.")
with c3:
    with_basics = st.checkbox("Include financials", value=True)

run = st.button("🔮 Generate Forecast", type="primary", disabled=not FINNHUB_API_KEY)

if run and ticker.strip():
    with st.spinner(f"Gathering market data and forecasting {ticker.upper()}..."):
        try:
            from modules.trading.forecaster import forecast, ForecasterError
            result = forecast(ticker, weeks=weeks, with_basics=with_basics)
        except ForecasterError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Forecast failed: {e}")
            st.stop()

    st.markdown(f"### {result['symbol']} — outlook as of {result['as_of']}")
    st.markdown(result["report"])

    with st.expander("🔬 Prompt sent to the model (data gathered deterministically)"):
        st.code(result["prompt"], language=None)
