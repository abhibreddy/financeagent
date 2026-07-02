"""
trading.py — plain JSON endpoints for the Trading module.
Reuses modules/trading/utils.py + forecaster.py verbatim.

The forecast endpoint has two engines:
  - "azure"  → the reimplementation on Azure OpenAI (modules/trading/forecaster.forecast)
  - "fingpt" → the ACTUAL FinGPT-Forecaster model, run locally via Ollama behind the
               host FinGPT service (fingpt-service/). We build the same prompt here (Finnhub +
               yfinance) and proxy it to that service.
"""
import os
from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.trading import utils as tu
from modules.trading import forecaster as tf
from backend.serializers import jsonable

router = APIRouter(prefix="/api/trading", tags=["trading"])

# The backend runs in a container; the FinGPT service runs on the host → host.docker.internal.
# Override with FINGPT_SERVICE_URL (e.g. http://localhost:8001 when the backend runs on-host).
FINGPT_SERVICE_URL = os.getenv("FINGPT_SERVICE_URL", "http://host.docker.internal:8001")
# FinGPT's num_ctx is 4096; cap weeks so the news-heavy prompt fits with response headroom.
FINGPT_MAX_WEEKS = 3


class ForecastRequest(BaseModel):
    symbol: str
    weeks: int = 2
    with_basics: bool = True
    engine: Literal["azure", "fingpt"] = "azure"


@router.get("/portfolio")
def portfolio():
    positions, prices = tu.load_positions(), tu.load_prices()
    report = tu.build_portfolio_report(positions, prices)
    return {"report": jsonable(report), "positions": jsonable(positions)}


@router.get("/positions")
def positions():
    return {"positions": jsonable(tu.load_positions())}


@router.get("/prices/{ticker}")
def prices(ticker: str):
    df = tu.load_prices()
    series = df[df["ticker"] == ticker.upper()].sort_values("date")
    if series.empty:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker.upper()}")
    return {"ticker": ticker.upper(), "prices": jsonable(series)}


@router.post("/forecast")
def forecast(req: ForecastRequest):
    if req.engine == "fingpt":
        return _forecast_fingpt(req)
    # Azure engine (default)
    try:
        result = jsonable(tf.forecast(req.symbol, weeks=req.weeks, with_basics=req.with_basics))
        result["engine"] = "azure"
        return result
    except tf.ForecasterError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # network / LLM failure
        raise HTTPException(status_code=502, detail=f"Forecast failed: {e}")


def _forecast_fingpt(req: ForecastRequest):
    """Build the FinGPT prompt here (Finnhub + yfinance), proxy to the host FinGPT service."""
    weeks = min(req.weeks, FINGPT_MAX_WEEKS)
    as_of = datetime.today().strftime("%Y-%m-%d")
    try:
        prompt = tf.build_forecast_prompt(req.symbol, as_of, weeks=weeks, with_basics=req.with_basics)
    except tf.ForecasterError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # Finnhub / yfinance failure
        raise HTTPException(status_code=502, detail=f"Market data fetch failed: {e}")

    try:
        r = httpx.post(f"{FINGPT_SERVICE_URL}/generate", json={"prompt": prompt}, timeout=120)
    except (httpx.ConnectError, httpx.ReadTimeout) as e:
        raise HTTPException(
            status_code=503,
            detail=f"FinGPT service/Ollama unavailable ({e}). Start it, or use the Azure engine.",
        )
    if r.status_code != 200:
        detail = r.json().get("detail", r.text[:200]) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]
        raise HTTPException(status_code=502 if r.status_code != 503 else 503, detail=f"FinGPT service error: {detail}")

    data = r.json()
    return {
        "symbol": req.symbol.upper(),
        "as_of": as_of,
        "prompt": prompt,
        "report": data["report"],
        "engine": "fingpt",
        "model": data.get("model", "fingpt-forecaster"),
        "latency_ms": data.get("latency_ms"),
    }
