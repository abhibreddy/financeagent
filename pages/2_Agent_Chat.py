"""
pages/2_Agent_Chat.py
Conversational fraud investigation chat powered by LangGraph + Ollama + Langfuse.
"""

import streamlit as st
import uuid
import os
from dotenv import load_dotenv
from components import render_sidebar_nav

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FraudGuard — Agent Chat",
    page_icon="🤖",
    layout="centered",
)

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "analyst" not in st.session_state:
    st.session_state.analyst = "analyst"

# pending_input holds a suggestion click so it survives the rerun
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🤖</div>
  <div>
    <div class="fd-title">Agent Chat</div>
    <div class="fd-sub">Fraud Investigation · qwen2.5:14b via Ollama · Traced by Langfuse</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_nav()
    st.markdown('<div class="sb-section-label">Session</div>', unsafe_allow_html=True)

    analyst = st.text_input("Analyst name", value=st.session_state.analyst, placeholder="Your name")
    if analyst:
        st.session_state.analyst = analyst

    st.divider()
    st.markdown("**Session ID**")
    st.code(st.session_state.session_id[:18] + "...", language=None)

    langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
    st.markdown(
        "**[Open Langfuse →](" + langfuse_host + ")**",
        unsafe_allow_html=False
    )

    st.divider()
    if st.button("🗑 Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_input = None
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.markdown("**Available tools**")
    tools = [
        ("🔍", "lookup_account"),
        ("📋", "get_transaction_history"),
        ("⚡", "analyze_velocity"),
        ("👥", "get_similar_flagged_accounts"),
        ("🔒", "record_decision"),
    ]
    for icon, name in tools:
        st.markdown(
            "<span class='tool-chip'>" + icon + " " + name + "</span>",
            unsafe_allow_html=True
        )

    if "last_debug" not in st.session_state:
        st.session_state.last_debug = {}

# ── Suggested prompts ─────────────────────────────────────────────────────────
SUGGESTIONS = [
    "Investigate ACC-00009",
    "Why is ACC-00043 flagged?",
    "Is ACC-00054 safe to clear?",
    "Block ACC-00009 and explain why",
    "Are there coordinated attacks in the dataset?",
]

if not st.session_state.messages and st.session_state.pending_input is None:
    st.markdown("""
    <div class="empty-state">
      <div class="icon">🛡️</div>
      Ask the fraud agent to investigate an account, explain a flag, or recommend an action.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="suggestion-row">', unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTIONS))
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i]:
            if st.button(suggestion, key="sug_" + str(i), use_container_width=True):
                # Store as pending — don't append yet, let the agent block handle it
                st.session_state.pending_input = suggestion
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────────
langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])
            st.caption(
                f"Traced in [Langfuse]({langfuse_host})"
                f" · session: {st.session_state.session_id[:12]}..."
            )

# ── Pipeline debug panel ──────────────────────────────────────────────────────
if st.session_state.get("last_debug"):
    debug = st.session_state.last_debug
    with st.expander("🔬 Pipeline Debug — last run", expanded=False):
        gt = debug.get("ground_truth", "")
        if gt:
            if "DISCREPANCIES" in gt:
                st.error(gt)
            else:
                st.success(gt)
        t1, t2, t3 = st.tabs(["Data Agent", "Audit Agent", "Synthesis Input"])
        with t1:
            st.code(debug.get("data_agent", "—"), language=None)
        with t2:
            st.markdown(debug.get("audit_agent", "—"))
        with t3:
            st.caption("What the Synthesis Agent received")
            da = debug.get("data_agent", "")
            aa = debug.get("audit_agent", "")
            st.code(da, language=None)
            st.divider()
            st.markdown(aa)

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask the agent to investigate an account...")

# Resolve what to send: typed input takes priority, then pending suggestion
to_send = user_input or st.session_state.pending_input

if to_send:
    # Clear pending so it doesn't re-fire on the next rerun
    st.session_state.pending_input = None

    # Append user message and rerun immediately so the bubble renders first
    if not st.session_state.messages or st.session_state.messages[-1]["content"] != to_send:
        st.session_state.messages.append({"role": "user", "content": to_send})
        st.session_state._run_agent_for = to_send
        st.rerun()

# After the rerun, the user bubble is visible — now run the agent
if hasattr(st.session_state, "_run_agent_for") and st.session_state._run_agent_for:
    prompt = st.session_state._run_agent_for
    st.session_state._run_agent_for = None

    with st.spinner("Running investigation pipeline..."):
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
            from agent import run_agent
            response, updated_messages, debug = run_agent(
                messages=st.session_state.messages,
                session_id=st.session_state.session_id,
                analyst=st.session_state.analyst or "analyst",
            )
            st.session_state.messages = updated_messages
            st.session_state.last_debug = debug
            pipeline_ph.empty()
        except Exception as e:
            pipeline_ph.empty()
            st.session_state.messages.append({"role": "assistant", "content": f"Agent error: {e}"})

    st.rerun()
