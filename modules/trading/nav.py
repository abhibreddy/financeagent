"""
modules/trading/nav.py — exposes the Trading module's pages to the ERP shell.
Paths are relative to the app entrypoint (app.py at repo root).
"""
import streamlit as st

_PAGES = "modules/trading/pages"


def get_pages():
    return [
        st.Page(f"{_PAGES}/trading_dashboard.py",  title="Trading Dashboard", icon="📈"),
        st.Page(f"{_PAGES}/trading_agent_chat.py", title="Portfolio Agent",   icon="🤖"),
        st.Page(f"{_PAGES}/stock_forecaster.py",   title="Stock Forecaster",  icon="🔮"),
    ]
