import argparse
import os
import sys
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.market_data import load_ohlcv_csv
from bot.risk import units_for_fixed_risk
from bot.strategy import evaluate_trend_pullback_entry
from backtest.metrics import summarize_trades


def run_backtest(
    df,
    starting_balance=1000,
    risk_pct=0.01,
    max_position_pct=1.0,
    fee_rate=0.0026,
    max_hold_bars=20,
    min_net_reward_r=1.0,
    collect_diagnostics=False,
):
    balance = starting_balance
    trades = []
    diagnostics = Counter()
    warmup_bars = 250
    i = warmup_bars

    while i < len(df) - 1:
        window = df.iloc[: i + 1]
        setup, rejection_reason = evaluate_trend_pullback_entry(window)

        if not setup:
            if collect_diagnostics:
                diagnostics[rejection_reason] += 1
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
    parser.add_argument("--starting-balance", type=float, default=1000)
    parser.add_argument("--risk-pct", type=float, default=0.01)
    parser.add_argument("--max-position-pct", type=float, default=1.0)
    parser.add_argument("--fee-rate", type=float, default=0.0026)
    parser.add_argument("--max-hold-bars", type=int, default=20)
    parser.add_argument("--min-net-reward-r", type=float, default=1.0)
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()

    df = load_ohlcv_csv(args.csv)
    trades, metrics, diagnostics = run_backtest(
        df,
        starting_balance=args.starting_balance,
        risk_pct=args.risk_pct,
        max_position_pct=args.max_position_pct,
        fee_rate=args.fee_rate,
        max_hold_bars=args.max_hold_bars,
        min_net_reward_r=args.min_net_reward_r,
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
