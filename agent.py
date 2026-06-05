"""
agent.py — 3-stage multi-agent pipeline for velocity fraud detection.

Stage 1 — DataAgent:   Calls tools to collect raw account/transaction facts (has tools).
Stage 2 — AuditAgent:  Reviews findings for consistency and flags false positives (no tools).
Stage 3 — SynthAgent:  Produces concise analyst-ready summary (no tools).
"""

import os
import re
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

Call tools to collect facts. For any account investigation:
1. lookup_account
2. analyze_velocity
3. get_transaction_history (limit 10)
4. If risk_level is High: get_similar_flagged_accounts
5. If user requests a decision: record_decision

After all tool calls, output a STRUCTURED DATA SUMMARY in exactly this format:

ACCOUNT SUMMARY
- Account ID: [value]
- Customer: [value]
- Account Type: [value]
- Home City: [value]
- KYC Verified: [Yes/No]
- Dormant: [Yes – X days / No]
- Risk Tier: [value]

VELOCITY ANALYSIS
- Max Velocity: [number] txns in a 5-min window
- Velocity Threshold: 5
- Risk Score: [number]/100
- Risk Level: [High/Medium/Low]
- Geo Anomaly Flags: [number]
- Total Transactions: [number]
- Total Amount: $[number]
- Peak Window: [start timestamp] – [end timestamp]
- Fraud Types Detected: [list or None]

RECENT TRANSACTIONS (last 10)
[List each as: timestamp | $amount | type | city | status | flags]"""

AUDIT_AGENT_PROMPT = """You are the Audit Agent for FraudGuard.

You receive two things:
1. The Data Agent's text summary of an account investigation
2. A GROUND TRUTH section produced by a deterministic database check (no LLM)

Your job:
1. Read the GROUND TRUTH section first. If it says "DISCREPANCIES", those are confirmed hallucinations — call each one out by name.
2. Check that the Data Agent's conclusions (risk level, recommendation) are logically supported by the verified numbers.
3. Flag any claim in the summary that contradicts the ground truth values.
4. Rate each key finding: Confirmed / Uncertain / Hallucination.
5. Note any data gaps that should affect the final recommendation.

The GROUND TRUTH values are authoritative. If the Data Agent wrote a different number, the Data Agent is wrong."""

SYNTH_AGENT_PROMPT = """You are the Synthesis Agent for FraudGuard, a financial fraud detection system.

You will receive:
- A data summary with sections: ACCOUNT SUMMARY, VELOCITY ANALYSIS, RECENT TRANSACTIONS
- An audit review with ground truth verification results

Write the following report. Copy values directly from the data — do not paraphrase field names, do not add parenthetical notes, do not explain where values came from.

Output only the report. Nothing before it, nothing after the final line of dashes.

---
## Fraud Investigation Report

**Account:** <account ID from ACCOUNT SUMMARY>
**Customer:** <customer name from ACCOUNT SUMMARY>
**Risk Level:** <risk level from VELOCITY ANALYSIS>
**Recommended Action:** <one of: BLOCK / ESCALATE / MONITOR / CLEAR>

---

### Executive Summary
Write 2-3 sentences. State the risk level, the primary reason, and the recommended action. Use exact numbers. Do not hedge.

### Risk Indicators

| Indicator | Value | Verdict |
|-----------|-------|---------|
| Max velocity (txns/5 min) | <Max Velocity number> | <BREACH if above 5, else Normal> |
| Velocity threshold | 5 | — |
| Geographic anomalies | <Geo Anomaly Flags number> | <FLAGGED if above 0, else None> |
| Account dormancy | <Dormant line from ACCOUNT SUMMARY> | <Risk factor if dormant, else Normal> |
| KYC verified | <KYC Verified value> | <Compliant if Yes, else At Risk> |
| Risk score | <Risk Score number> | <High / Medium / Low> |

### Evidence

Write one paragraph per confirmed finding. Each paragraph must name the finding, state what happened, and include at least one specific number (amount, count, timestamp, or city name) from the data.

### Recommendation
Write: BLOCK / ESCALATE / MONITOR / or CLEAR, followed by a dash, followed by one sentence with the specific numbers that justify the action.

### Audit Notes
Copy any discrepancies or caveats from the audit review. If none, write: No caveats identified.

---

Rules:
- Do NOT write parenthetical notes like "(from ACCOUNT SUMMARY)" or "(extracted from data)" in any field.
- Do NOT write "Not available" for any field that appears anywhere in the data.
- The velocity threshold is 5. Never use any other number.
- Stop writing after the final ---. No trailing notes or commentary."""


# ── Direct account investigation (no LLM for data collection) ────────────────
def _direct_account_investigation(account_id: str) -> str:
    """
    Call all investigation tools directly — bypasses LLM tool routing entirely.
    Returns the same structured summary format as _build_data_summary_from_messages.
    """
    acc_raw      = lookup_account.invoke({"account_id": account_id})
    velocity_raw = analyze_velocity.invoke({"account_id": account_id})
    txn_raw      = get_transaction_history.invoke({"account_id": account_id, "limit": 10})
    similar_raw  = None

    try:
        acc      = json.loads(acc_raw)
        vel      = json.loads(velocity_raw)
        txns     = json.loads(txn_raw) if not txn_raw.startswith("No transactions") else []
        risk_lvl = vel.get("risk_level", "Low")
        if risk_lvl == "High":
            similar_raw = get_similar_flagged_accounts.invoke({"account_id": account_id})
    except (json.JSONDecodeError, TypeError):
        return f"Tool error collecting data for {account_id}."

    dormant_str = (
        f"Yes – {int(acc.get('dormant_days', 0))} days"
        if acc.get("is_dormant") else "No"
    )
    peak = vel.get("peak_window") or {}
    peak_str = f"{peak.get('start', '—')} – {peak.get('end', '—')}"
    fraud_types = vel.get("fraud_types") or []

    lines = [
        "ACCOUNT SUMMARY",
        f"- Account ID: {acc.get('account_id', account_id)}",
        f"- Customer: {acc.get('customer', '—')}",
        f"- Account Type: {acc.get('account_type', '—')}",
        f"- Home City: {acc.get('home_city', '—')}",
        f"- KYC Verified: {'Yes' if acc.get('kyc_verified') else 'No'}",
        f"- Dormant: {dormant_str}",
        f"- Risk Tier: {acc.get('risk_tier', '—')}",
        "",
        "VELOCITY ANALYSIS",
        f"- Max Velocity: {vel.get('max_velocity', '—')} txns in a 5-min window",
        f"- Velocity Threshold: 5",
        f"- Risk Score: {vel.get('risk_score', '—')}/100",
        f"- Risk Level: {vel.get('risk_level', '—')}",
        f"- Geo Anomaly Flags: {vel.get('geo_flags', '—')}",
        f"- Total Transactions: {vel.get('total_txns', '—')}",
        f"- Total Amount: ${float(vel.get('total_amount', 0)):,.2f}",
        f"- Peak Window: {peak_str}",
        f"- Fraud Types Detected: {', '.join(fraud_types) if fraud_types else 'None'}",
    ]

    if txns:
        lines += ["", "RECENT TRANSACTIONS (last 10)"]
        for t in txns[:10]:
            flags = []
            if t.get("velocity_flag"):
                flags.append("VELOCITY")
            if t.get("geo_flag"):
                flags.append("GEO")
            flag_str = " | ".join(flags) if flags else "OK"
            lines.append(
                f"- {t.get('timestamp','—')} | ${float(t.get('amount',0)):,.2f} | "
                f"{t.get('type','—')} | {t.get('city','—')} | {t.get('status','—')} | {flag_str}"
            )

    if similar_raw and not similar_raw.startswith("No similar"):
        try:
            similar = json.loads(similar_raw)
            lines += ["", "SIMILAR FLAGGED ACCOUNTS"]
            for s in similar[:3]:
                lines.append(
                    f"- {s.get('account_id','—')}: {s.get('fraud_txns','—')} fraud txns, "
                    f"city overlap: {', '.join(s.get('city_overlap', [])) or 'none'}"
                )
        except (json.JSONDecodeError, TypeError):
            pass

    return "\n".join(lines)


# ── Tool output parser (no LLM) ──────────────────────────────────────────────
def _build_data_summary_from_messages(messages: list) -> str:
    """
    Parse ToolMessage results from the Data Agent's message history into a
    structured text summary. Deterministic — no LLM formatting required.
    """
    from langchain_core.messages import ToolMessage

    account_data: dict = {}
    velocity_data: dict = {}
    txn_data: list = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            content = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(content, dict):
            if "customer" in content and "account_id" in content:
                account_data = content
            elif "max_velocity" in content:
                velocity_data = content
        elif isinstance(content, list) and content and "timestamp" in content[0]:
            txn_data = content

    lines = ["ACCOUNT SUMMARY"]
    if account_data:
        dormant_str = (
            f"Yes – {int(account_data.get('dormant_days', 0))} days"
            if account_data.get("is_dormant") else "No"
        )
        lines += [
            f"- Account ID: {account_data.get('account_id', '—')}",
            f"- Customer: {account_data.get('customer', '—')}",
            f"- Account Type: {account_data.get('account_type', '—')}",
            f"- Home City: {account_data.get('home_city', '—')}",
            f"- KYC Verified: {'Yes' if account_data.get('kyc_verified') else 'No'}",
            f"- Dormant: {dormant_str}",
            f"- Risk Tier: {account_data.get('risk_tier', '—')}",
        ]
    else:
        lines.append("- (lookup_account not called or failed)")

    lines += ["", "VELOCITY ANALYSIS"]
    if velocity_data:
        peak = velocity_data.get("peak_window") or {}
        peak_str = f"{peak.get('start', '—')} – {peak.get('end', '—')}"
        fraud_types = velocity_data.get("fraud_types") or []
        lines += [
            f"- Max Velocity: {velocity_data.get('max_velocity', '—')} txns in a 5-min window",
            f"- Velocity Threshold: 5",
            f"- Risk Score: {velocity_data.get('risk_score', '—')}/100",
            f"- Risk Level: {velocity_data.get('risk_level', '—')}",
            f"- Geo Anomaly Flags: {velocity_data.get('geo_flags', '—')}",
            f"- Total Transactions: {velocity_data.get('total_txns', '—')}",
            f"- Total Amount: ${float(velocity_data.get('total_amount', 0)):,.2f}",
            f"- Peak Window: {peak_str}",
            f"- Fraud Types Detected: {', '.join(fraud_types) if fraud_types else 'None'}",
        ]
    else:
        lines.append("- (analyze_velocity not called or failed)")

    if txn_data:
        lines += ["", "RECENT TRANSACTIONS (last 10)"]
        for t in txn_data[:10]:
            flags = []
            if t.get("velocity_flag"):
                flags.append("VELOCITY")
            if t.get("geo_flag"):
                flags.append("GEO")
            flag_str = " | ".join(flags) if flags else "OK"
            lines.append(
                f"- {t.get('timestamp','—')} | ${float(t.get('amount',0)):,.2f} | "
                f"{t.get('type','—')} | {t.get('city','—')} | {t.get('status','—')} | {flag_str}"
            )

    return "\n".join(lines)


# ── Ground truth verifier (no LLM) ───────────────────────────────────────────
def _verify_data_summary(data_summary: str) -> str:
    """
    Re-runs actual DB calculations and compares against what the Data Agent wrote.
    Returns a discrepancy report injected into the Audit Agent's input.
    Any mismatch is a confirmed hallucination the Audit Agent must flag.
    """
    _load()

    # Extract account ID from the summary text
    acc_match = re.search(r"Account ID:\s*(ACC-\w+)", data_summary, re.IGNORECASE)
    if not acc_match:
        return "GROUND TRUTH: Could not extract account ID from summary — manual review required."

    account_id = acc_match.group(1).upper()
    acc_txns = _txns[_txns["account_id"] == account_id]
    if acc_txns.empty:
        return f"GROUND TRUTH: Account {account_id} not found in database."

    from utils import compute_velocity
    v = compute_velocity(acc_txns)

    actual = {
        "max_velocity":  v["max_velocity"],
        "risk_score":    v["risk_score"],
        "risk_level":    v["risk_level"],
        "geo_flags":     v["geo_flags"],
        "total_txns":    len(acc_txns),
        "total_amount":  round(v["total_amount"], 2),
    }

    # Parse claimed values from the data summary text
    def _int(pattern):
        m = re.search(pattern, data_summary, re.IGNORECASE)
        return int(m.group(1)) if m else None

    def _float(pattern):
        m = re.search(pattern, data_summary, re.IGNORECASE)
        return round(float(m.group(1).replace(",", "")), 2) if m else None

    def _str(pattern):
        m = re.search(pattern, data_summary, re.IGNORECASE)
        return m.group(1).strip() if m else None

    claimed = {
        "max_velocity": _int(r"Max Velocity:\s*(\d+)"),
        "risk_score":   _int(r"Risk Score:\s*(\d+)"),
        "risk_level":   _str(r"Risk Level:\s*(High|Medium|Low)"),
        "geo_flags":    _int(r"Geo Anomaly Flags:\s*(\d+)"),
        "total_txns":   _int(r"Total Transactions:\s*(\d+)"),
        "total_amount": _float(r"Total Amount:\s*\$?([\d,]+\.?\d*)"),
    }

    discrepancies = []
    for field, actual_val in actual.items():
        claimed_val = claimed.get(field)
        if claimed_val is None:
            discrepancies.append(f"  - {field}: not found in summary (actual: {actual_val})")
        elif str(claimed_val).lower() != str(actual_val).lower():
            discrepancies.append(f"  - {field}: claimed {claimed_val}, actual {actual_val} ← MISMATCH")

    if discrepancies:
        return (
            "GROUND TRUTH DISCREPANCIES — the following values in the Data Agent summary "
            "do not match the database. Treat these as hallucinations and use the actual values:\n"
            + "\n".join(discrepancies)
        )

    return (
        f"GROUND TRUTH VERIFIED for {account_id}: "
        f"max_velocity={actual['max_velocity']}, risk_score={actual['risk_score']}, "
        f"risk_level={actual['risk_level']}, geo_flags={actual['geo_flags']}, "
        f"total_txns={actual['total_txns']}, total_amount=${actual['total_amount']:,.2f}. "
        "All values match the database."
    )


# ── Agent builders ────────────────────────────────────────────────────────────
def _build_data_agent():
    llm = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
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
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
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
    Traces each stage to Langfuse using the stable low-level API.
    """
    lc_messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]

    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

    trace = langfuse.trace(
        name="fraud-agent-run",
        input=user_input,
        session_id=session_id,
        user_id=analyst,
        metadata={"analyst": analyst},
    )

    debug: dict = {}

    try:
        # Stage 1: Data collection
        # If query contains an account ID, call tools directly (reliable).
        # Otherwise fall back to LLM agent for open-ended questions.
        gen1 = trace.generation(name="data-agent", model=model_name, input=user_input)
        acc_match = re.search(r"\bACC-\w+\b", user_input, re.IGNORECASE)
        if acc_match:
            data_output = _direct_account_investigation(acc_match.group(0).upper())
        else:
            data_result = _build_data_agent().invoke({"messages": lc_messages})
            data_output = _build_data_summary_from_messages(data_result["messages"])
        gen1.end(output=data_output)
        debug["data_agent"] = data_output

        # Ground truth check (deterministic — no LLM)
        ground_truth = _verify_data_summary(data_output)
        gt_span = trace.span(name="ground-truth-verifier", input=data_output)
        gt_span.end(output=ground_truth)
        debug["ground_truth"] = ground_truth

        # Stage 2: Audit review (gets data summary + ground truth verification)
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

    except Exception:
        raise
    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}], debug
