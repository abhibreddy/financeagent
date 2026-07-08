"""
_suite_page.py — shared renderers for the Finance AI Suite pages.

Every page under modules/finance_suite/pages/<key>.py is a thin st.Page script that
calls render_report_agent(key) or render_chat(key). Session state is namespaced by
agent key so the six pages keep independent chat histories and scenario selections.
Mirrors modules/finance/pages/agent_chat.py (header, suggestions, chat loop, pipeline
debug expander) but drives the shared engine.run_suite_agent instead of run_agent.
"""

import os
import uuid

import pandas as pd
import streamlit as st

from modules.finance_suite.specs import SUITE
from modules.finance_suite.scenarios import list_scenarios, load_scenario
from modules.finance_suite.data import build_report
from modules.finance_suite.engine import run_suite_agent

# Report fields that are nested dicts — rendered as small tables, not st.metric.
_TABLE_FIELDS = ("aging", "dunning_priority", "breaks_by_type")


def _ns(key: str, name: str) -> str:
    """Namespace a session-state key by agent so pages don't share state."""
    return f"suite_{key}_{name}"


def _init_state(key: str) -> None:
    defaults = {
        _ns(key, "messages"): [],
        _ns(key, "session_id"): str(uuid.uuid4()),
        _ns(key, "analyst"): "analyst",
        _ns(key, "pending_input"): None,
        _ns(key, "last_debug"): {},
        _ns(key, "run_for"): None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _header(spec) -> None:
    st.markdown(f"""
    <div class="fd-header">
      <div class="fd-icon">{spec.icon}</div>
      <div>
        <div class="fd-title">{spec.title}</div>
        <div class="fd-sub">{spec.subtitle}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _money(v) -> str:
    """Format a scalar as currency when it looks like an amount, else plain."""
    return f"${v:,.2f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def _render_metrics(report: dict) -> None:
    """Scalar fields as st.metric in rows of 4; nested dicts as st.table below."""
    scalars = {k: v for k, v in report.items() if k not in _TABLE_FIELDS and not isinstance(v, dict)}
    tables = {k: v for k, v in report.items() if k in _TABLE_FIELDS and isinstance(v, dict)}

    items = list(scalars.items())
    for start in range(0, len(items), 4):
        row = items[start:start + 4]
        cols = st.columns(4)
        for col, (field, value) in zip(cols, row):
            label = field.replace("_", " ").title()
            # Amount-like fields get currency formatting; counts/pcts/bools stay plain.
            if any(t in field for t in ("amount", "cash", "outstanding", "receivable", "inflow", "outflow", "savings")):
                display = _money(value)
            elif "pct" in field:
                display = f"{value}%"
            else:
                display = str(value)
            col.metric(label, display)

    for field, mapping in tables.items():
        st.markdown(f'<div class="sec-label">{field.replace("_", " ").title()}</div>', unsafe_allow_html=True)
        if mapping:
            df = pd.DataFrame({"Key": list(mapping.keys()), "Value": list(mapping.values())})
            st.table(df)
        else:
            st.caption("None.")


def _pipeline_debug(key: str) -> None:
    debug = st.session_state.get(_ns(key, "last_debug"))
    if not debug:
        return
    with st.expander("🔬 Pipeline Debug — last run", expanded=False):
        gt = debug.get("ground_truth", "")
        if gt:
            if "DISCREPANC" in gt:
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
            st.code(debug.get("data_agent", ""), language=None)
            st.divider()
            st.markdown(debug.get("audit_agent", ""))


def _chat(key: str, scenario_id: str | None) -> None:
    """The chat loop, cloned from agent_chat.py and pointed at run_suite_agent."""
    spec = SUITE[key]
    langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    msgs_key = _ns(key, "messages")
    pending_key = _ns(key, "pending_input")
    run_key = _ns(key, "run_for")

    # ── Sidebar controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sb-section-label">Session</div>', unsafe_allow_html=True)
        analyst = st.text_input("Analyst name", value=st.session_state[_ns(key, "analyst")],
                                placeholder="Your name", key=_ns(key, "analyst_input"))
        if analyst:
            st.session_state[_ns(key, "analyst")] = analyst

        st.divider()
        st.markdown("**Session ID**")
        st.code(st.session_state[_ns(key, "session_id")][:18] + "...", language=None)
        st.markdown("**[Open Langfuse →](" + langfuse_host + ")**")

        st.divider()
        if st.button("🗑 Clear conversation", width="stretch", key=_ns(key, "clear")):
            st.session_state[msgs_key] = []
            st.session_state[pending_key] = None
            st.session_state[run_key] = None
            st.session_state[_ns(key, "session_id")] = str(uuid.uuid4())
            st.rerun()

    # ── Suggested prompts ─────────────────────────────────────────────────────
    if not st.session_state[msgs_key] and st.session_state[pending_key] is None:
        st.markdown(f"""
        <div class="empty-state">
          <div class="icon">{spec.icon}</div>
          Ask the {spec.title} about this scenario, or pick a starter below.
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="suggestion-row">', unsafe_allow_html=True)
        cols = st.columns(len(spec.suggestions))
        for i, suggestion in enumerate(spec.suggestions):
            with cols[i]:
                if st.button(suggestion, key=_ns(key, f"sug_{i}"), width="stretch"):
                    st.session_state[pending_key] = suggestion
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state[msgs_key]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar=spec.icon):
                st.markdown(msg["content"])
                st.caption(
                    f"Traced in [Langfuse]({langfuse_host})"
                    f" · session: {st.session_state[_ns(key, 'session_id')][:12]}..."
                )

    _pipeline_debug(key)

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input(f"Ask the {spec.title}...", key=_ns(key, "input"))
    to_send = user_input or st.session_state[pending_key]

    if to_send:
        st.session_state[pending_key] = None
        if not st.session_state[msgs_key] or st.session_state[msgs_key][-1]["content"] != to_send:
            st.session_state[msgs_key].append({"role": "user", "content": to_send})
            st.session_state[run_key] = to_send
            st.rerun()

    # After the rerun, the user bubble is visible — now run the agent.
    if st.session_state[run_key]:
        st.session_state[run_key] = None
        with st.spinner("Running pipeline..."):
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
                final, updated_messages, debug = run_suite_agent(
                    key,
                    messages=st.session_state[msgs_key],
                    session_id=st.session_state[_ns(key, "session_id")],
                    analyst=st.session_state[_ns(key, "analyst")] or "analyst",
                    scenario=scenario_id,
                )
                st.session_state[msgs_key] = updated_messages
                st.session_state[_ns(key, "last_debug")] = debug
                pipeline_ph.empty()
            except Exception as e:
                pipeline_ph.empty()
                st.session_state[msgs_key].append({"role": "assistant", "content": f"Agent error: {e}"})
        st.rerun()


def render_report_agent(key: str) -> None:
    """Full page for a report agent: header, scenario picker, metrics, then chat."""
    _init_state(key)
    spec = SUITE[key]
    _header(spec)

    scenarios = list_scenarios(key)
    scenario_id = None
    if scenarios:
        label_to_id = {s["name"]: s["id"] for s in scenarios}
        picked = st.selectbox("Scenario", list(label_to_id.keys()), key=_ns(key, "scenario"))
        scenario_id = label_to_id[picked]

        sc = load_scenario(key, scenario_id)
        if sc.get("description"):
            st.caption(sc["description"])

        st.markdown('<div class="sec-label">Report</div>', unsafe_allow_html=True)
        report = build_report(key, sc)
        _render_metrics(report)
    else:
        st.info("No scenarios available for this agent.")

    st.divider()
    _chat(key, scenario_id)


def render_chat_agent(key: str) -> None:
    """Full page for a chat-only agent (Copilot): header then chat, no scenario."""
    _init_state(key)
    _header(SUITE[key])
    _chat(key, None)
