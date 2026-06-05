"""
pages/2_Agent_Chat.py
Conversational fraud investigation chat powered by LangGraph + Ollama + Langfuse.
"""

import streamlit as st
import uuid
import os
from dotenv import load_dotenv

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
    <div class="fd-sub">Fraud Investigation · qwen2.5 via Ollama · Traced by Langfuse</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ FraudGuard")
    st.caption("Fraud Detection Platform")
    st.divider()
    st.page_link("account_lookup.py",        label="🔍 Account Lookup")
    st.page_link("pages/alert_queue.py",     label="🚨 Alert Queue")
    st.page_link("pages/2_Agent_Chat.py",    label="🤖 Agent Chat")
    st.page_link("pages/3_Invoice_Fraud.py", label="🧾 Invoice Fraud")
    st.divider()
    st.markdown("### 🤖 Agent Session")
    st.divider()

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
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            "<div class='chat-label chat-label-right'>You</div>"
            "<div class='chat-bubble chat-user'>" + msg["content"] + "</div>",
            unsafe_allow_html=True
        )
    else:
        content = msg["content"].replace("\n", "<br>")
        st.markdown(
            "<div class='chat-label'>🤖 FraudGuard Agent</div>"
            "<div class='chat-bubble chat-agent'>" + content + "</div>",
            unsafe_allow_html=True
        )
        langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        st.markdown(
            "<div class='langfuse-link'>Traced in "
            "<a href='" + langfuse_host + "' target='_blank'>Langfuse</a>"
            " · session: " + st.session_state.session_id[:12] + "..."
            "</div>",
            unsafe_allow_html=True
        )

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
            response, updated_messages = run_agent(
                messages=st.session_state.messages,
                session_id=st.session_state.session_id,
                analyst=st.session_state.analyst or "analyst",
            )
            st.session_state.messages = updated_messages
            pipeline_ph.empty()
        except Exception as e:
            pipeline_ph.empty()
            error_msg = (
                "Agent error: " + str(e) +
                ". Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull qwen2.5`)."
            )
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()
