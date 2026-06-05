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
    _agents = [
        ("🔍", "Velocity Agent",  "online"),
        ("🧾", "Invoice Agent",   "online"),
        ("🔎", "Audit Agent",     "online"),
        ("📊", "Synthesis Agent", "online"),
    ]
    for _icon, _name, _status in _agents:
        st.markdown(
            f"<div class='agent-status-row'>{_icon} {_name}"
            f"<span style='flex:1'></span>"
            f"<span class='agent-dot {_status}'></span></div>",
            unsafe_allow_html=True,
        )
    st.divider()
    st.page_link("account_lookup.py",        label="🔍 Account Lookup")
    st.page_link("pages/alert_queue.py",     label="🚨 Alert Queue")
    st.page_link("pages/2_Agent_Chat.py",    label="🤖 Agent Chat")
    st.page_link("pages/3_Invoice_Fraud.py", label="🧾 Invoice Fraud")
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
ghost_vendor_count = len(set(r["vendor"] for r in report["ghost_vendors"]))
st.markdown(
    "<div class='metric-row'>"
    f"<div class='metric-box'><div class='label'>Total Invoices</div><div class='value'>{report['total_invoices']}</div></div>"
    f"<div class='metric-box'><div class='label'>🚩 Flagged</div><div class='value red'>{report['flagged_count']}</div></div>"
    f"<div class='metric-box'><div class='label'>⚠️ Exposure</div><div class='value yellow'>${report['total_flagged_amount']:,.0f}</div></div>"
    f"<div class='metric-box'><div class='label'>Exact Duplicates</div><div class='value red'>{len(report['exact_duplicates'])}</div></div>"
    f"<div class='metric-box'><div class='label'>Ghost Vendors</div><div class='value red'>{ghost_vendor_count}</div></div>"
    "</div>",
    unsafe_allow_html=True
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 Findings", "📋 All Invoices", "🤖 Agent Investigation"])

# ── TAB 1: Findings ───────────────────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns(2)

    with col_left:
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
        st.markdown('<div class="sec-label">Fraud Pattern Counts</div>', unsafe_allow_html=True)
        patterns = {
            "Exact Duplicates":    len(report["exact_duplicates"]),
            "Near Duplicates":     len(report["near_duplicates"]),
            "Split Billing":       len(report["split_billing"]),
            "Threshold Avoidance": len(report["threshold_avoidance"]),
            "Ghost Vendors":       len(report["ghost_vendors"]),
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
                unsafe_allow_html=True,
            )

    _show_finding_section("Exact Duplicates",     "🔁", report["exact_duplicates"],    "b-block")
    _show_finding_section("Near Duplicates",      "⚠️", report["near_duplicates"],     "b-flag")
    _show_finding_section("Split Billing",        "✂️", report["split_billing"],       "b-flag")
    _show_finding_section("Threshold Avoidance",  "📏", report["threshold_avoidance"], "b-info")
    _show_finding_section("Ghost Vendors",        "👻", report["ghost_vendors"],       "b-block")

# ── TAB 2: All Invoices ───────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sec-label">Invoice Data</div>', unsafe_allow_html=True)
    show_df = df.copy()
    show_df["date"] = show_df["date"].astype(str)
    st.dataframe(
        show_df.style.apply(
            lambda row: ["background-color: #fff8f8" if row["fraud_type"] else "" for _ in row],
            axis=1,
        ),
        use_container_width=True,
        height=500,
    )

# ── TAB 3: Agent Chat ─────────────────────────────────────────────────────────
with tab3:
    if "invoice_messages" not in st.session_state:
        st.session_state.invoice_messages = []
    if "invoice_session_id" not in st.session_state:
        st.session_state.invoice_session_id = str(uuid.uuid4())

    for msg in st.session_state.invoice_messages:
        if msg["role"] == "user":
            st.markdown(
                "<div class='chat-label chat-label-right'>You</div>"
                "<div class='chat-bubble chat-user'>" + msg["content"] + "</div>",
                unsafe_allow_html=True,
            )
        else:
            content = msg["content"].replace("\n", "<br>")
            st.markdown(
                "<div class='chat-label'>🤖 Invoice Agent</div>"
                "<div class='chat-bubble chat-agent'>" + content + "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("""
    <div class="agent-pipeline">
      <span class="pipeline-step data">1. Data Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step audit">2. Audit Agent</span>
      <span class="pipeline-arrow">→</span>
      <span class="pipeline-step synth">3. Synthesis Agent</span>
    </div>
    """, unsafe_allow_html=True)

    SUGGESTIONS = [
        "Find all duplicate invoices",
        "Are there any ghost vendors?",
        "Show split billing patterns",
        "What's the total fraud exposure?",
        "Which invoices avoid the approval threshold?",
    ]

    if not st.session_state.invoice_messages:
        sug_cols = st.columns(len(SUGGESTIONS))
        for i, sug in enumerate(SUGGESTIONS):
            with sug_cols[i]:
                if st.button(sug, key=f"inv_sug_{i}", use_container_width=True):
                    st.session_state.invoice_messages.append({"role": "user", "content": sug})
                    st.session_state._inv_run_agent = sug
                    st.rerun()

    user_input = st.chat_input("Ask the invoice fraud agent...")
    if user_input:
        st.session_state.invoice_messages.append({"role": "user", "content": user_input})
        st.session_state._inv_run_agent = user_input
        st.rerun()

    if getattr(st.session_state, "_inv_run_agent", None):
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
                err = f"Agent error: {e}. Ensure Ollama is running (`ollama serve`)."
                st.session_state.invoice_messages.append({"role": "assistant", "content": err})
        st.rerun()
