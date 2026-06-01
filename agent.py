"""
agent.py — LangGraph fraud detection agent
Ollama (qwen3.5) · LangGraph tools · Langfuse v2 observability (with latency tracking)
"""

import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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

SYSTEM_PROMPT = """You are FraudGuard, an expert fraud detection agent for a financial institution.

You have access to tools to investigate accounts suspected of transaction velocity fraud.

Your capabilities:
- Look up account details (lookup_account)
- Retrieve transaction history (get_transaction_history)
- Analyze velocity patterns (analyze_velocity)
- Find similar flagged accounts in the same time window (get_similar_flagged_accounts)
- Record analyst decisions: block, clear, escalate, monitor (record_decision)

When investigating an account:
1. Always start with lookup_account to get account context
2. Run analyze_velocity to get the risk assessment
3. Use get_transaction_history to review the actual transactions
4. If high risk, check get_similar_flagged_accounts for coordinated attacks
5. Provide a clear recommendation: block / clear / escalate / monitor
6. If the user confirms an action, call record_decision

Be concise, precise, and analytical. Always cite specific numbers (velocity count,
geo flags, amounts) when explaining your reasoning. If an account is high risk,
be direct about it."""


# ── Agent factory ─────────────────────────────────────────────────────────────
def _build_agent():
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen3.5"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    ).bind_tools(TOOLS)

    tool_node = ToolNode(TOOLS)

    def call_model(state: AgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


# ── Public run function ───────────────────────────────────────────────────────
def run_agent(
    messages: list,
    session_id: str,
    analyst: str = "analyst",
) -> tuple[str, list]:
    """
    Run the agent with a full message history.
    Returns (response_text, updated_messages).
    Traces each run to Langfuse v2 with session + user metadata.
    """
    # Convert stored dicts to LangChain message objects
    lc_messages = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    # Langfuse v2 SDK tracing
    trace = langfuse.trace(
        name="fraud-agent-run",
        session_id=session_id,
        user_id=analyst,
        input=messages[-1]["content"] if messages else "",
    )

    # generation span — start time is stamped here, end() stamps finish time
    # this is what gives Langfuse the latency = end - start measurement
    generation = trace.generation(
        name="langgraph-agent",
        model=os.getenv("OLLAMA_MODEL", "qwen3.5"),
        input=messages[-1]["content"] if messages else "",
    )

    try:
        agent    = _build_agent()
        result   = agent.invoke({"messages": lc_messages})
        response = result["messages"][-1].content
        generation.end(output=response)
        trace.update(output=response)
    except Exception as e:
        generation.end(output={"error": str(e)})
        trace.update(output={"error": str(e)})
        raise e
    finally:
        langfuse.flush()

    updated = messages + [{"role": "assistant", "content": response}]
    return response, updated