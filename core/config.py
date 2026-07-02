"""
core/config.py — single source of environment loading and resolved absolute paths.

Loading .env once here (instead of per-module) and resolving every data/db/css path
relative to the repo root makes the app work regardless of the current working directory.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# The one and only load_dotenv() for the whole app. Load from an explicit absolute path so
# it works regardless of the current working directory (Streamlit, uvicorn, pytest, cron…).
load_dotenv(REPO_ROOT / ".env")

CSS_PATH = REPO_ROOT / "css" / "style.css"

# Finance module
FINANCE_DATA = REPO_ROOT / "modules" / "finance" / "data"
# DB path is env-overridable so a container can point it at a mounted volume for persistence.
FINANCE_DB = Path(os.getenv("FINANCE_DB", str(REPO_ROOT / "modules" / "finance" / "fraudguard.db")))

# Trading module
TRADING_DATA = REPO_ROOT / "modules" / "trading" / "data"

# Finnhub API key for the FinGPT-style forecaster (free tier at finnhub.io).
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
