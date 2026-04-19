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


def evaluate_trend_pullback_entry(
    df,
    reward_risk=2.0,
    pullback_tolerance_pct=0.0,
    pullback_lookback_bars=1,
    volume_multiplier=1.0,
    require_prior_high_reclaim=True,
    breakout_lookback_bars=6,
    min_ema50_slope_pct=0.001,
    ema_slope_lookback_bars=24,
    max_extension_atr=0.75,
    min_body_atr=0.10,
):
    if len(df) < 200:
        return None, "not_enough_candles"

    regime = classify_regime(df)
    if regime != Regime.UPTREND:
        return None, f"regime_{regime.value.lower()}"

    indicator_columns = {"ema20", "ema50", "ema200", "atr14", "volume_sma20"}
    enriched = df if indicator_columns.issubset(df.columns) else add_core_indicators(df)
    latest = enriched.iloc[-1]
    previous = enriched.iloc[-2]

    required = ["ema20", "ema50", "ema200", "atr14", "volume_sma20"]
    if latest[required].isna().any():
        return None, "indicators_not_ready"

    if not (latest["ema20"] > latest["ema50"] > latest["ema200"]):
        return None, "weak_ema_stack"

    ema_slope_lookback_bars = max(1, int(ema_slope_lookback_bars))
    if len(enriched) <= ema_slope_lookback_bars:
        return None, "not_enough_slope_history"

    prior_ema50 = enriched["ema50"].iloc[-1 - ema_slope_lookback_bars]
    if prior_ema50 <= 0 or prior_ema50 != prior_ema50:
        return None, "indicators_not_ready"

    ema50_slope_pct = (latest["ema50"] - prior_ema50) / prior_ema50
    if ema50_slope_pct < min_ema50_slope_pct:
        return None, "weak_ema50_slope"

    pullback_lookback_bars = max(1, int(pullback_lookback_bars))
    recent = enriched.tail(pullback_lookback_bars)
    pullback_ceiling = recent["ema20"] * (1 + pullback_tolerance_pct)
    touched_ema20 = (recent["low"] <= pullback_ceiling).any()
    closed_green = latest["close"] > latest["open"]
    reclaimed_previous_high = latest["close"] > previous["high"]
    volume_confirmed = latest["volume"] > latest["volume_sma20"] * volume_multiplier
    extension_atr = (latest["close"] - latest["ema20"]) / latest["atr14"]
    body_atr = (latest["close"] - latest["open"]) / latest["atr14"]
    candle_range = latest["high"] - latest["low"]
    close_position = (
        (latest["close"] - latest["low"]) / candle_range
        if candle_range > 0
        else 0
    )

    if not touched_ema20:
        return None, "no_ema20_pullback"

    if not closed_green:
        return None, "not_green_candle"

    if body_atr < min_body_atr or close_position < 0.6:
        return None, "weak_bullish_candle"

    if require_prior_high_reclaim and not reclaimed_previous_high:
        return None, "no_prior_high_reclaim"

    if not volume_confirmed:
        return None, "no_volume_confirmation"

    if extension_atr > max_extension_atr:
        return None, "entry_too_extended"

    breakout_lookback_bars = max(0, int(breakout_lookback_bars))
    if breakout_lookback_bars:
        if len(enriched) <= breakout_lookback_bars:
            return None, "not_enough_breakout_history"

        prior_high = enriched["high"].iloc[-1 - breakout_lookback_bars : -1].max()
        if latest["close"] <= prior_high:
            return None, "no_local_high_breakout"

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


def find_trend_pullback_entry(
    df,
    reward_risk=2.0,
    pullback_tolerance_pct=0.0,
    pullback_lookback_bars=1,
    volume_multiplier=1.0,
    require_prior_high_reclaim=True,
    breakout_lookback_bars=6,
):
    setup, _ = evaluate_trend_pullback_entry(
        df,
        reward_risk=reward_risk,
        pullback_tolerance_pct=pullback_tolerance_pct,
        pullback_lookback_bars=pullback_lookback_bars,
        volume_multiplier=volume_multiplier,
        require_prior_high_reclaim=require_prior_high_reclaim,
        breakout_lookback_bars=breakout_lookback_bars,
    )
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
