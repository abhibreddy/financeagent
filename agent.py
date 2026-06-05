"""
agent.py — 3-stage multi-agent pipeline for velocity fraud detection.

Stage 1 — DataAgent:   Calls tools to collect raw account/transaction facts (has tools).
Stage 2 — AuditAgent:  Reviews findings for consistency and flags false positives (no tools).
Stage 3 — SynthAgent:  Produces concise analyst-ready summary (no tools).
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
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

# ── Data helpers ──────────────────────────────────────────────────────────────
_txns     = None
_accounts = None

def _load():
    global _txns, _accounts
    if _txns is None:
        _txns     = pd.read_csv("synthetictables/transactions.csv", parse_dates=["timestamp"])
        _accounts = pd.read_csv("synthetictables/accounts.csv")


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def lookup_account(account_id: str) -> str:
    """
    Look up a customer account by ID.
    Returns account details: name, type, home city, KYC status, dormancy, risk tier.
    Use this first when investigating any account.
    """
    _load()
    acc = _accounts[_accounts["account_id"] == account_id.upper()]
    if acc.empty:
        return f"Account {account_id} not found."
    row = acc.iloc[0]
    return json.dumps({
        "account_id":   row["account_id"],
        "customer":     row["customer_name"],
        "account_type": row["account_type"],
        "home_city":    row["home_city"],
        "risk_tier":    row["risk_tier"],
        "kyc_verified": bool(row["kyc_verified"]),
        "is_dormant":   bool(row["is_dormant"]),
        "dormant_days": int(row["dormant_days"]),
        "open_date":    row["open_date"],
    })


@tool
def get_transaction_history(account_id: str, limit: int = 20) -> str:
    """
    Get the most recent transactions for an account.
    Returns timestamp, amount, type, city, status, and fraud flags.
    Use this to understand the pattern of activity on an account.
    """
    _load()
    txns = (
        _txns[_txns["account_id"] == account_id.upper()]
        .sort_values("timestamp", ascending=False)
        .head(limit)
    )
    if txns.empty:
        return f"No transactions found for {account_id}."

    records = []
    for _, row in txns.iterrows():
        records.append({
            "timestamp":     row["timestamp"].strftime("%Y-%m-%d %H:%M"),
            "amount":        round(float(row["amount"]), 2),
            "type":          row["txn_type"],
            "city":          row["city"],
            "merchant":      row["merchant"],
            "status":        row["status"],
            "velocity_flag": bool(row["velocity_flag"]),
            "geo_flag":      bool(row["geo_flag"]),
            "fraud_type":    row["fraud_type"] if pd.notna(row["fraud_type"]) else None,
        })
    return json.dumps(records)


@tool
def analyze_velocity(account_id: str) -> str:
    """
    Compute transaction velocity analysis for an account.
    Returns max transactions in any 5-minute window, geo anomaly count,
    peak window timestamps, detected fraud types, and risk level.
    Use this to assess whether velocity-based fraud is occurring.
    """
    _load()
    from utils import compute_velocity
    acc_txns = _txns[_txns["account_id"] == account_id.upper()].copy()
    if acc_txns.empty:
        return f"No transactions found for {account_id}."

    v = compute_velocity(acc_txns)
    peak_start, peak_end = v["peak_window"]

    return json.dumps({
        "account_id":   account_id.upper(),
        "max_velocity": v["max_velocity"],
        "threshold":    5,
        "geo_flags":    v["geo_flags"],
        "total_amount": v["total_amount"],
        "total_txns":   len(acc_txns),
        "fraud_types":  v["fraud_types"],
        "risk_level":   v["risk_level"],
        "risk_score":   v["risk_score"],
        "peak_window": {
            "start": peak_start.strftime("%Y-%m-%d %H:%M") if peak_start else None,
            "end":   peak_end.strftime("%Y-%m-%d %H:%M")   if peak_end   else None,
        },
    })


@tool
def get_similar_flagged_accounts(account_id: str) -> str:
    """
    Find other accounts that had fraud activity at the same time or in the same
    cities as the given account. Useful for spotting coordinated attacks.
    """
    _load()
    target_txns = _txns[_txns["account_id"] == account_id.upper()]
    if target_txns.empty:
        return "No transactions found for comparison."

    flagged = target_txns[target_txns["velocity_flag"] | target_txns["geo_flag"]]
    if flagged.empty:
        return "No flagged transactions on this account to compare against."

    flag_time_start = flagged["timestamp"].min()
    flag_time_end   = flagged["timestamp"].max()
    flag_cities     = set(flagged["city"].tolist())

    window_txns = _txns[
        (_txns["timestamp"] >= flag_time_start) &
        (_txns["timestamp"] <= flag_time_end) &
        (_txns["account_id"] != account_id.upper()) &
        (_txns["is_fraud"] == True)
    ]

    similar = (
        window_txns.groupby("account_id")
        .agg(fraud_txns=("is_fraud", "sum"), cities=("city", lambda x: list(x.unique())))
        .reset_index()
        .head(5)
    )

    if similar.empty:
        return "No similar flagged accounts found in the same time window."

    results = []
    for _, row in similar.iterrows():
        overlap = flag_cities.intersection(set(row["cities"]))
        results.append({
            "account_id":   row["account_id"],
            "fraud_txns":   int(row["fraud_txns"]),
            "cities":       row["cities"],
            "city_overlap": list(overlap),
        })
    return json.dumps(results)


@tool
def record_decision(account_id: str, decision: str, notes: str = "") -> str:
    """
    Record an analyst decision for an account.
    decision must be one of: blocked, cleared, escalated, monitoring.
    Use this when the user asks to block, clear, escalate, or monitor an account.
    """
    valid = {"blocked", "cleared", "escalated", "monitoring"}
    if decision.lower() not in valid:
        return f"Invalid decision '{decision}'. Must be one of: {', '.join(valid)}."
    from utils import save_decision
    save_decision(account_id.upper(), decision.lower(), "agent", notes)
    return f"Decision recorded: {account_id.upper()} → {decision.lower()}. Notes: {notes or 'none'}"


# ── Agent state ───────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


TOOLS = [
    lookup_account,
    get_transaction_history,
    analyze_velocity,
    get_similar_flagged_accounts,
    record_decision,
]

# ── System prompts ────────────────────────────────────────────────────────────
DATA_AGENT_PROMPT = """You are the Data Collection Agent for FraudGuard.

Call tools to collect facts. Do NOT reason, interpret, or summarize.
For any account investigation:
1. lookup_account
2. analyze_velocity
3. get_transaction_history
4. If risk is High: get_similar_flagged_accounts
5. If user requests a decision: record_decision

After tool calls, output ONLY the raw data as collected — no interpretation."""

AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard.

You receive raw data from the Data Agent. Your job:
1. Verify every claim is supported by the actual data (no hallucinated numbers)
2. Check velocity counts match the transaction history
3. Confirm geo flags correspond to actual city mismatches
4. Rate each finding: Confirmed / Uncertain / Likely False Positive
5. Note any data gaps that should affect the final recommendation

Be skeptical. If a number doesn't add up, flag it."""

SYNTH_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard.

You receive data findings + an audit review. Produce a concise analyst summary:

## Fraud Investigation: [Account ID]

**Risk Level:** [High / Medium / Low]
**Recommendation:** [Block / Clear / Escalate / Monitor]

**Key Evidence:**
- [Confirmed finding with specific numbers]

**Caveats:** [Anything the Audit Agent flagged as uncertain]

Be direct. Only cite numbers that appear in the actual data."""


# ── Agent builders ────────────────────────────────────────────────────────────
def _build_data_agent():
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen3.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    ).bind_tools(TOOLS)
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
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen3.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )

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


# ── Public run function ───────────────────────────────────────────────────────
def run_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple:
    """
    Run the 3-stage fraud detection pipeline: Data → Audit → Synthesis.
    Returns (final_response, updated_messages).
    Traces each stage to Langfuse using the v4 context-manager API.
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.5")

    try:
        with langfuse.start_as_current_observation(
            name="fraud-agent-run",
            as_type="span",
            input=user_input,
            metadata={"session_id": session_id, "analyst": analyst},
        ):
            # Stage 1: Data collection (with tools)
            with langfuse.start_as_current_observation(
                name="data-agent",
                as_type="generation",
                model=model_name,
                input=user_input,
            ) as gen1:
                data_result = _build_data_agent().invoke({"messages": lc_messages})
                data_output = data_result["messages"][-1].content
                gen1.update(output=data_output)

            # Stage 2: Audit review
            with langfuse.start_as_current_observation(
                name="audit-agent",
                as_type="generation",
                model=model_name,
                input=data_output,
            ) as gen2:
                audit_result = _build_reasoning_agent(AUDIT_AGENT_PROMPT).invoke({
                    "messages": [HumanMessage(content=f"Data Agent output:\n\n{data_output}")]
                })
                audit_output = audit_result["messages"][-1].content
                gen2.update(output=audit_output)

            # Stage 3: Synthesis
            with langfuse.start_as_current_observation(
                name="synthesis-agent",
                as_type="generation",
                model=model_name,
                input=audit_output,
            ) as gen3:
                synth_result = _build_reasoning_agent(SYNTH_AGENT_PROMPT).invoke({
                    "messages": [HumanMessage(content=(
                        f"Original request: {user_input}\n\n"
                        f"Data findings:\n{data_output}\n\n"
                        f"Audit review:\n{audit_output}"
                    ))]
                })
                final = synth_result["messages"][-1].content
                gen3.update(output=final)

            langfuse.set_current_trace_io(input=user_input, output=final)

    except Exception:
        raise
    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}]
