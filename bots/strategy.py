import pandas as pd

from bots.indicators import rsi, volatility


MIN_CANDLES = 15


def generate_signal(df):
    df = df.copy()

    if len(df) < MIN_CANDLES:
        return "HOLD"

    df["rsi"] = rsi(df["close"])
    vol = volatility(df).iloc[-1]

    latest = df.iloc[-1]
    baseline = df["close"].iloc[-10]
    if baseline == 0:
        return "HOLD"

    price_change = (df["close"].iloc[-1] - baseline) / baseline

    if pd.isna(latest["rsi"]) or pd.isna(vol):
        return "HOLD"

    # ENTRY CONDITIONS
    if price_change < -0.03 and latest["rsi"] < 35 and vol > 0.01:
        return "BUY"

    # EXIT CONDITIONS
    if latest["rsi"] > 65 or price_change > 0.05:
        return "SELL"

    return "HOLD"
