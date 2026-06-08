"""
pages/2_Agent_Chat.py
Conversational fraud investigation chat powered by LangGraph + Ollama + Langfuse.
"""

import streamlit as st
import uuid
import os
import json
import pandas as pd
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
.file-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 6px 12px;
    font-size: 11px; color: #8b949e; margin-bottom: 10px;
}
.file-badge .fname { color: #e6edf3; font-weight: 600; }
.file-badge .fmeta { color: #7d8590; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages"        not in st.session_state: st.session_state.messages        = []
if "session_id"      not in st.session_state: st.session_state.session_id      = str(uuid.uuid4())
if "analyst"         not in st.session_state: st.session_state.analyst         = "analyst"
if "pending_input"   not in st.session_state: st.session_state.pending_input   = None
if "uploaded_context" not in st.session_state: st.session_state.uploaded_context = None  # {name, content, meta}


# ── File parser ───────────────────────────────────────────────────────────────
def parse_upload(file) -> dict:
    """
    Parse an uploaded file into a plain-text context string the agent can read.
    Returns {"name": str, "content": str, "meta": str} or raises on failure.
    """
    name = file.name
    ext  = name.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        df      = pd.read_csv(file)
        rows, cols = df.shape
        preview = df.head(200).to_csv(index=False)
        content = f"CSV file with {rows} rows and {cols} columns.\n\n{preview}"
        meta    = f"{rows} rows · {cols} cols"

    elif ext == "json":
        raw  = json.load(file)
        text = json.dumps(raw, indent=2)
        # Truncate very large JSON
        if len(text) > 8000:
            text = text[:8000] + "\n... (truncated)"
        content = f"JSON file contents:\n\n{text}"
        meta    = f"{len(text)} chars"

    elif ext == "txt":
        text = file.read().decode("utf-8", errors="replace")
        if len(text) > 8000:
            text = text[:8000] + "\n... (truncated)"
        content = f"Text file contents:\n\n{text}"
        meta    = f"{len(text)} chars"

    else:
        raise ValueError(f"Unsupported file type: .{ext}. Please upload CSV, JSON, or TXT.")

    return {"name": name, "content": content, "meta": meta}


# ── Inject file context into a user message ───────────────────────────────────
def build_message_with_context(user_text: str) -> str:
    """
    If a file is loaded, prepend its contents to the user message so the
    agent receives it as part of the conversation turn.
    """
    if st.session_state.uploaded_context:
        ctx = st.session_state.uploaded_context
        return (
            f"I have uploaded a file called '{ctx['name']}'. "
            f"Here are its contents:\n\n"
            f"{ctx['content']}\n\n"
            f"---\n"
            f"My question: {user_text}"
        )
    return user_text


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

# ── Sidebar ───────────────────────────────────────────────────────────────────
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
    st.markdown("**[Open Langfuse →](" + langfuse_host + ")**")

    st.divider()

    # ── File upload ───────────────────────────────────────────────────────────
    st.markdown("**📎 Upload a file**")
    st.caption("CSV, JSON, or TXT — the agent will read its contents.")

    uploaded_file = st.file_uploader(
        "Upload file",
        type=["csv", "json", "txt"],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        # Only re-parse if it's a new file
        current_name = st.session_state.uploaded_context["name"] if st.session_state.uploaded_context else None
        if current_name != uploaded_file.name:
            try:
                parsed = parse_upload(uploaded_file)
                st.session_state.uploaded_context = parsed
                st.success(f"✅ Loaded **{parsed['name']}** ({parsed['meta']})")
            except ValueError as e:
                st.error(str(e))
                st.session_state.uploaded_context = None
    else:
        # File was removed from uploader
        st.session_state.uploaded_context = None

    # Show active file badge
    if st.session_state.uploaded_context:
        ctx = st.session_state.uploaded_context
        st.markdown(
            f"<div class='file-badge'>📄 "
            f"<span class='fname'>{ctx['name']}</span>"
            f"<span class='fmeta'>{ctx['meta']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("🗑 Remove file", use_container_width=True):
            st.session_state.uploaded_context = None
            st.rerun()

    st.divider()
    if st.button("🗑 Clear conversation", use_container_width=True):
        st.session_state.messages        = []
        st.session_state.pending_input   = None
        st.session_state.uploaded_context = None
        st.session_state.session_id      = str(uuid.uuid4())
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
            unsafe_allow_html=True,
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

    cols = st.columns(len(SUGGESTIONS))
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i]:
            if st.button(suggestion, key="sug_" + str(i), use_container_width=True):
                st.session_state.pending_input = suggestion
                st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        # Show the display_content if set (hides raw file dump), else show content
        display = msg.get("display_content", msg["content"])
        st.markdown(
            "<div class='chat-label chat-label-right'>You</div>"
            "<div class='chat-bubble chat-user'>" + display + "</div>",
            unsafe_allow_html=True,
        )
    else:
        content = msg["content"].replace("\n", "<br>")
        st.markdown(
            "<div class='chat-label'>🤖 FraudGuard Agent</div>"
            "<div class='chat-bubble chat-agent'>" + content + "</div>",
            unsafe_allow_html=True,
        )
        langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        st.markdown(
            "<div class='langfuse-link'>Traced in "
            "<a href='" + langfuse_host + "' target='_blank'>Langfuse</a>"
            " · session: " + st.session_state.session_id[:12] + "..."
            "</div>",
            unsafe_allow_html=True,
        )

# ── Active file indicator above chat input ────────────────────────────────────
if st.session_state.uploaded_context:
    ctx = st.session_state.uploaded_context
    st.markdown(
        f"<div class='file-badge'>📎 "
        f"<span class='fname'>{ctx['name']}</span> "
        f"<span class='fmeta'>will be sent with your next message</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask the agent to investigate an account...")

to_send = user_input or st.session_state.pending_input

if to_send:
    st.session_state.pending_input = None

    # Build the actual message sent to the agent (may include file context)
    agent_message = build_message_with_context(to_send)

    # Store both the full agent message and a clean display version
    last_content = st.session_state.messages[-1]["content"] if st.session_state.messages else None
    if last_content != agent_message:
        msg_entry = {"role": "user", "content": agent_message}

        # If file context was injected, store a clean label for the UI
        if st.session_state.uploaded_context:
            ctx = st.session_state.uploaded_context
            msg_entry["display_content"] = (
                f"📎 <em>{ctx['name']}</em><br>{to_send}"
            )

        st.session_state.messages.append(msg_entry)
        st.session_state._run_agent_for = agent_message

        # Clear file after sending so it doesn't re-attach on the next message
        st.session_state.uploaded_context = None
        st.rerun()

# After rerun — run the agent
if getattr(st.session_state, "_run_agent_for", None):
    st.session_state._run_agent_for = None

    with st.spinner("Agent is investigating..."):
        try:
            from agent import run_agent
            response, updated_messages = run_agent(
                messages=st.session_state.messages,
                session_id=st.session_state.session_id,
                analyst=st.session_state.analyst or "analyst",
            )
            st.session_state.messages = updated_messages
        except Exception as e:
            error_msg = (
                "Agent error: " + str(e) +
                ". Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull qwen2.5`)."
            )
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    st.rerun()