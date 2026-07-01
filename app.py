"""
app.py — ERP shell entry point.

Hosts the module registry via st.navigation, grouped by module section. Each module
exposes get_pages() -> list[st.Page]; app.py stays module-agnostic. Page config and CSS
are set once here, so page bodies never call st.set_page_config or inject CSS themselves.

Run with: streamlit run app.py
"""
import streamlit as st

from core.ui import inject_css
from modules.finance.nav import get_pages as finance_pages
from modules.trading.nav import get_pages as trading_pages

st.set_page_config(
    page_title="RT ERP",
    page_icon="🛡️",
    layout="wide",
)

nav = st.navigation({
    "Home": [st.Page("home.py", title="Home", icon="🏠", default=True)],
    "Finance": finance_pages(),
    "Trading": trading_pages(),
})

inject_css()
nav.run()
