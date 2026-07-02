"""
forecaster.py — FinGPT-Forecaster methodology, re-implemented on Azure OpenAI.

Adapted from AI4Finance-Foundation/FinGPT (FinGPT_Forecaster: prompt.py, app.py).
FinGPT-Forecaster fine-tunes Llama-2 with LoRA; here we keep its *methodology* — the
company/news/financials prompt structure and the seasoned-analyst system prompt — but run
the reasoning through the project's existing Azure OpenAI model instead of a self-hosted
GPU model. Data is gathered deterministically (no tokens); a single Azure call produces the
forecast, keeping token usage low.

See modules/trading/vendor/ for the original FinGPT prompt code and license (attribution).
"""
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from core.config import FINNHUB_API_KEY
from core.llm import make_azure_llm

# FinGPT-Forecaster's inference system prompt (verbatim methodology).
SYSTEM_PROMPT = (
    "You are a seasoned stock market analyst. Your task is to list the positive "
    "developments and potential concerns for companies based on relevant news and basic "
    "financials from the past weeks, then provide an analysis and prediction for the "
    "companies' stock price movement for the upcoming week. Your answer format should be "
    "as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n"
    "[Prediction & Analysis]\nPrediction: ...\nAnalysis: ..."
)

# Token-control caps
MAX_HEADLINES_PER_WEEK = 5
SUMMARY_CHARS = 200


class ForecasterError(Exception):
    pass


def _finnhub_client():
    if not FINNHUB_API_KEY:
        raise ForecasterError(
            "FINNHUB_API_KEY is not set. Add it to .env (free key at https://finnhub.io)."
        )
    import finnhub  # imported lazily so the module loads without the dep installed
    return finnhub.Client(api_key=FINNHUB_API_KEY)


def _week_windows(as_of: str, weeks: int) -> list[tuple[str, str]]:
    """Return [(start, end), ...] weekly windows ending at as_of, oldest first."""
    end = datetime.strptime(as_of, "%Y-%m-%d")
    windows = []
    for _ in range(weeks):
        start = end - timedelta(days=7)
        windows.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        end = start
    return list(reversed(windows))


def _company_intro(client, symbol: str) -> str:
    profile = client.company_profile2(symbol=symbol)
    if not profile:
        return f"[Company Introduction]:\n\n{symbol} — no profile available."
    return (
        "[Company Introduction]:\n\n"
        f"{profile.get('name', symbol)} operates in the {profile.get('finnhubIndustry', 'N/A')} "
        f"sector, trading as {profile.get('ticker', symbol)} on {profile.get('exchange', 'N/A')} "
        f"({profile.get('country', 'N/A')}). Market cap: "
        f"{profile.get('marketCapitalization', 0):.0f} {profile.get('currency', '')}."
    )


def _weekly_news_and_prices(client, symbol: str, windows: list[tuple[str, str]]) -> str:
    """Per-week price move + a capped set of news headlines. Deterministic, no LLM."""
    prices = yf.download(symbol, windows[0][0], windows[-1][1], progress=False, auto_adjust=True)
    # Newer yfinance returns MultiIndex columns like ('Close', 'AAPL'); flatten to a single level
    # so prices["Close"] is a 1-D Series and float(span.iloc[i]) works.
    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = prices.columns.get_level_values(0)
    blocks = []
    for start, end in windows:
        try:
            span = prices.loc[start:end]["Close"]
            if len(span) >= 2:
                s_px, e_px = float(span.iloc[0]), float(span.iloc[-1])
                term = "increased" if e_px >= s_px else "decreased"
                head = (f"From {start} to {end}, {symbol}'s stock price {term} from "
                        f"{s_px:.2f} to {e_px:.2f}. News during this period:")
            else:
                head = f"From {start} to {end}, {symbol} (price data unavailable). News:"
        except (KeyError, IndexError):
            head = f"From {start} to {end}, {symbol}. News:"

        news = client.company_news(symbol, _from=start, to=end) or []
        items = []
        for n in news[:MAX_HEADLINES_PER_WEEK]:
            summary = (n.get("summary") or "")[:SUMMARY_CHARS]
            items.append(f"[Headline]: {n.get('headline', '')}\n[Summary]: {summary}")
        blocks.append(head + "\n\n" + ("\n\n".join(items) if items else "No major news.") + "\n")
    return "\n".join(blocks)


def _basic_financials(client, symbol: str) -> str:
    data = client.company_basic_financials(symbol, "all")
    metric = (data or {}).get("metric", {})
    if not metric:
        return "[Basic Financials]:\n\nNo basic financials reported."
    keys = ["52WeekHigh", "52WeekLow", "peBasicExclExtraTTM", "psTTM",
            "roeTTM", "netProfitMarginTTM", "revenueGrowthTTMYoy"]
    lines = [f"{k}: {metric[k]}" for k in keys if k in metric and metric[k] is not None]
    return "[Basic Financials]:\n\n" + ("\n".join(lines) if lines else "No key metrics available.")


def build_forecast_prompt(symbol: str, as_of: str, weeks: int = 2, with_basics: bool = True) -> str:
    """Assemble the FinGPT-style user prompt from live market data (no tokens spent here)."""
    client = _finnhub_client()
    windows = _week_windows(as_of, weeks)
    period_start = windows[-1][1]
    next_end = (datetime.strptime(period_start, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

    parts = [_company_intro(client, symbol), _weekly_news_and_prices(client, symbol, windows)]
    if with_basics:
        parts.append(_basic_financials(client, symbol))

    info = "\n\n".join(parts)
    return (
        info
        + f"\n\nBased on all the information before {period_start}, let's first analyze the "
        f"positive developments and potential concerns for {symbol}. Come up with 2-4 most "
        "important factors respectively and keep them concise. Most factors should be inferred "
        f"from company related news. Then make your prediction of the {symbol} stock price "
        f"movement for next week ({period_start} to {next_end}). Provide a summary analysis to "
        "support your prediction."
    )


def forecast(symbol: str, as_of: str | None = None, weeks: int = 2, with_basics: bool = True) -> dict:
    """
    Run one FinGPT-style forecast for a ticker via Azure OpenAI.
    Returns {"symbol", "as_of", "prompt", "report"}.
    """
    symbol = symbol.upper().strip()
    as_of = as_of or datetime.today().strftime("%Y-%m-%d")

    prompt = build_forecast_prompt(symbol, as_of, weeks=weeks, with_basics=with_basics)

    from langchain_core.messages import SystemMessage, HumanMessage
    llm = make_azure_llm()
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])

    return {"symbol": symbol, "as_of": as_of, "prompt": prompt, "report": response.content}
