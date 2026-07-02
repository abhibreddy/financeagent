"""
fingpt-service — a small host-run service that runs FinGPT-Forecaster inference via Ollama.

Runs on the HOST (not in a container) so it can reach the host Ollama at localhost:11434.
The main backend proxies to this service. It is keyless and stateless: it takes only a user
prompt and returns the model's forecast. The FinGPT system prompt + Llama-2 template live in
the Ollama Modelfile (single source of truth), so this service sends only the user message.

Run: uvicorn main:app --host 0.0.0.0 --port 8001   (from the fingpt-service/ directory)
"""
import os
import time

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("FINGPT_MODEL", "fingpt-forecaster")
# 7B generation on Apple-Silicon CPU/Metal can take 30-90s; give Ollama room.
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

app = FastAPI(title="FinGPT Forecaster Service", version="1.0.0")


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    report: str
    model: str
    latency_ms: int


@app.get("/health")
def health():
    """OK only if Ollama is reachable and the FinGPT model is present."""
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        ready = any(m.startswith(MODEL) for m in models)
        return {"status": "ok" if ready else "model_missing", "model": MODEL, "ollama_models": models}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Run one FinGPT forecast. Sends only the user prompt; the model owns its system prompt."""
    started = time.monotonic()
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": req.prompt}],
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama error {r.status_code}: {r.text[:200]}")

    report = (r.json().get("message") or {}).get("content", "").strip()
    if not report:
        raise HTTPException(status_code=502, detail="FinGPT returned an empty response")
    return GenerateResponse(report=report, model=MODEL, latency_ms=int((time.monotonic() - started) * 1000))
