import pandas as pd

from bots.config import EMA_PERIOD
from bots.indicators import ema, rsi, volatility, volume_spike

MIN_CANDLES = EMA_PERIOD + 15


def generate_signal(df):
    df = df.copy()

    if len(df) < MIN_CANDLES:
        return "HOLD"

    df["rsi"] = rsi(df["close"])
    df["ema"] = ema(df["close"], period=EMA_PERIOD)
    vol = volatility(df).iloc[-1]

    latest = df.iloc[-1]
    baseline = df["close"].iloc[-10]

    if baseline == 0:
        return "HOLD"

    price_change = (latest["close"] - baseline) / baseline

    if pd.isna(latest["rsi"]) or pd.isna(vol) or pd.isna(latest["ema"]):
        return "HOLD"

    in_uptrend = latest["close"] > latest["ema"]
    has_volume = volume_spike(df)

    # ENTRY: only buy dips in an uptrend with volume confirmation
    if (
        in_uptrend
        and price_change < -0.03
        and latest["rsi"] < 35
        and vol > 0.01
        and has_volume
    ):
        return "BUY"

    # EXIT: RSI overbought or momentum target hit
    if latest["rsi"] > 65 or price_change > 0.05:
        return "SELL"

    return "HOLD"
