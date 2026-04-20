"""
Hybrid strategy: EMA200 trend filter + Bollinger Band lower touch + RSI oversold.

Entry conditions (ALL must be true):
  1. Strong uptrend: price > EMA200 AND EMA50 > EMA200
  2. Price touched or crossed below the lower Bollinger Band this candle
  3. RSI < RSI_BUY (default 42) — momentum oversold

Exit conditions (first hit wins):
  1. Trailing stop (managed in main.py, not here)
  2. Take profit (managed in main.py)
  3. RSI > RSI_SELL (default 65) — momentum overbought

Backtest result (BTC/USD 1h, Apr 2024 – Apr 2026):
  +24.8% return vs +19.9% buy-and-hold
  89 trades | 39% win rate | avg win +3.91% | avg loss -1.93% | PF 1.26
"""

import pandas as pd

from bots.config import (
    BB_PERIOD, BB_STD,
    EMA_FAST, EMA_SLOW,
    RSI_BUY, RSI_PERIOD, RSI_SELL,
)
from bots.indicators import bollinger_bands, ema, rsi

# Minimum candles needed before signals are valid
MIN_CANDLES = EMA_SLOW + 20


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all indicators on a copy of df. Call this once per tick."""
    df = df.copy()
    df["rsi"]      = rsi(df["close"], period=RSI_PERIOD)
    df["ema_fast"] = ema(df["close"], period=EMA_FAST)
    df["ema_slow"] = ema(df["close"], period=EMA_SLOW)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger_bands(
        df["close"], period=BB_PERIOD, std_mult=BB_STD
    )
    return df


def generate_signal(df: pd.DataFrame) -> str:
    """
    Returns 'BUY', 'SELL', or 'HOLD'.
    df must have columns: close, high, low, open, volume.
    """
    if len(df) < MIN_CANDLES:
        return "HOLD"

    df = add_indicators(df)
    latest = df.iloc[-1]

    # Guard against NaN during warmup
    for col in ("rsi", "ema_fast", "ema_slow", "bb_lower", "bb_upper"):
        if pd.isna(latest[col]):
            return "HOLD"

    price = latest["close"]

    # ── ENTRY ────────────────────────────────────────────────────────────────
    strong_uptrend  = price > latest["ema_slow"] and latest["ema_fast"] > latest["ema_slow"]
    touched_bb_low  = latest["low"] <= latest["bb_lower"]
    rsi_oversold    = latest["rsi"] < RSI_BUY

    if strong_uptrend and touched_bb_low and rsi_oversold:
        return "BUY"

    # ── EXIT ─────────────────────────────────────────────────────────────────
    rsi_overbought = latest["rsi"] > RSI_SELL

    if rsi_overbought:
        return "SELL"

    return "HOLD"
