"""
invoice_agent.py — 3-stage multi-agent pipeline for invoice fraud detection.

Stage 1 — DataAgent:   Pulls invoice data and runs detection passes (has tools).
Stage 2 — AuditAgent:  Reviews findings for false positives (no tools).
Stage 3 — SynthAgent:  Produces analyst-ready summary (no tools).
"""
import os
import json
import pandas as pd
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from core.llm import make_azure_llm
from core.tracing import get_langfuse

langfuse = get_langfuse()


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_invoice_summary() -> str:
    """
    Load all invoices and return summary statistics:
    total count, total spend, vendor breakdown, date range.
    Call this first to understand the dataset scope.
    """
    from modules.finance.utils import load_invoices
    df = load_invoices()
    return json.dumps({
        "total_invoices": len(df),
        "total_amount":   round(float(df["amount"].sum()), 2),
        "date_range":     [str(df["date"].min().date()), str(df["date"].max().date())],
        "vendor_count":   int(df["vendor"].nunique()),
        "top_vendors":    df["vendor"].value_counts().head(5).to_dict(),
        "departments":    df["department"].value_counts().to_dict(),
    })


@tool
def find_duplicate_invoices() -> str:
    """
    Detect exact and near-duplicate invoices (same vendor + same/similar amount
    within a short date window). Returns flagged invoice pairs.
    """
    from modules.finance.utils import load_invoices, detect_exact_duplicates, detect_near_duplicates
    df = load_invoices()
    exact = detect_exact_duplicates(df)
    near  = detect_near_duplicates(df)
    return json.dumps({
        "exact_duplicates": exact[["invoice_id", "vendor", "amount", "date"]].assign(
            date=exact["date"].astype(str)).to_dict("records"),
        "near_duplicates":  near[["invoice_id", "vendor", "amount", "date"]].assign(
            date=near["date"].astype(str)).to_dict("records"),
        "total_duplicate_exposure": round(float(exact["amount"].sum()), 2),
    })


@tool
def find_split_billing() -> str:
    """
    Detect invoice splitting: a vendor submitting many small invoices in a short
    window to stay below the approval threshold.
    """
    from modules.finance.utils import load_invoices, detect_split_billing
    df = load_invoices()
    splits = detect_split_billing(df)
    if splits.empty:
        return json.dumps({"split_groups": [], "total_exposure": 0.0})
    groups = splits.groupby("vendor").agg(
        invoice_count=("invoice_id", "count"),
        total_amount=("amount", "sum"),
        date_range=("date", lambda x: [str(x.min().date()), str(x.max().date())]),
    ).reset_index()
    return json.dumps({
        "split_groups":   groups.to_dict("records"),
        "total_exposure": round(float(splits["amount"].sum()), 2),
    })


@tool
def find_threshold_avoidance() -> str:
    """
    Find invoices just below the $10,000 approval threshold.
    """
    from modules.finance.utils import load_invoices, detect_threshold_avoidance
    df = load_invoices()
    flagged = detect_threshold_avoidance(df)
    return json.dumps({
        "invoices":       flagged[["invoice_id", "vendor", "amount", "date"]].assign(
            date=flagged["date"].astype(str)).to_dict("records"),
        "unique_vendors": int(flagged["vendor"].nunique()),
        "total_exposure": round(float(flagged["amount"].sum()), 2),
    })


@tool
def find_ghost_vendors() -> str:
    """
    Identify vendors who appear in very few invoices — potential ghost/fictitious vendors.
    """
    from modules.finance.utils import load_invoices, detect_ghost_vendors
    df = load_invoices()
    ghosts = detect_ghost_vendors(df)
    return json.dumps({
        "ghost_vendors":  ghosts[["invoice_id", "vendor", "amount", "date"]].assign(
            date=ghosts["date"].astype(str)).to_dict("records"),
        "vendor_names":   ghosts["vendor"].unique().tolist(),
        "total_exposure": round(float(ghosts["amount"].sum()), 2),
    })


INVOICE_TOOLS = [
    get_invoice_summary,
    find_duplicate_invoices,
    find_split_billing,
    find_threshold_avoidance,
    find_ghost_vendors,
]


# ── Agent state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ── System prompts ────────────────────────────────────────────────────────────
DATA_AGENT_PROMPT = """You are the Data Collection Agent for FraudGuard Invoice Analysis.

Your ONLY job is to call tools and collect raw findings. Do not interpret or summarize.

For every invoice audit request:
1. Call get_invoice_summary to understand the dataset
2. Call find_duplicate_invoices
3. Call find_split_billing
4. Call find_threshold_avoidance
5. Call find_ghost_vendors

After all tool calls, output a JSON block with the raw tool results. Do not add commentary."""


AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard Invoice Analysis.

You receive raw data findings from the Data Agent. Your job is to:
1. Check each finding for logical consistency
2. Assign a confidence level (High / Medium / Low) to each fraud pattern found
3. Identify any findings that are likely false positives and explain why
4. Estimate total financial exposure

Output a structured audit review — be skeptical, precise, and cite specific invoice IDs."""


SYNTHESIS_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard Invoice Analysis.

You receive both raw data findings and an audit review. Produce a clear analyst summary:

## Invoice Fraud Analysis Summary

**Risk Level:** [High / Medium / Low]

**Key Findings:**
- [Bullet per confirmed fraud pattern with amounts]

**Confirmed Issues:**
[Specific invoice IDs and amounts for each pattern]

**Recommended Actions:**
1. [Action]
2. [Action]

**Financial Exposure:** $X across N invoices

Only include findings the Audit Agent rated as Medium or High confidence."""


# ── Agent builders ────────────────────────────────────────────────────────────
def _build_data_agent():
    llm = make_azure_llm().bind_tools(INVOICE_TOOLS)
    tool_node = ToolNode(INVOICE_TOOLS)

    def call_model(state):
        messages = [SystemMessage(content=DATA_AGENT_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        if not isinstance(response, BaseMessage):
            response = AIMessage(content=response.content)
        return {"messages": [response]}

    def should_continue(state):
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

    def call_model(state):
        response = llm.invoke([SystemMessage(content=system_prompt)] + state["messages"])
        if not isinstance(response, BaseMessage):
            response = AIMessage(content=response.content)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


# ── Public run function ───────────────────────────────────────────────────────
def run_invoice_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple:
    """
    Run the 3-stage invoice fraud pipeline.
    Returns (final_response, updated_messages).
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    trace = langfuse.trace(
        name="invoice-fraud-agent",
        input=user_input,
        session_id=session_id,
        user_id=analyst,
        metadata={"analyst": analyst},
    )

    try:
        # Stage 1: Data collection
        gen1 = trace.generation(name="data-agent", model=model_name, input=user_input)
        data_result = _build_data_agent().invoke({"messages": lc_messages})
        data_output = data_result["messages"][-1].content
        gen1.end(output=data_output)

        # Stage 2: Audit
        gen2 = trace.generation(name="audit-agent", model=model_name, input=data_output)
        audit_result = _build_reasoning_agent(AUDIT_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=f"Data Agent findings:\n\n{data_output}")]
        })
        audit_output = audit_result["messages"][-1].content
        gen2.end(output=audit_output)

        # Stage 3: Synthesis
        gen3 = trace.generation(name="synthesis-agent", model=model_name, input=audit_output)
        synth_result = _build_reasoning_agent(SYNTHESIS_AGENT_PROMPT).invoke({
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

    return final, messages + [{"role": "assistant", "content": final}]
