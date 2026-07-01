"""
trading_agent_chat.py — conversational portfolio analysis via LangGraph + Azure OpenAI + Langfuse.
Mirrors the finance Agent Chat page, calling the trading pipeline.
"""
import streamlit as st
import uuid
import os

# ── Session state init ────────────────────────────────────────────────────────
if "t_messages" not in st.session_state:
    st.session_state.t_messages = []
if "t_session_id" not in st.session_state:
    st.session_state.t_session_id = str(uuid.uuid4())
if "t_analyst" not in st.session_state:
    st.session_state.t_analyst = "analyst"
if "t_pending_input" not in st.session_state:
    st.session_state.t_pending_input = None
if "t_last_debug" not in st.session_state:
    st.session_state.t_last_debug = {}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">📈</div>
  <div>
    <div class="fd-title">Portfolio Agent</div>
    <div class="fd-sub">Portfolio Analysis · gpt-4o-mini via Azure OpenAI · Traced by Langfuse</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sb-section-label">Session</div>', unsafe_allow_html=True)

    analyst = st.text_input("Analyst name", value=st.session_state.t_analyst, placeholder="Your name")
    if analyst:
        st.session_state.t_analyst = analyst

    st.divider()
    st.markdown("**Session ID**")
    st.code(st.session_state.t_session_id[:18] + "...", language=None)

    langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    st.markdown("**[Open Langfuse →](" + langfuse_host + ")**", unsafe_allow_html=False)

    st.divider()
    if st.button("🗑 Clear conversation", width="stretch"):
        st.session_state.t_messages = []
        st.session_state.t_pending_input = None
        st.session_state.t_session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.markdown("**Available tools**")
    for icon, name in [
        ("💰", "get_portfolio_summary"),
        ("📊", "analyze_exposure"),
        ("⚠️", "analyze_risk"),
        ("📈", "get_price_trend"),
        ("🗞", "get_signal"),
    ]:
        st.markdown("<span class='tool-chip'>" + icon + " " + name + "</span>", unsafe_allow_html=True)

# ── Suggested prompts ─────────────────────────────────────────────────────────
SUGGESTIONS = [
    "Analyze portfolio risk",
    "What's my largest concentration?",
    "Summarize unrealized P&L",
    "Should I rebalance?",
]

if not st.session_state.t_messages and st.session_state.t_pending_input is None:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">📈</div>
      Ask the portfolio agent about risk, concentration, P&L, or rebalancing.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="suggestion-row">', unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTIONS))
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i]:
            if st.button(suggestion, key="t_sug_" + str(i), width="stretch"):
                st.session_state.t_pending_input = suggestion
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

for msg in st.session_state.t_messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="📈"):
            st.markdown(msg["content"])
            st.caption(
                f"Traced in [Langfuse]({langfuse_host})"
                f" · session: {st.session_state.t_session_id[:12]}..."
            )

# ── Pipeline debug panel ──────────────────────────────────────────────────────
if st.session_state.get("t_last_debug"):
    debug = st.session_state.t_last_debug
    with st.expander("🔬 Pipeline Debug — last run", expanded=False):
        gt = debug.get("ground_truth", "")
        if gt:
            if "DISCREPANCIES" in gt:
                st.error(gt)
            else:
                st.success(gt)
        t1, t2 = st.tabs(["Data Agent", "Audit Agent"])
        with t1:
            st.code(debug.get("data_agent", "—"), language=None)
        with t2:
            st.markdown(debug.get("audit_agent", "—"))

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask the agent about your portfolio...")
to_send = user_input or st.session_state.t_pending_input

if to_send:
    st.session_state.t_pending_input = None
    if not st.session_state.t_messages or st.session_state.t_messages[-1]["content"] != to_send:
        st.session_state.t_messages.append({"role": "user", "content": to_send})
        st.session_state._t_run_agent_for = to_send
        st.rerun()

if hasattr(st.session_state, "_t_run_agent_for") and st.session_state._t_run_agent_for:
    st.session_state._t_run_agent_for = None
    with st.spinner("Running portfolio pipeline..."):
        pipeline_ph = st.empty()
        pipeline_ph.markdown("""
        <div class="agent-pipeline">
          <span class="pipeline-step data active">1. Data Agent</span>
          <span class="pipeline-arrow">→</span>
          <span class="pipeline-step audit">2. Audit Agent</span>
          <span class="pipeline-arrow">→</span>
          <span class="pipeline-step synth">3. Synthesis Agent</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            from modules.trading.trading_agent import run_trading_agent
            response, updated_messages, debug = run_trading_agent(
                messages=st.session_state.t_messages,
                session_id=st.session_state.t_session_id,
                analyst=st.session_state.t_analyst or "analyst",
            )
            st.session_state.t_messages = updated_messages
            st.session_state.t_last_debug = debug
            pipeline_ph.empty()
        except Exception as e:
            pipeline_ph.empty()
            st.session_state.t_messages.append(
                {"role": "assistant", "content": f"Agent error: {e}. Check your Azure OpenAI credentials in .env."}
            )
    st.rerun()
