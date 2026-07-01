"""
utils.py — pure data/logic layer for the Trading module (no Streamlit, no LLM).

Mirrors the role of modules/finance/utils.py: load synthetic data and compute the
deterministic metrics the agent pipeline reasons over and audits against.
"""
import hashlib

import pandas as pd

from core.config import TRADING_DATA

# Concentration thresholds (largest single-name weight, %)
CONCENTRATION_HIGH = 25.0
CONCENTRATION_MEDIUM = 15.0


# ── Data loading ────────────────────────────────────────────────────────────────
def load_positions() -> pd.DataFrame:
    return pd.read_csv(TRADING_DATA / "positions.csv")


def load_trades() -> pd.DataFrame:
    return pd.read_csv(TRADING_DATA / "trades.csv", parse_dates=["timestamp"])


def load_prices() -> pd.DataFrame:
    return pd.read_csv(TRADING_DATA / "prices.csv", parse_dates=["date"])


# ── Portfolio metrics ─────────────────────────────────────────────────────────
def compute_portfolio_metrics(positions: pd.DataFrame) -> dict:
    """Market value, cost basis, unrealized P&L, and per-position weights."""
    p = positions.copy()
    p["market_value"] = p["quantity"] * p["current_price"]
    p["cost_basis"] = p["quantity"] * p["avg_cost"]
    p["unrealized_pnl"] = p["market_value"] - p["cost_basis"]

    total_mv = float(p["market_value"].sum())
    total_cb = float(p["cost_basis"].sum())
    p["weight_pct"] = (p["market_value"] / total_mv * 100).round(2) if total_mv else 0.0

    return {
        "total_market_value": round(total_mv, 2),
        "total_cost_basis": round(total_cb, 2),
        "unrealized_pnl": round(total_mv - total_cb, 2),
        "unrealized_pnl_pct": round((total_mv - total_cb) / total_cb * 100, 2) if total_cb else 0.0,
        "num_positions": int(len(p)),
        "weights": p[["ticker", "weight_pct"]].set_index("ticker")["weight_pct"].to_dict(),
    }


def compute_exposure(positions: pd.DataFrame) -> dict:
    """Sector / asset-class concentration and largest single-name weight."""
    p = positions.copy()
    p["market_value"] = p["quantity"] * p["current_price"]
    total_mv = float(p["market_value"].sum())

    sector = (p.groupby("sector")["market_value"].sum() / total_mv * 100).round(2)
    asset = (p.groupby("asset_class")["market_value"].sum() / total_mv * 100).round(2)
    name_weights = (p.groupby("ticker")["market_value"].sum() / total_mv * 100).round(2)

    largest_name = name_weights.idxmax()
    largest_weight = float(name_weights.max())

    if largest_weight >= CONCENTRATION_HIGH:
        level = "High"
    elif largest_weight >= CONCENTRATION_MEDIUM:
        level = "Medium"
    else:
        level = "Low"

    return {
        "sector_exposure": sector.to_dict(),
        "asset_class_exposure": asset.to_dict(),
        "largest_position": largest_name,
        "largest_weight_pct": largest_weight,
        "concentration_level": level,
    }


def compute_risk_metrics(prices: pd.DataFrame, positions: pd.DataFrame) -> dict:
    """Portfolio-weighted volatility, worst single-name drawdown, and a 0-100 risk score."""
    held = positions["ticker"].tolist()
    p = prices[prices["ticker"].isin(held)].sort_values(["ticker", "date"])

    daily_vol = {}
    max_dd = {}
    for ticker, grp in p.groupby("ticker"):
        closes = grp["close"].reset_index(drop=True)
        returns = closes.pct_change().dropna()
        daily_vol[ticker] = float(returns.std())
        running_max = closes.cummax()
        drawdown = (closes - running_max) / running_max
        max_dd[ticker] = float(drawdown.min())  # most negative

    # Weight volatility by market value
    metrics = compute_portfolio_metrics(positions)
    weights = metrics["weights"]
    port_vol = sum(daily_vol.get(t, 0) * (w / 100) for t, w in weights.items())
    worst_dd = min(max_dd.values()) if max_dd else 0.0

    # Risk score: blend annualized vol and worst drawdown into 0-100
    ann_vol = port_vol * (252 ** 0.5)
    risk_score = int(min(100, round(ann_vol * 200 + abs(worst_dd) * 100)))

    if risk_score >= 66:
        risk_level = "High"
    elif risk_score >= 33:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "portfolio_daily_volatility": round(port_vol, 4),
        "annualized_volatility_pct": round(ann_vol * 100, 2),
        "worst_drawdown_pct": round(worst_dd * 100, 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
    }


def signal_stub(ticker: str, prices: pd.DataFrame, window: int = 20) -> dict:
    """Naive momentum signal: last close vs N-day moving average."""
    grp = prices[prices["ticker"] == ticker].sort_values("date")
    if grp.empty:
        return {"ticker": ticker, "signal": "UNKNOWN", "reason": "no price data"}
    closes = grp["close"]
    last = float(closes.iloc[-1])
    ma = float(closes.tail(window).mean())
    if last > ma * 1.02:
        signal = "BUY"
    elif last < ma * 0.98:
        signal = "SELL"
    else:
        signal = "HOLD"
    return {
        "ticker": ticker,
        "signal": signal,
        "last_close": round(last, 2),
        "moving_avg": round(ma, 2),
    }


def sentiment_stub(ticker: str) -> dict:
    """Deterministic pseudo-sentiment (hash-seeded). Clearly synthetic — no external data."""
    h = int(hashlib.sha256(ticker.encode()).hexdigest(), 16)
    score = (h % 201 - 100) / 100.0  # -1.0 .. 1.0
    label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
    return {"ticker": ticker, "sentiment_score": round(score, 2), "label": label, "source": "synthetic"}


def build_portfolio_report(positions: pd.DataFrame, prices: pd.DataFrame) -> dict:
    """Consolidated deterministic report — the ground truth the audit stage verifies against."""
    return {
        "portfolio": compute_portfolio_metrics(positions),
        "exposure": compute_exposure(positions),
        "risk": compute_risk_metrics(prices, positions),
    }
