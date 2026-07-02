"""
alert_queue_agent.py — 3-stage multi-agent pipeline for alert queue analysis.

Stage 1 — DataAgent:   Calls tools to collect current alert state + decisions (has tools).
Stage 2 — AuditAgent:  Reviews findings and identifies patterns (no tools).
Stage 3 — SynthAgent:  Produces analyst-ready alert summary (no tools).
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langfuse import Langfuse

load_dotenv()

# ── Langfuse client ───────────────────────────────────────────────────────────
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_alert_context() -> str:
    """
    Get overview of current alert queue state:
    total accounts, flagged count, pending review count,
    and top 3 high-risk accounts for immediate action.
    """
    from utils import load_data, build_alert_queue, get_decisions
    txns, accounts = load_data()
    queue = build_alert_queue(txns, accounts)
    decisions = get_decisions()
    
    pending_ids = set(queue["account_id"]) - set(decisions.keys())
    high_risk = queue[queue["risk_level"] == "High"].head(3)
    medium_risk = queue[queue["risk_level"] == "Medium"].head(3)
    
    high_risk_records = []
    for _, row in high_risk.iterrows():
        high_risk_records.append({
            "account_id": row["account_id"],
            "customer": row["customer"],
            "risk_score": row["risk_score"],
            "max_velocity": row["max_velocity"],
            "geo_flags": row["geo_flags"],
        })
    
    return json.dumps({
        "total_accounts": len(accounts),
        "flagged_count": len(queue),
        "pending_count": len(pending_ids),
        "high_risk_count": len(queue[queue["risk_level"] == "High"]),
        "medium_risk_count": len(queue[queue["risk_level"] == "Medium"]),
        "high_risk_top_3": high_risk_records,
    })


@tool
def get_current_alerts() -> str:
    """
    Get all high + medium risk flagged accounts ranked by risk score.
    Returns top 10 accounts with key metrics.
    """
    from utils import load_data, build_alert_queue
    txns, accounts = load_data()
    queue = build_alert_queue(txns, accounts)
    
    records = []
    for _, row in queue.head(10).iterrows():
        records.append({
            "account_id": row["account_id"],
            "customer": row["customer"],
            "account_type": row["account_type"],
            "home_city": row["home_city"],
            "risk_level": row["risk_level"],
            "risk_score": row["risk_score"],
            "max_velocity": row["max_velocity"],
            "geo_flags": row["geo_flags"],
            "total_amount": round(row["total_amount"], 2),
            "fraud_types": row["fraud_types"],
        })
    
    return json.dumps({
        "total_flagged": len(queue),
        "high_risk_count": len(queue[queue["risk_level"] == "High"]),
        "medium_risk_count": len(queue[queue["risk_level"] == "Medium"]),
        "top_10_accounts": records,
    })


@tool
def get_decision_summary() -> str:
    """
    Get summary of analyst decisions:
    blocked, cleared, escalated, monitoring counts.
    """
    from utils import get_decisions
    decisions = get_decisions()
    
    blocked = sum(1 for d in decisions.values() if d["decision"] == "blocked")
    cleared = sum(1 for d in decisions.values() if d["decision"] == "cleared")
    escalated = sum(1 for d in decisions.values() if d["decision"] == "escalated")
    monitoring = sum(1 for d in decisions.values() if d["decision"] == "monitoring")
    
    return json.dumps({
        "blocked": blocked,
        "cleared": cleared,
        "escalated": escalated,
        "monitoring": monitoring,
        "total_decided": len(decisions),
    })


# ── Agent state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


ALERT_TOOLS = [
    get_alert_context,
    get_current_alerts,
    get_decision_summary,
]


# ── System prompts ────────────────────────────────────────────────────────────
ALERT_DATA_AGENT_PROMPT = """You are the Alert Queue Agent for FraudGuard.

Your job is to call tools to collect current alert state and findings.

For any alert-related question:
1. Call get_alert_context to understand the current state
2. Call get_current_alerts to see the top flagged accounts
3. Call get_decision_summary to see what decisions have been made

After all tool calls, output a STRUCTURED ALERT SUMMARY in this format:

ALERT QUEUE STATE
- Total Accounts: [number]
- Flagged Accounts: [number]
- Pending Review: [number]
- High Risk: [number]
- Medium Risk: [number]

TOP PRIORITIES
[List each as: account_id | customer | risk_score | max_velocity txns/5min | geo flags]

ANALYST ACTIONS
- Blocked: [number]
- Cleared: [number]
- Escalated: [number]
- Monitoring: [number]
- Total Decided: [number]

TOP 10 FLAGGED ACCOUNTS
[List each as: account_id | customer | risk_level | risk_score | fraud_types]"""


ALERT_AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard Alert Queue.

You receive a summary of current alerts and analyst decisions. Your job is to:
1. Verify the numbers are internally consistent
2. Identify any concerning patterns (e.g., many high-risk accounts from same city)
3. Spot accounts that should be prioritized for investigation
4. Assess whether the pending review queue is manageable

Output a structured audit review with observations and recommendations."""


ALERT_SYNTHESIS_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard Alert Queue.

You receive alert findings and an audit review. Produce a clear analyst summary:

## Alert Queue Status Report

**Current State:**
- Total Flagged: [number]
- Pending Review: [number]
- High Risk: [number]

**Key Insights:**
- [Insight 1]
- [Insight 2]
- [Insight 3]

**Top Priorities (Next 3 to investigate):**
1. [Account ID – reason]
2. [Account ID – reason]
3. [Account ID – reason]

**Analyst Progress:**
- Blocked: X accounts
- Cleared: X accounts
- Escalated: X accounts
- Monitoring: X accounts

**Recommendation:**
[Action or observation]"""


# ── Agent builders ────────────────────────────────────────────────────────────
def _build_alert_data_agent():
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        temperature=0,
    ).bind_tools(ALERT_TOOLS)
    tool_node = ToolNode(ALERT_TOOLS)

    def call_model(state):
        messages = [SystemMessage(content=ALERT_DATA_AGENT_PROMPT)] + state["messages"]
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
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        temperature=0,
    )

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
def run_alert_queue_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple:
    """
    Run the 3-stage alert queue analysis pipeline: Data → Audit → Synthesis.
    Returns (final_response, updated_messages, debug).
    Traces each stage to Langfuse.
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

    trace = langfuse.trace(
        name="alert-queue-agent-run",
        input=user_input,
        session_id=session_id,
        user_id=analyst,
        metadata={"analyst": analyst},
    )

    debug: dict = {}

    try:
        # Stage 1: Data collection (tools)
        gen1 = trace.generation(name="alert-data-agent", model=model_name, input=user_input)
        data_result = _build_alert_data_agent().invoke({"messages": lc_messages})
        data_output = data_result["messages"][-1].content
        gen1.end(output=data_output)
        debug["data_agent"] = data_output

        # Stage 2: Audit review (no tools)
        audit_input = f"Alert findings:\n\n{data_output}"
        gen2 = trace.generation(name="alert-audit-agent", model=model_name, input=audit_input)
        audit_result = _build_reasoning_agent(ALERT_AUDIT_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=audit_input)]
        })
        audit_output = audit_result["messages"][-1].content
        gen2.end(output=audit_output)
        debug["audit_agent"] = audit_output

        # Stage 3: Synthesis
        gen3 = trace.generation(name="alert-synthesis-agent", model=model_name, input=audit_output)
        synth_result = _build_reasoning_agent(ALERT_SYNTHESIS_AGENT_PROMPT).invoke({
            "messages": [HumanMessage(content=(
                f"Original request: {user_input}\n\n"
                f"Alert findings:\n{data_output}\n\n"
                f"Audit review:\n{audit_output}"
            ))]
        })
        final = synth_result["messages"][-1].content
        gen3.end(output=final)

        trace.update(output=final)

    except Exception:
        raise
    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}], debug
