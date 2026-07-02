"""
sse.py — stream a 3-stage agent pipeline to the client as Server-Sent Events.

The reused run_* functions compute everything and return at the end, so this is a "staged
reveal": run the pipeline off the event loop, then emit its stages (data → ground_truth →
audit → final) in order with small pauses so the UI can animate the Data→Audit→Synthesis
pipeline. True token streaming would require the agents to yield — a later enhancement.
"""
import asyncio
import json

STAGE_KEYS = [
    ("data", "data_agent"),
    ("ground_truth", "ground_truth"),
    ("audit", "audit_agent"),
]


def _event(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload)}


async def stream_agent(run_fn, messages, session_id, analyst, has_debug=True):
    """Async generator of SSE events for one agent run."""
    yield _event("status", {"state": "running"})

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, run_fn, messages, session_id, analyst)
    except Exception as e:  # noqa: BLE001 — surface any agent/LLM failure to the client
        yield _event("error", {"message": str(e)})
        return

    if has_debug:
        final, updated_messages, debug = result
        for stage_name, debug_key in STAGE_KEYS:
            content = debug.get(debug_key, "")
            if content:
                yield _event("stage", {"stage": stage_name, "content": content})
                await asyncio.sleep(0.4)  # animate the pipeline reveal
    else:
        final, updated_messages = result

    yield _event("final", {"final": final, "messages": updated_messages})
