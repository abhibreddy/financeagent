"""
core/llm.py — single factory for the Azure OpenAI chat model.

All agents build their LLM through make_azure_llm() so credentials and defaults live
in one place. Tests patch core.llm.AzureChatOpenAI to mock every agent at once.
"""
import os
from langchain_openai import AzureChatOpenAI

import core.config  # noqa: F401 — imported for its side effect: loads .env before we read env vars


def make_azure_llm(**kwargs):
    """Return a configured AzureChatOpenAI. Extra kwargs override defaults."""
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        temperature=0,
        **kwargs,
    )
