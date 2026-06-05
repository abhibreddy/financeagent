"""
components.py — shared UI building blocks for FraudGuard pages.
"""
import streamlit as st


def render_sidebar_nav():
    """Standard sidebar: branding, nav links, agent status. Call inside `with st.sidebar:` or standalone."""
    st.markdown('<div class="sb-brand">🛡️ FraudGuard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-tagline">Fraud Detection Platform</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section-label">Navigation</div>', unsafe_allow_html=True)
    st.page_link("account_lookup.py",        label="🏠  Dashboard")
    st.page_link("pages/alert_queue.py",     label="🚨  Alert Queue")
    st.page_link("pages/2_Agent_Chat.py",    label="🤖  Agent Chat")
    st.page_link("pages/3_Invoice_Fraud.py", label="🧾  Invoice Fraud")

    st.markdown('<div class="sb-section-label">Agents</div>', unsafe_allow_html=True)
    _agents = [
        ("Velocity Agent",  "online"),
        ("Invoice Agent",   "online"),
        ("Audit Agent",     "online"),
        ("Synthesis Agent", "online"),
    ]
    for _name, _status in _agents:
        st.markdown(
            f'<div class="sb-agent-row">'
            f'<span class="agent-dot {_status}"></span>{_name}'
            f'</div>',
            unsafe_allow_html=True,
        )
