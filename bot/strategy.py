from dataclasses import dataclass

from bot.indicators import add_core_indicators, rsi
from bot.regime import Regime, classify_regime


@dataclass(frozen=True)
class TradeSetup:
    side: str
    entry: float
    stop: float
    target: float
    regime: str
    reason: str


def evaluate_trend_pullback_entry(df, reward_risk=2.0):
    if len(df) < 200:
        return None, "not_enough_candles"

    regime = classify_regime(df)
    if regime != Regime.UPTREND:
        return None, f"regime_{regime.value.lower()}"

    enriched = add_core_indicators(df)
    latest = enriched.iloc[-1]
    previous = enriched.iloc[-2]

    required = ["ema20", "atr14", "volume_sma20"]
    if latest[required].isna().any():
        return None, "indicators_not_ready"

    touched_ema20 = latest["low"] <= latest["ema20"] <= latest["high"]
    closed_green = latest["close"] > latest["open"]
    reclaimed_previous_high = latest["close"] > previous["high"]
    volume_confirmed = latest["volume"] > latest["volume_sma20"]

    if not touched_ema20:
        return None, "no_ema20_pullback"

    if not closed_green:
        return None, "not_green_candle"

    if not reclaimed_previous_high:
        return None, "no_prior_high_reclaim"

    if not volume_confirmed:
        return None, "no_volume_confirmation"

    entry = float(latest["close"])
    stop = float(entry - latest["atr14"])
    target = float(entry + reward_risk * latest["atr14"])

    if stop <= 0 or stop >= entry or target <= entry:
        return None, "invalid_atr_levels"

    return (
        TradeSetup(
            side="BUY",
            entry=entry,
            stop=stop,
            target=target,
            regime=regime.value,
            reason="uptrend pullback reclaimed prior high with volume confirmation",
        ),
        "entry",
    )


def find_trend_pullback_entry(df, reward_risk=2.0):
    setup, _ = evaluate_trend_pullback_entry(df, reward_risk=reward_risk)
    return setup


def generate_signal(df, in_position=False):
    """Compatibility wrapper for the live loop."""
    if in_position:
        enriched = add_core_indicators(df)
        latest = enriched.iloc[-1]
        if latest["close"] < latest["ema20"]:
            return "SELL"
        return "HOLD"

    setup = find_trend_pullback_entry(df)
    if setup:
        return "BUY"

    return "HOLD"


def legacy_rsi_signal(df, in_position=False):
    df = df.copy()
    df["rsi"] = rsi(df["close"])

    latest = df.iloc[-1]
    prev = df.iloc[-3]

    price_change = (latest["close"] - prev["close"]) / prev["close"]

    if in_position:
        if price_change > 0.001 or latest["rsi"] > 58:
            return "SELL"
        return "HOLD"

    if price_change < -0.001 or latest["rsi"] < 50:
        return "BUY"

    return "HOLD"
