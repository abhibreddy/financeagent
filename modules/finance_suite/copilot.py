"""
copilot.py — tool-calling data stage for the Finance Copilot.

The five analytical suite agents have a single deterministic report as their data stage. Copilot
has no fixed scenario, so it uses an LLM with tools to decide which agents/scenarios to pull. The
tools return the SAME deterministic build_report() output, so the data layer stays hallucination-free
even though an LLM chose what to fetch. The shared engine then audits + synthesizes over what was
gathered. Mirrors modules/finance/agent.py's _build_data_agent (bind_tools + ToolNode loop).
"""
import json
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from core.llm import make_azure_llm
from modules.finance_suite.specs import SUITE
from modules.finance_suite.scenarios import list_scenarios, load_scenario
from modules.finance_suite.data import build_report, render_report


@tool
def list_finance_data() -> str:
    """List the finance agents and the scenario ids available for each. Call this first to see what data exists."""
    out = {key: [s["id"] for s in list_scenarios(key)]
           for key, spec in SUITE.items() if spec.has_report}
    return json.dumps(out)


@tool
def get_finance_report(agent_key: str, scenario_id: str) -> str:
    """Get the deterministic finance report for one agent + scenario.
    agent_key is one of: ap, ar, cashflow, reconciliation, insights.
    scenario_id is one of the ids returned by list_finance_data."""
    spec = SUITE.get(agent_key)
    if spec is None or not spec.has_report:
        return json.dumps({"error": f"unknown agent '{agent_key}'"})
    try:
        sc = load_scenario(agent_key, scenario_id)
    except KeyError:
        return json.dumps({"error": f"unknown scenario '{scenario_id}' for '{agent_key}'"})
    return json.dumps({"agent": agent_key, "scenario": scenario_id, "report": build_report(agent_key, sc)})


COPILOT_TOOLS = [list_finance_data, get_finance_report]

COPILOT_DATA_PROMPT = (
    "You are the data-gathering stage of Finance Copilot. Use the tools to pull the finance reports "
    "needed to answer the user. Call list_finance_data first if unsure what exists, then "
    "get_finance_report for each agent/scenario relevant to the question. Gather data only — do not "
    "write the final answer here."
)


class _State(TypedDict):
    messages: Annotated[list, add_messages]


def _build_copilot_data_agent():
    llm = make_azure_llm().bind_tools(COPILOT_TOOLS)
    tool_node = ToolNode(COPILOT_TOOLS)

    def call_model(state: _State):
        messages = [SystemMessage(content=COPILOT_DATA_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        if not isinstance(response, BaseMessage):
            response = AIMessage(content=response.content)
        return {"messages": [response]}

    def should_continue(state: _State):
        last = state["messages"][-1]
        return "tools" if (hasattr(last, "tool_calls") and last.tool_calls) else END

    graph = StateGraph(_State)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def gather_copilot_data(messages: list) -> tuple:
    """
    Run the tool-calling data agent over the conversation. Returns (data_output_text, pulled_refs).
    The data_output is built ONLY from tool results (deterministic build_report output), never from
    LLM free-text, so it can't be hallucinated.
    """
    lc = [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
          for m in messages]
    result = _build_copilot_data_agent().invoke({"messages": lc}, {"recursion_limit": 12})

    reports, refs = [], []
    for msg in result["messages"]:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            content = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(content, dict) and "report" in content:
            ref = f"{content['agent']}/{content['scenario']}"
            refs.append(ref)
            reports.append(f"REPORT {ref}\n" + render_report(content["agent"], content["report"]))

    if reports:
        return "\n\n".join(reports), refs
    return "(Copilot queried no datasets — answering from general finance knowledge.)", refs
