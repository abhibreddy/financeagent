"""
engine.py — the ONE shared 3-stage runtime for every Finance AI Suite agent.

Mirrors modules/finance/agent.py::run_agent (Data → Ground Truth → Audit → Synthesis, each
traced to Langfuse) but is config-driven: the agent's AgentSpec + deterministic report builder
supply everything, so all six agents share this code. Stage 1 (data) is deterministic — the
report itself — so there is nothing to hallucinate there; the ground-truth stage re-verifies it.

Returns the 3-tuple (final, updated_messages, debug) with debug keys
`data_agent` / `ground_truth` / `audit_agent` so backend/sse.py lights up all three stage badges.
"""
from __future__ import annotations

import os

from langchain_core.messages import SystemMessage, HumanMessage

from core.llm import make_azure_llm
from core.tracing import get_langfuse
from modules.finance_suite.specs import SUITE
from modules.finance_suite.scenarios import load_scenario
from modules.finance_suite.data import build_report, render_report, verify_report
from modules.finance_suite.copilot import gather_copilot_data

langfuse = get_langfuse()


def _reason(system_prompt: str, user_content: str) -> str:
    """One LLM turn. Isolated so tests mock a single seam (core.llm.AzureChatOpenAI)."""
    resp = make_azure_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ])
    return resp.content if hasattr(resp, "content") else str(resp)


def run_suite_agent(
    agent_key: str,
    messages: list,
    session_id: str,
    analyst: str = "analyst",
    scenario: str | None = None,
) -> tuple:
    """Run the shared 3-stage pipeline for one suite agent. Returns (final, messages, debug)."""
    spec = SUITE.get(agent_key)
    if spec is None:
        raise ValueError(f"Unknown suite agent '{agent_key}'")

    user_input = messages[-1]["content"] if messages else ""
    model_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    trace = langfuse.trace(
        name=f"suite-{agent_key}-run",
        input=user_input,
        session_id=session_id,
        user_id=analyst,
        metadata={"analyst": analyst, "agent": agent_key, "scenario": scenario},
    )

    debug: dict = {}
    try:
        # ── Stage 1: Data (deterministic) ─────────────────────────────────────
        gen1 = trace.generation(name="data-agent", model=model_name, input=user_input)
        if spec.has_report:
            if not scenario:
                raise ValueError(f"Agent '{agent_key}' requires a scenario")
            sc = load_scenario(agent_key, scenario)
            report = build_report(agent_key, sc)
            data_output = f"Scenario: {sc['name']} — {sc.get('description', '')}\n\n" + render_report(agent_key, report)
            ground_truth = verify_report(agent_key, report, sc)
        else:
            # Copilot: tool-calling data stage — the LLM picks which reports to pull; the tools
            # return deterministic build_report() output, so the data layer can't be hallucinated.
            data_output, refs = gather_copilot_data(messages)
            ground_truth = (
                f"GROUND TRUTH: {len(refs)} report(s) pulled deterministically via build_report(): "
                f"{', '.join(refs)}. Figures in the data stage are exact."
                if refs else "GROUND TRUTH: N/A — no datasets were queried."
            )
        gen1.end(output=data_output)
        debug["data_agent"] = data_output

        # ── Ground truth (deterministic, no LLM) ──────────────────────────────
        gt_span = trace.span(name="ground-truth-verifier", input=data_output)
        gt_span.end(output=ground_truth)
        debug["ground_truth"] = ground_truth

        # ── Stage 2: Audit (LLM) ──────────────────────────────────────────────
        audit_input = f"Report:\n\n{data_output}\n\n---\n{ground_truth}"
        gen2 = trace.generation(name="audit-agent", model=model_name, input=audit_input)
        audit_output = _reason(spec.audit_prompt, audit_input)
        gen2.end(output=audit_output)
        debug["audit_agent"] = audit_output

        # ── Stage 3: Synthesis (LLM) ──────────────────────────────────────────
        synth_input = (
            f"Original request: {user_input}\n\n"
            f"Report:\n{data_output}\n\n"
            f"Ground truth:\n{ground_truth}\n\n"
            f"Audit review:\n{audit_output}"
        )
        gen3 = trace.generation(name="synthesis-agent", model=model_name, input=synth_input)
        final = _reason(spec.synth_prompt, synth_input)
        gen3.end(output=final)

        trace.update(output=final)
    finally:
        langfuse.flush()

    return final, messages + [{"role": "assistant", "content": final}], debug
