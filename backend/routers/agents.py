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
from backend.sse import stream_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRequest(BaseModel):
    messages: list[dict]
    session_id: str
    analyst: str = "analyst"


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
