"""
modules/finance/nav.py — exposes the Finance module's pages to the ERP shell.

Paths are relative to the app entrypoint (app.py at repo root) so they match the
strings used by st.page_link elsewhere.
"""
import streamlit as st

_PAGES = "modules/finance/pages"


def get_pages():
    return [
        st.Page(f"{_PAGES}/dashboard.py",     title="Dashboard",     icon="🏠"),
        st.Page(f"{_PAGES}/alert_queue.py",   title="Alert Queue",   icon="🚨"),
        st.Page(f"{_PAGES}/agent_chat.py",    title="Agent Chat",    icon="🤖"),
        st.Page(f"{_PAGES}/invoice_fraud.py", title="Invoice Fraud", icon="🧾"),
    ]
