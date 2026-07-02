"""
core/tracing.py — single cached Langfuse client factory.

Replaces the identical Langfuse(...) inits previously duplicated across agents and the
dashboard. Callers keep using whichever tracing API they need; this only hands back one
configured client.
"""
import os
from functools import lru_cache
from langfuse import Langfuse

import core.config  # noqa: F401 — imported for its side effect: loads .env before we read env vars


@lru_cache
def get_langfuse() -> Langfuse:
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
    )
