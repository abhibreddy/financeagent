"""
main.py — FastAPI app that exposes the existing Python logic to the Next.js frontend.

Reuses modules.finance.*, modules.trading.*, core.* verbatim (no logic rewrite). The repo
root is added to sys.path so those absolute imports resolve when running from anywhere.
Run: uvicorn backend.main:app --reload --port 8000
"""
import os
import sys
from pathlib import Path

# Ensure repo root is importable so `from modules.finance.utils import ...` works.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import agents, finance, finance_suite, trading

app = FastAPI(title="RT ERP API", version="1.0.0")

# Frontend dev server. It runs on 3001 to avoid Langfuse's 3000; 3000 kept for flexibility.
# Override with FRONTEND_ORIGINS (comma-separated) for other hosts / deployment.
_default_origins = "http://localhost:3001,http://127.0.0.1:3001,http://localhost:3000"
_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(finance.router)
app.include_router(finance_suite.router)
app.include_router(trading.router)
app.include_router(agents.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
