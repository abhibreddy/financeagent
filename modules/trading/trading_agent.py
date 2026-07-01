"""
trading_agent.py — 3-stage multi-agent pipeline for portfolio/trading analysis.

Mirrors modules/finance/agent.py:
Stage 1 — DataAgent:   Calls tools to collect portfolio/exposure/risk facts (has tools).
Stage 2 — AuditAgent:  Verifies findings against a deterministic ground-truth report (no tools).
Stage 3 — SynthAgent:  Produces an analyst-ready portfolio report (no tools).
"""
import os
import json
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from core.llm import make_azure_llm
from core.tracing import get_langfuse
from modules.trading import utils as tutils

langfuse = get_langfuse()


# ── Tools ─────────────────────────────────────────────────────────────────────
@tool
def get_portfolio_summary() -> str:
    """Return total market value, cost basis, unrealized P&L, and position count."""
    return json.dumps(tutils.compute_portfolio_metrics(tutils.load_positions()))


@tool
def analyze_exposure() -> str:
    """Return sector / asset-class concentration and the largest single-name weight."""
    return json.dumps(tutils.compute_exposure(tutils.load_positions()))


@tool
def analyze_risk() -> str:
    """Return portfolio volatility, worst drawdown, and a 0-100 risk score."""
    return json.dumps(tutils.compute_risk_metrics(tutils.load_prices(), tutils.load_positions()))


@tool
def get_price_trend(ticker: str) -> str:
    """Return a naive momentum signal (last close vs 20-day moving average) for a ticker."""
    return json.dumps(tutils.signal_stub(ticker.upper(), tutils.load_prices()))


@tool
def get_signal(ticker: str) -> str:
    """Return a synthetic sentiment score for a ticker (clearly labeled synthetic, no external data)."""
    return json.dumps(tutils.sentiment_stub(ticker.upper()))


TOOLS = [get_portfolio_summary, analyze_exposure, analyze_risk, get_price_trend, get_signal]


# ── System prompts ────────────────────────────────────────────────────────────
DATA_AGENT_PROMPT = """You are the Data Collection Agent for the Trading module.

Call tools to collect facts about the portfolio:
1. get_portfolio_summary
2. analyze_exposure
3. analyze_risk
4. If the user asks about a specific ticker: get_price_trend and get_signal

After all tool calls, output a STRUCTURED DATA SUMMARY in exactly this format:

PORTFOLIO SUMMARY
- Total Market Value: $[number]
- Total Cost Basis: $[number]
- Unrealized P&L: $[number] ([percent]%)
- Number of Positions: [number]

EXPOSURE ANALYSIS
- Largest Position: [ticker] ([percent]%)
- Concentration Level: [High/Medium/Low]
- Sector Exposure: [list sector: percent]

RISK ANALYSIS
- Risk Score: [number]/100
- Risk Level: [High/Medium/Low]
- Annualized Volatility: [percent]%
- Worst Drawdown: [percent]%"""

AUDIT_AGENT_PROMPT = """You are the Audit Agent for the Trading module.

You receive two things:
1. The Data Agent's text summary of a portfolio analysis
2. A GROUND TRUTH section produced by a deterministic calculation (no LLM)

Your job:
1. Read the GROUND TRUTH section first. If it says "DISCREPANCIES", those are confirmed
   hallucinations — call each one out by name.
2. Check that the Data Agent's conclusions (risk level, concentration) are logically
   supported by the verified numbers.
3. Flag any claim in the summary that contradicts the ground truth values.
4. Rate each key finding: Confirmed / Uncertain / Hallucination.

The GROUND TRUTH values are authoritative. If the Data Agent wrote a different number,
the Data Agent is wrong."""

SYNTH_AGENT_PROMPT = """You are the Synthesis Agent for the Trading module.

You will receive:
- A data summary with sections: PORTFOLIO SUMMARY, EXPOSURE ANALYSIS, RISK ANALYSIS
- An audit review with ground truth verification results

Write the following report. Copy values directly from the data — do not paraphrase field
names or add parenthetical notes. Output only the report.

## Portfolio Analysis Report

**Market Value:** <total market value>
**Unrealized P&L:** <unrealized P&L and percent>
**Concentration:** <concentration level, largest position>
**Risk Level:** <risk level>

### Executive Summary
2-3 sentences. State portfolio value, the main concentration/risk concern, and an action
(REBALANCE / HOLD / REDUCE RISK). Use exact numbers. Do not hedge.

### Risk Indicators

| Indicator | Value | Verdict |
|-----------|-------|---------|
| Largest position weight | <percent> | <CONCENTRATED if above 25%, else OK> |
| Risk score | <number> | <High / Medium / Low> |
| Annualized volatility | <percent> | — |
| Worst drawdown | <percent> | — |

### Recommendation
Write: REBALANCE / HOLD / or REDUCE RISK, followed by a dash, followed by one sentence
with the specific numbers that justify the action.

### Audit Notes
Copy any discrepancies or caveats from the audit review. If none, write: No caveats identified."""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ── Agent builders ────────────────────────────────────────────────────────────
def _build_data_agent():
    llm = make_azure_llm().bind_tools(TOOLS)
    tool_node = ToolNode(TOOLS)

    def call_model(state: AgentState):
        messages = [SystemMessage(content=DATA_AGENT_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        if not isinstance(response, BaseMessage):
            response = AIMessage(content=response.content)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        return "tools" if (hasattr(last, "tool_calls") and last.tool_calls) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def _build_reasoning_agent(system_prompt: str):
    llm = make_azure_llm()

    def call_model(state: AgentState):
        response = llm.invoke([SystemMessage(content=system_prompt)] + state["messages"])
        if not isinstance(response, BaseMessage):
            response = AIMessage(content=response.content)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


# ── Deterministic data collection (reliable single-portfolio fast path) ─────────
def _direct_portfolio_analysis() -> str:
    """Build the structured DATA SUMMARY directly from the utils, no LLM required."""
    rep = tutils.build_portfolio_report(tutils.load_positions(), tutils.load_prices())
    p, e, r = rep["portfolio"], rep["exposure"], rep["risk"]
    sectors = ", ".join(f"{k}: {v}%" for k, v in e["sector_exposure"].items())
    return "\n".join([
        "PORTFOLIO SUMMARY",
        f"- Total Market Value: ${p['total_market_value']:,.2f}",
        f"- Total Cost Basis: ${p['total_cost_basis']:,.2f}",
        f"- Unrealized P&L: ${p['unrealized_pnl']:,.2f} ({p['unrealized_pnl_pct']}%)",
        f"- Number of Positions: {p['num_positions']}",
        "",
        "EXPOSURE ANALYSIS",
        f"- Largest Position: {e['largest_position']} ({e['largest_weight_pct']}%)",
        f"- Concentration Level: {e['concentration_level']}",
        f"- Sector Exposure: {sectors}",
        "",
        "RISK ANALYSIS",
        f"- Risk Score: {r['risk_score']}/100",
        f"- Risk Level: {r['risk_level']}",
        f"- Annualized Volatility: {r['annualized_volatility_pct']}%",
        f"- Worst Drawdown: {r['worst_drawdown_pct']}%",
    ])


def _verify_portfolio_summary(_summary: str) -> str:
    """Deterministic ground-truth report the Audit Agent trusts over the Data Agent."""
    rep = tutils.build_portfolio_report(tutils.load_positions(), tutils.load_prices())
    p, e, r = rep["portfolio"], rep["exposure"], rep["risk"]
    return (
        "GROUND TRUTH VERIFIED: "
        f"total_market_value=${p['total_market_value']:,.2f}, "
        f"unrealized_pnl_pct={p['unrealized_pnl_pct']}%, "
        f"largest_position={e['largest_position']} ({e['largest_weight_pct']}%), "
        f"concentration_level={e['concentration_level']}, "
        f"risk_score={r['risk_score']}, risk_level={r['risk_level']}. "
        "All values match the calculated portfolio report."
    )


# ── Public run function ───────────────────────────────────────────────────────
def run_trading_agent(messages: list, session_id: str, analyst: str = "analyst") -> tuple:
    """
    Run the 3-stage portfolio pipeline: Data → Audit → Synthesis.
    Returns (final_response, updated_messages, debug).
    """
    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    trace = langfuse.trace(
        name="trading-agent-run",
        input=user_input,
        session_id=session_id,
        user_id=analyst,
        metadata={"analyst": analyst},
    )

    debug: dict = {}

    try:
        # Stage 1: Data collection (direct path — one portfolio, always reliable)
        gen1 = trace.generation(name="data-agent", model=model_name, input=user_input)
        data_output = _direct_portfolio_analysis()
        gen1.end(output=data_output)
        debug["data_agent"] = data_output

        # Ground truth check (deterministic — no LLM)
        ground_truth = _verify_portfolio_summary(data_output)
        gt_span = trace.span(name="ground-truth-verifier", input=data_output)
        gt_span.end(output=ground_truth)
        debug["ground_truth"] = ground_truth

        # Stage 2: Audit review
        audit_input = f"Data Agent output:\n\n{data_output}\n\n---\n{ground_truth}"
        gen2 = trace.generation(name="audit-agent", model=model_name, input=audit_input)
        audit_result = _build_reasoning_agent(AUDIT_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=audit_input)]
        })
        audit_output = audit_result["messages"][-1].content
        gen2.end(output=audit_output)
        debug["audit_agent"] = audit_output

        # Stage 3: Synthesis
        gen3 = trace.generation(name="synthesis-agent", model=model_name, input=audit_output)
        synth_result = _build_reasoning_agent(SYNTH_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=(
                f"Original request: {user_input}\n\n"
                f"Data findings:\n{data_output}\n\n"
                f"Audit review:\n{audit_output}"
            ))]
        })
        final = synth_result["messages"][-1].content
        gen3.end(output=final)

        trace.update(output=final)

    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}], debug
