"""
Backtesting engine for kraken-adaptive-bot.

Fetches up to 1 year of OHLCV data from Kraken, then walks forward
candle-by-candle applying the same strategy and risk logic as the
live bot — no lookahead bias.

Usage:
    python -m bots.backtest
    python -m bots.backtest --symbol ETH/USD --timeframe 1h --days 180
"""

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd

from bots.config import (
    EMA_PERIOD,
    RISK_PCT,
    STOP_LOSS_PCT,
    SYMBOL,
    TAKE_PROFIT_PCT,
    TIMEFRAME,
)
from bots.exchange import get_exchange
from bots.indicators import ema, rsi, volatility, volume_spike
from bots.risk import position_size, stop_loss, take_profit
from bots.strategy import MIN_CANDLES, generate_signal


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

TIMEFRAME_MINUTES = {
    "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440,
}


def fetch_historical(exchange, symbol, timeframe, days=365):
    """
    Fetch `days` worth of OHLCV candles from Kraken, paginating as needed.
    Returns a DataFrame sorted oldest-first.
    """
    tf_minutes = TIMEFRAME_MINUTES.get(timeframe)
    if tf_minutes is None:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    since_dt = datetime.now(tz=timezone.utc) - timedelta(days=days)
    since_ms = int(since_dt.timestamp() * 1000)

    all_candles = []
    limit = 720  # Kraken max per request
    fetched = 0

    print(f"Fetching {days} days of {timeframe} {symbol} data from Kraken...")

    while True:
        try:
            batch = exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since_ms, limit=limit
            )
        except Exception as e:
            print(f"  Error fetching batch: {e}")
            time.sleep(5)
            continue

        if not batch:
            break

        all_candles.extend(batch)
        fetched += len(batch)

        last_ts = batch[-1][0]
        # Estimate total candles expected
        total_expected = int(days * 24 * 60 / tf_minutes)
        pct = min(100, int(fetched / total_expected * 100))
        print(f"  {fetched:,} candles fetched ({pct}%) | up to {exchange.iso8601(last_ts)}", end="\r")

        if len(batch) < limit:
            break  # no more data

        # Advance since to just after last candle
        since_ms = last_ts + (tf_minutes * 60 * 1000)
        time.sleep(exchange.rateLimit / 1000)

    print(f"\n  Done — {len(all_candles):,} candles fetched.")

    df = pd.DataFrame(
        all_candles,
        columns=["time", "open", "high", "low", "close", "volume"]
    )
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Trade tracking
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_time: datetime
    entry_price: float
    amount: float
    stop_price: float
    take_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    @property
    def pnl_pct(self):
        if self.exit_price is None:
            return None
        return (self.exit_price - self.entry_price) / self.entry_price * 100

    @property
    def pnl_usd(self):
        if self.exit_price is None:
            return None
        return self.amount * (self.exit_price - self.entry_price)

    @property
    def is_win(self):
        return self.pnl_pct is not None and self.pnl_pct > 0


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(df: pd.DataFrame, initial_balance: float = 1000.0) -> dict:
    """
    Walk-forward simulation. At each candle we only look at data
    up to and including that candle — no lookahead.
    """
    balance = initial_balance
    position: Optional[Trade] = None
    trades: List[Trade] = []
    equity_curve = []

    for i in range(MIN_CANDLES, len(df)):
        window = df.iloc[: i + 1].copy()
        candle = df.iloc[i]
        price = candle["close"]
        ts = datetime.fromtimestamp(candle["time"] / 1000, tz=timezone.utc)

        # --- Manage open position ---
        if position is not None:
            if price <= position.stop_price:
                position.exit_time = ts
                position.exit_price = price
                position.exit_reason = "STOP_LOSS"
                balance += position.pnl_usd
                trades.append(position)
                position = None

            elif price >= position.take_price:
                position.exit_time = ts
                position.exit_price = price
                position.exit_reason = "TAKE_PROFIT"
                balance += position.pnl_usd
                trades.append(position)
                position = None

            else:
                signal = generate_signal(window)
                if signal == "SELL":
                    position.exit_time = ts
                    position.exit_price = price
                    position.exit_reason = "SIGNAL"
                    balance += position.pnl_usd
                    trades.append(position)
                    position = None

        # --- Look for entry ---
        if position is None:
            signal = generate_signal(window)
            if signal == "BUY" and balance > 10:
                trade_usd = position_size(balance, risk_pct=RISK_PCT)
                amount = trade_usd / price
                position = Trade(
                    entry_time=ts,
                    entry_price=price,
                    amount=amount,
                    stop_price=stop_loss(price, pct=STOP_LOSS_PCT),
                    take_price=take_profit(price, pct=TAKE_PROFIT_PCT),
                )

        # Track equity (mark open position to market)
        open_pnl = 0.0
        if position is not None:
            open_pnl = position.amount * (price - position.entry_price)
        equity_curve.append({
            "time": ts,
            "price": price,
            "equity": balance + open_pnl,
        })

    # Close any open position at end of data at last price
    if position is not None:
        last = df.iloc[-1]
        position.exit_time = datetime.fromtimestamp(last["time"] / 1000, tz=timezone.utc)
        position.exit_price = last["close"]
        position.exit_reason = "END_OF_DATA"
        balance += position.pnl_usd
        trades.append(position)

    return {
        "trades": trades,
        "final_balance": balance,
        "initial_balance": initial_balance,
        "equity_curve": pd.DataFrame(equity_curve),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(result: dict) -> dict:
    trades = result["trades"]
    eq = result["equity_curve"]
    initial = result["initial_balance"]
    final = result["final_balance"]

    if not trades:
        return {"error": "No trades executed during backtest period."}

    closed = [t for t in trades if t.exit_price is not None]
    wins = [t for t in closed if t.is_win]
    losses = [t for t in closed if not t.is_win]

    total_return = (final - initial) / initial * 100
    win_rate = len(wins) / len(closed) * 100 if closed else 0

    avg_win = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0

    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss = abs(sum(t.pnl_usd for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Max drawdown
    peak = eq["equity"].expanding().max()
    drawdown = (eq["equity"] - peak) / peak * 100
    max_drawdown = drawdown.min()

    # Exit reason breakdown
    reasons = {}
    for t in closed:
        reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1

    return {
        "total_trades": len(closed),
        "total_return_pct": total_return,
        "win_rate_pct": win_rate,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown,
        "gross_profit_usd": gross_profit,
        "gross_loss_usd": gross_loss,
        "net_pnl_usd": final - initial,
        "initial_balance": initial,
        "final_balance": final,
        "exit_reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(metrics: dict, symbol: str, timeframe: str, days: int):
    if "error" in metrics:
        print(f"\n⚠️  {metrics['error']}")
        return

    sep = "─" * 50
    print(f"\n{'═' * 50}")
    print(f"  BACKTEST RESULTS")
    print(f"  {symbol} | {timeframe} | Last {days} days")
    print(f"{'═' * 50}")
    print(f"  Starting balance : ${metrics['initial_balance']:>10,.2f}")
    print(f"  Final balance    : ${metrics['final_balance']:>10,.2f}")
    print(f"  Net P&L          : ${metrics['net_pnl_usd']:>+10,.2f}")
    print(f"  Total return     : {metrics['total_return_pct']:>+9.2f}%")
    print(sep)
    print(f"  Total trades     : {metrics['total_trades']:>10}")
    print(f"  Win rate         : {metrics['win_rate_pct']:>9.1f}%")
    print(f"  Avg win          : {metrics['avg_win_pct']:>+9.2f}%")
    print(f"  Avg loss         : {metrics['avg_loss_pct']:>+9.2f}%")
    print(f"  Profit factor    : {metrics['profit_factor']:>10.2f}")
    print(sep)
    print(f"  Max drawdown     : {metrics['max_drawdown_pct']:>+9.2f}%")
    print(sep)
    print(f"  Exit reasons:")
    for reason, count in metrics["exit_reasons"].items():
        print(f"    {reason:<20}: {count}")
    print(f"{'═' * 50}\n")


def save_chart(result: dict, symbol: str, timeframe: str, days: int):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        eq = result["equity_curve"]
        trades = result["trades"]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
        fig.suptitle(f"Backtest: {symbol} {timeframe} — Last {days} days", fontsize=13)

        # Price + trade markers
        ax1.plot(eq["time"], eq["price"], color="#aaaaaa", linewidth=0.8, label="Price")
        for t in trades:
            ax1.axvline(t.entry_time, color="#2ecc71", alpha=0.3, linewidth=0.6)
            if t.exit_time:
                color = "#2ecc71" if t.is_win else "#e74c3c"
                ax1.axvline(t.exit_time, color=color, alpha=0.4, linewidth=0.6)
        ax1.set_ylabel("Price (USD)")
        ax1.legend(loc="upper left", fontsize=8)

        # Equity curve
        initial = result["initial_balance"]
        ax2.plot(eq["time"], eq["equity"], color="#3498db", linewidth=1.2, label="Equity")
        ax2.axhline(initial, color="#888888", linestyle="--", linewidth=0.8, label="Starting balance")
        ax2.fill_between(eq["time"], initial, eq["equity"],
                         where=eq["equity"] >= initial, alpha=0.15, color="#2ecc71")
        ax2.fill_between(eq["time"], initial, eq["equity"],
                         where=eq["equity"] < initial, alpha=0.15, color="#e74c3c")
        ax2.set_ylabel("Portfolio Value (USD)")
        ax2.set_xlabel("Date")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax2.legend(loc="upper left", fontsize=8)

        plt.tight_layout()
        filename = f"backtest_{symbol.replace('/', '-')}_{timeframe}_{days}d.png"
        plt.savefig(filename, dpi=150)
        print(f"  Chart saved to: {filename}")
        plt.close()
    except ImportError:
        print("  (Install matplotlib to generate chart: pip install matplotlib)")
    except Exception as e:
        print(f"  Chart error: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Backtest the adaptive bot strategy")
    parser.add_argument("--symbol", default=SYMBOL, help="Trading pair (default: from .env)")
    parser.add_argument("--timeframe", default=TIMEFRAME, help="Candle timeframe (default: from .env)")
    parser.add_argument("--days", type=int, default=365, help="Days of history to test (default: 365)")
    parser.add_argument("--balance", type=float, default=1000.0, help="Starting balance in USD (default: 1000)")
    args = parser.parse_args()

    exchange = get_exchange()

    df = fetch_historical(exchange, args.symbol, args.timeframe, days=args.days)

    if len(df) < MIN_CANDLES + 10:
        print(f"Not enough data: got {len(df)} candles, need at least {MIN_CANDLES + 10}")
        sys.exit(1)

    print(f"\nRunning backtest on {len(df):,} candles...")
    result = run_backtest(df, initial_balance=args.balance)

    metrics = compute_metrics(result)
    print_report(metrics, args.symbol, args.timeframe, args.days)
    save_chart(result, args.symbol, args.timeframe, args.days)


if __name__ == "__main__":
    main()
