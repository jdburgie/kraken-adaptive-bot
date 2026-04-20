import argparse
import os
import sys
from collections import Counter

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.market_data import load_ohlcv_csv
from bot.risk import units_for_fixed_risk
from bot.indicators import add_core_indicators
from bot.strategy import evaluate_trend_pullback_entry
from backtest.metrics import summarize_trades


def filter_date_range(df, start_date=None, end_date=None):
    filtered = df

    if start_date:
        start = pd.to_datetime(start_date)
        filtered = filtered[filtered["time"] >= start]

    if end_date:
        end = pd.to_datetime(end_date)
        end_date_text = str(end_date)
        if "T" not in end_date_text and " " not in end_date_text and end.time() == pd.Timestamp(0).time():
            filtered = filtered[filtered["time"] < end + pd.Timedelta(days=1)]
        else:
            filtered = filtered[filtered["time"] <= end]

    return filtered.reset_index(drop=True)


def benchmark_gate_reason(
    benchmark_df,
    current_time,
    min_ema50_slope_pct=0.001,
    ema_slope_lookback_bars=24,
    require_ema_stack=True,
):
    if benchmark_df is None:
        return None

    if benchmark_df.empty:
        return "benchmark_not_ready"

    index = benchmark_df["time"].searchsorted(pd.to_datetime(current_time), side="right") - 1
    ema_slope_lookback_bars = max(1, int(ema_slope_lookback_bars))

    if index < ema_slope_lookback_bars:
        return "benchmark_not_ready"

    latest = benchmark_df.iloc[index]
    prior = benchmark_df.iloc[index - ema_slope_lookback_bars]
    required = ["ema20", "ema50", "ema200"]

    if latest[required].isna().any() or pd.isna(prior["ema50"]):
        return "benchmark_not_ready"

    if require_ema_stack and not (latest["ema20"] > latest["ema50"] > latest["ema200"]):
        return "benchmark_weak_ema_stack"

    if prior["ema50"] <= 0:
        return "benchmark_not_ready"

    ema50_slope_pct = (latest["ema50"] - prior["ema50"]) / prior["ema50"]
    if ema50_slope_pct < min_ema50_slope_pct:
        return "benchmark_weak_ema50_slope"

    return None


def run_backtest(
    df,
    starting_balance=1000,
    risk_pct=0.01,
    max_position_pct=1.0,
    fee_rate=0.0026,
    max_hold_bars=20,
    min_net_reward_r=1.0,
    reward_risk=2.0,
    stop_mode="atr",
    swing_lookback_bars=6,
    swing_stop_buffer_atr=0.25,
    pullback_tolerance_pct=0.0,
    pullback_lookback_bars=1,
    volume_multiplier=1.0,
    require_prior_high_reclaim=True,
    breakout_lookback_bars=6,
    min_ema50_slope_pct=0.001,
    ema_slope_lookback_bars=24,
    max_extension_atr=0.75,
    min_body_atr=0.10,
    benchmark_df=None,
    benchmark_min_ema50_slope_pct=0.001,
    benchmark_ema_slope_lookback_bars=24,
    benchmark_require_ema_stack=True,
    collect_diagnostics=False,
):
    df = add_core_indicators(df)
    if benchmark_df is not None:
        benchmark_df = add_core_indicators(benchmark_df)

    balance = starting_balance
    trades = []
    diagnostics = Counter()
    warmup_bars = 250
    i = warmup_bars

    while i < len(df) - 1:
        window = df.iloc[: i + 1]
        setup, rejection_reason = evaluate_trend_pullback_entry(
            window,
            reward_risk=reward_risk,
            stop_mode=stop_mode,
            swing_lookback_bars=swing_lookback_bars,
            swing_stop_buffer_atr=swing_stop_buffer_atr,
            pullback_tolerance_pct=pullback_tolerance_pct,
            pullback_lookback_bars=pullback_lookback_bars,
            volume_multiplier=volume_multiplier,
            require_prior_high_reclaim=require_prior_high_reclaim,
            breakout_lookback_bars=breakout_lookback_bars,
            min_ema50_slope_pct=min_ema50_slope_pct,
            ema_slope_lookback_bars=ema_slope_lookback_bars,
            max_extension_atr=max_extension_atr,
            min_body_atr=min_body_atr,
        )

        if not setup:
            if collect_diagnostics:
                diagnostics[rejection_reason] += 1
            i += 1
            continue

        benchmark_rejection_reason = benchmark_gate_reason(
            benchmark_df,
            window.iloc[-1]["time"],
            min_ema50_slope_pct=benchmark_min_ema50_slope_pct,
            ema_slope_lookback_bars=benchmark_ema_slope_lookback_bars,
            require_ema_stack=benchmark_require_ema_stack,
        )
        if benchmark_rejection_reason:
            if collect_diagnostics:
                diagnostics[benchmark_rejection_reason] += 1
            i += 1
            continue

        units = units_for_fixed_risk(
            balance,
            setup.entry,
            setup.stop,
            risk_pct,
            max_position_pct=max_position_pct,
        )
        if units <= 0:
            if collect_diagnostics:
                diagnostics["invalid_position_size"] += 1
            i += 1
            continue

        entry_fee = setup.entry * units * fee_rate
        stop_fee = setup.stop * units * fee_rate
        target_fee = setup.target * units * fee_rate
        net_stop_loss = abs((setup.stop - setup.entry) * units - entry_fee - stop_fee)
        net_target_profit = (setup.target - setup.entry) * units - entry_fee - target_fee

        if net_stop_loss <= 0 or net_target_profit / net_stop_loss < min_net_reward_r:
            if collect_diagnostics:
                diagnostics["poor_net_reward_after_fees"] += 1
            i += 1
            continue

        exit_price = None
        exit_reason = None
        exit_index = None

        future = df.iloc[i + 1 : min(i + 1 + max_hold_bars, len(df))]

        for index, row in future.iterrows():
            hit_stop = row["low"] <= setup.stop
            hit_target = row["high"] >= setup.target

            if hit_stop and hit_target:
                exit_price = setup.stop
                exit_reason = "stop_and_target_same_bar_stop_first"
            elif hit_stop:
                exit_price = setup.stop
                exit_reason = "stop"
            elif hit_target:
                exit_price = setup.target
                exit_reason = "target"

            if exit_price is not None:
                exit_index = index
                break

        if exit_price is None:
            last = future.iloc[-1]
            exit_price = float(last["close"])
            exit_reason = "time"
            exit_index = future.index[-1]

        exit_fee = exit_price * units * fee_rate
        pnl = (exit_price - setup.entry) * units - entry_fee - exit_fee
        balance += pnl

        trades.append(
            {
                "entry_time": window.iloc[-1]["time"],
                "exit_time": df.iloc[exit_index]["time"],
                "entry": setup.entry,
                "exit": float(exit_price),
                "stop": setup.stop,
                "target": setup.target,
                "units": units,
                "pnl": pnl,
                "exit_reason": exit_reason,
                "reason": setup.reason,
            }
        )

        i = int(exit_index) + 1

    return trades, summarize_trades(trades, starting_balance), diagnostics


def main():
    parser = argparse.ArgumentParser(description="Backtest the trend pullback strategy.")
    parser.add_argument("csv", help="Path to an OHLCV CSV with time/open/high/low/close/volume columns.")
    parser.add_argument("--start-date", help="Only backtest candles on or after this date/time.")
    parser.add_argument("--end-date", help="Only backtest candles on or before this date/time.")
    parser.add_argument("--starting-balance", type=float, default=1000)
    parser.add_argument("--risk-pct", type=float, default=0.01)
    parser.add_argument("--max-position-pct", type=float, default=1.0)
    parser.add_argument("--fee-rate", type=float, default=0.0026)
    parser.add_argument("--max-hold-bars", type=int, default=20)
    parser.add_argument("--min-net-reward-r", type=float, default=1.0)
    parser.add_argument("--reward-risk", type=float, default=2.0)
    parser.add_argument("--stop-mode", choices=["atr", "swing-low"], default="atr")
    parser.add_argument("--swing-lookback-bars", type=int, default=6)
    parser.add_argument("--swing-stop-buffer-atr", type=float, default=0.25)
    parser.add_argument("--pullback-tolerance-pct", type=float, default=0.0)
    parser.add_argument("--pullback-lookback-bars", type=int, default=1)
    parser.add_argument("--volume-multiplier", type=float, default=1.0)
    parser.add_argument("--no-prior-high-reclaim", action="store_true")
    parser.add_argument("--breakout-lookback-bars", type=int, default=6)
    parser.add_argument("--min-ema50-slope-pct", type=float, default=0.001)
    parser.add_argument("--ema-slope-lookback-bars", type=int, default=24)
    parser.add_argument("--max-extension-atr", type=float, default=0.75)
    parser.add_argument("--min-body-atr", type=float, default=0.10)
    parser.add_argument("--benchmark-csv", help="Optional benchmark OHLCV CSV used as a market regime gate.")
    parser.add_argument("--benchmark-min-ema50-slope-pct", type=float, default=0.001)
    parser.add_argument("--benchmark-ema-slope-lookback-bars", type=int, default=24)
    parser.add_argument("--no-benchmark-ema-stack", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()

    df = load_ohlcv_csv(args.csv)
    df = filter_date_range(df, args.start_date, args.end_date)
    benchmark_df = None
    if args.benchmark_csv:
        benchmark_df = load_ohlcv_csv(args.benchmark_csv)
        benchmark_df = filter_date_range(benchmark_df, args.start_date, args.end_date)

    trades, metrics, diagnostics = run_backtest(
        df,
        starting_balance=args.starting_balance,
        risk_pct=args.risk_pct,
        max_position_pct=args.max_position_pct,
        fee_rate=args.fee_rate,
        max_hold_bars=args.max_hold_bars,
        min_net_reward_r=args.min_net_reward_r,
        reward_risk=args.reward_risk,
        stop_mode=args.stop_mode,
        swing_lookback_bars=args.swing_lookback_bars,
        swing_stop_buffer_atr=args.swing_stop_buffer_atr,
        pullback_tolerance_pct=args.pullback_tolerance_pct,
        pullback_lookback_bars=args.pullback_lookback_bars,
        volume_multiplier=args.volume_multiplier,
        require_prior_high_reclaim=not args.no_prior_high_reclaim,
        breakout_lookback_bars=args.breakout_lookback_bars,
        min_ema50_slope_pct=args.min_ema50_slope_pct,
        ema_slope_lookback_bars=args.ema_slope_lookback_bars,
        max_extension_atr=args.max_extension_atr,
        min_body_atr=args.min_body_atr,
        benchmark_df=benchmark_df,
        benchmark_min_ema50_slope_pct=args.benchmark_min_ema50_slope_pct,
        benchmark_ema_slope_lookback_bars=args.benchmark_ema_slope_lookback_bars,
        benchmark_require_ema_stack=not args.no_benchmark_ema_stack,
        collect_diagnostics=args.diagnostics,
    )

    print(f"Trades: {metrics['trades']}")
    print(f"Wins: {metrics['wins']} | Losses: {metrics['losses']} | Win rate: {metrics['win_rate']:.2%}")
    print(f"Net PnL: {metrics['net_pnl']:.2f}")
    print(f"Ending balance: {metrics['ending_balance']:.2f}")
    print(f"Return: {metrics['return_pct']:.2%}")
    print(f"Profit factor: {metrics['profit_factor']:.2f}")
    print(f"Max drawdown: {metrics['max_drawdown_pct']:.2%}")
    print(f"Expectancy/trade: {metrics['expectancy']:.2f}")

    if trades:
        print("Recent trades:")
        for trade in trades[-5:]:
            print(
                f"{trade['entry_time']} -> {trade['exit_time']} | "
                f"{trade['exit_reason']} | PnL {trade['pnl']:.2f}"
            )

    if args.diagnostics:
        print("Diagnostics:")
        for reason, count in diagnostics.most_common():
            print(f"{reason}: {count}")


if __name__ == "__main__":
    main()
