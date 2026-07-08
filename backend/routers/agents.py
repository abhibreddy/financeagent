"""
agents.py — SSE streaming endpoints for the three agent pipelines.
Reuses run_agent / run_invoice_agent / run_trading_agent verbatim.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from modules.finance.agent import run_agent
from modules.finance.invoice_agent import run_invoice_agent
from modules.trading.trading_agent import run_trading_agent
from modules.finance_suite.engine import run_suite_agent
from backend.sse import stream_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRequest(BaseModel):
    messages: list[dict]
    session_id: str
    analyst: str = "analyst"


class SuiteAgentRequest(AgentRequest):
    scenario: str | None = None


@router.post("/finance/stream")
async def finance_stream(req: AgentRequest):
    return EventSourceResponse(
        stream_agent(run_agent, req.messages, req.session_id, req.analyst, has_debug=True)
    )


@router.post("/invoice/stream")
async def invoice_stream(req: AgentRequest):
    return EventSourceResponse(
        stream_agent(run_invoice_agent, req.messages, req.session_id, req.analyst, has_debug=False)
    )


@router.post("/trading/stream")
async def trading_stream(req: AgentRequest):
    return EventSourceResponse(
        stream_agent(run_trading_agent, req.messages, req.session_id, req.analyst, has_debug=True)
    )


@router.post("/suite/{agent_key}/stream")
async def suite_stream(agent_key: str, req: SuiteAgentRequest):
    # Bind agent_key + scenario so the run_fn matches stream_agent's (messages, session_id, analyst) call.
    def run_fn(messages, session_id, analyst):
        return run_suite_agent(agent_key, messages, session_id, analyst, scenario=req.scenario)

    return EventSourceResponse(
        stream_agent(run_fn, req.messages, req.session_id, req.analyst, has_debug=True)
    )
