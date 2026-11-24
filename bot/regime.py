from enum import Enum

from bot.indicators import add_core_indicators


class Regime(str, Enum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    SIDEWAYS = "SIDEWAYS"
    UNKNOWN = "UNKNOWN"


def classify_regime(df, trend_tolerance=0.001):
    if len(df) < 200:
        return Regime.UNKNOWN

    required = {"ema50", "ema200"}
    with_indicators = df if required.issubset(df.columns) else add_core_indicators(df)
    latest = with_indicators.iloc[-1]

    ema50 = latest["ema50"]
    ema200 = latest["ema200"]

    if ema200 == 0 or ema50 != ema50 or ema200 != ema200:
        return Regime.UNKNOWN

    spread = (ema50 - ema200) / ema200

    if spread > trend_tolerance:
        return Regime.UPTREND

    if spread < -trend_tolerance:
        return Regime.DOWNTREND

    return Regime.SIDEWAYS
