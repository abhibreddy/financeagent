"""
specs.py — per-agent configuration for the Finance AI Suite.

One AgentSpec per agent drives the shared engine (engine.run_suite_agent): which
deterministic report to compute, the audit/synthesis system prompts, UI metadata, and
demo suggestions. Adding a 7th agent is just another AgentSpec entry (+ a report builder
and a data/<key>.json fixture) — no new pipeline code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_AUDIT = (
    "You are a {title} audit reviewer. You are given a deterministic finance report and a "
    "ground-truth verification of it. Sanity-check the numbers, call out the 1-3 most material "
    "risks or anomalies, and flag anything the ground-truth marked as a discrepancy. Be concise "
    "and specific. Never invent figures not present in the report."
)

_SYNTH = (
    "You are {title}, a finance operations assistant. Using ONLY the verified report and the "
    "audit review, answer the user's request in clear markdown: a one-line headline, the key "
    "numbers as bullets, and a short 'Recommended actions' list. Do not fabricate values."
)


@dataclass(frozen=True)
class AgentSpec:
    key: str
    title: str
    icon: str
    subtitle: str
    has_report: bool = True                      # False for Copilot (no scenario fixtures)
    suggestions: list[str] = field(default_factory=list)

    @property
    def audit_prompt(self) -> str:
        return _AUDIT.format(title=self.title)

    @property
    def synth_prompt(self) -> str:
        return _SYNTH.format(title=self.title)


SUITE: dict[str, AgentSpec] = {
    "ap": AgentSpec(
        key="ap", title="AP Agent", icon="📤", subtitle="Accounts Payable — aging, overdue bills & early-pay discounts",
        suggestions=["Summarize this scenario", "Which bills should we pay first?", "Any duplicate-payment risk?"],
    ),
    "ar": AgentSpec(
        key="ar", title="AR Agent", icon="📥", subtitle="Accounts Receivable — DSO, aging & collections priority",
        suggestions=["Summarize this scenario", "Who should we chase for collections?", "What is at risk of write-off?"],
    ),
    "cashflow": AgentSpec(
        key="cashflow", title="Cash Flow Agent", icon="💵", subtitle="13-week cash forecast, runway & liquidity risk",
        suggestions=["Summarize the forecast", "When do we run out of cash?", "How can we extend runway?"],
    ),
    "reconciliation": AgentSpec(
        key="reconciliation", title="Reconciliation Agent", icon="🔗", subtitle="Bank vs ledger matching & break analysis",
        suggestions=["Summarize the reconciliation", "What are the biggest breaks?", "Which breaks are timing vs real?"],
    ),
    "insights": AgentSpec(
        key="insights", title="Financial Insights Agent", icon="📊", subtitle="KPIs, margins & budget variance",
        suggestions=["Summarize performance", "What is driving margin change?", "How are we tracking vs budget?"],
    ),
    "copilot": AgentSpec(
        key="copilot", title="Finance Copilot", icon="🤖", subtitle="Cross-domain finance assistant over AP, AR, cash, recon & insights",
        has_report=False,
        suggestions=[
            "What should the finance team focus on this week?",
            "Summarize our payables and receivables position.",
            "Where is the biggest liquidity risk?",
        ],
    ),
}
