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

# ── Extra chat-specific styles ────────────────────────────────────────────────
st.markdown("""
<style>
.chat-bubble {
    padding: 12px 16px; border-radius: 10px; font-size: 13px;
    line-height: 1.7; margin-bottom: 8px; max-width: 88%;
}
.chat-user {
    background: #1f2d3d; border: 1px solid #1a3a5c;
    color: #79c0ff; margin-left: auto; text-align: right;
}
.chat-agent {
    background: #161b22; border: 1px solid #21262d; color: #e6edf3;
}
.chat-label {
    font-size: 10px; color: #7d8590; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 4px;
}
.chat-label-right { text-align: right; }
.tool-chip {
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 10px; font-weight: 600; margin: 2px;
    background: #0d1f38; color: #58a6ff; border: 1px solid #1a3a5c;
}
.langfuse-link {
    font-size: 11px; color: #7d8590; text-align: right;
    padding: 4px 0 12px;
}
.langfuse-link a { color: #58a6ff; text-decoration: none; }
.langfuse-link a:hover { text-decoration: underline; }
.suggestion-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 1rem; }
.empty-state {
    text-align: center; padding: 3rem 1rem; color: #7d8590; font-size: 13px;
}
.empty-state .icon { font-size: 40px; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "analyst" not in st.session_state:
    st.session_state.analyst = "analyst"

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

if not st.session_state.messages:
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
                st.session_state.messages.append({"role": "user", "content": suggestion})
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
        # Render agent response — preserve newlines as <br>
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

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Run agent
    with st.spinner("Agent is investigating..."):
        try:
            from agent import run_agent
            response, updated_messages = run_agent(
                messages=st.session_state.messages[:-1] + [{"role": "user", "content": user_input}],
                session_id=st.session_state.session_id,
                analyst=st.session_state.analyst or "analyst",
            )
            st.session_state.messages = updated_messages
        except Exception as e:
            error_msg = "Agent error: " + str(e) + ". Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull qwen2.5`)."
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()
