"""
generate_trading_data.py — synthetic trading data for the Trading module.

Deterministic (fixed seed) so the dataset is reproducible. Writes positions.csv,
trades.csv, and prices.csv into modules/trading/data/.
Run: python modules/trading/scripts/generate_trading_data.py
"""
import random
from datetime import date, timedelta

import pandas as pd

from core.config import TRADING_DATA

random.seed(42)

# ticker -> (sector, asset_class, starting price)
UNIVERSE = {
    "AAPL": ("Technology", "Equity", 190.0),
    "MSFT": ("Technology", "Equity", 420.0),
    "NVDA": ("Technology", "Equity", 120.0),
    "JPM":  ("Financials", "Equity", 200.0),
    "GS":   ("Financials", "Equity", 470.0),
    "XOM":  ("Energy",     "Equity", 110.0),
    "CVX":  ("Energy",     "Equity", 155.0),
    "JNJ":  ("Healthcare", "Equity", 150.0),
    "PFE":  ("Healthcare", "Equity", 28.0),
    "WMT":  ("Consumer",   "Equity", 68.0),
    "KO":   ("Consumer",   "Equity", 62.0),
    "TLT":  ("Fixed Income", "Bond", 92.0),
}

N_DAYS = 90
TRADERS = ["a.chen", "m.patel", "s.rossi", "j.kim"]

# ── Price history: geometric random walk per ticker ─────────────────────────────
start_day = date(2026, 3, 1)
dates = [start_day + timedelta(days=i) for i in range(N_DAYS)]

price_rows = []
last_close = {}
for ticker, (sector, asset_class, px) in UNIVERSE.items():
    price = px
    vol = 0.008 if asset_class == "Bond" else 0.02
    for d in dates:
        drift = random.gauss(0.0004, vol)
        price = round(max(1.0, price * (1 + drift)), 2)
        price_rows.append({"ticker": ticker, "date": d.isoformat(), "close": price})
    last_close[ticker] = price

prices = pd.DataFrame(price_rows)

# ── Positions: hold ~9 of the tickers ───────────────────────────────────────────
held = list(UNIVERSE.keys())[:9]
pos_rows = []
for i, ticker in enumerate(held, start=1):
    sector, asset_class, start_px = UNIVERSE[ticker]
    qty = random.choice([250, 500, 1000, 1500, 2000, 3000])
    avg_cost = round(start_px * random.uniform(0.85, 1.1), 2)
    pos_rows.append({
        "position_id": f"POS-{i:03d}",
        "ticker": ticker,
        "sector": sector,
        "quantity": qty,
        "avg_cost": avg_cost,
        "current_price": last_close[ticker],
        "asset_class": asset_class,
    })
positions = pd.DataFrame(pos_rows)

# ── Trades: executed trade log over the window ──────────────────────────────────
trade_rows = []
for i in range(1, 61):
    ticker = random.choice(list(UNIVERSE.keys()))
    d = random.choice(dates)
    side = random.choice(["BUY", "SELL"])
    qty = random.choice([100, 200, 500, 1000])
    px = prices[(prices["ticker"] == ticker) & (prices["date"] == d.isoformat())]["close"].iloc[0]
    trade_rows.append({
        "trade_id": f"TRD-{i:04d}",
        "timestamp": f"{d.isoformat()}T{random.randint(9,16):02d}:{random.randint(0,59):02d}:00",
        "ticker": ticker,
        "side": side,
        "quantity": qty,
        "price": px,
        "notional": round(px * qty, 2),
        "trader": random.choice(TRADERS),
    })
trades = pd.DataFrame(trade_rows).sort_values("timestamp")

TRADING_DATA.mkdir(parents=True, exist_ok=True)
positions.to_csv(TRADING_DATA / "positions.csv", index=False)
trades.to_csv(TRADING_DATA / "trades.csv", index=False)
prices.to_csv(TRADING_DATA / "prices.csv", index=False)
print(f"Generated {len(positions)} positions, {len(trades)} trades, {len(prices)} price rows")
