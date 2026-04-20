"""
Backtesting engine — walk-forward simulation, no lookahead bias.

Data sources (tried in order):
  1. Yahoo Finance (yfinance) — up to 2 years of hourly data
  2. Kraken public REST API  — daily candles, up to 2 years

Usage:
    python -m bots.backtest
    python -m bots.backtest --days 365 --balance 1000 --risk 0.01
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd

from bots.config import (
    BB_PERIOD, BB_STD, EMA_FAST, EMA_SLOW,
    RISK_PCT, RSI_BUY, RSI_PERIOD, RSI_SELL,
    STOP_PCT, SYMBOL, TAKE_PCT, TIMEFRAME,
)
from bots.indicators import bollinger_bands, ema, rsi
from bots.risk import (
    position_size_usd, stop_loss_price,
    take_profit_price, update_trailing_stop,
)
from bots.strategy import MIN_CANDLES


# ── Data fetching ─────────────────────────────────────────────────────────────

def _kraken_symbol(symbol: str) -> str:
    mapping = {"BTC/USD": "XBTUSD", "ETH/USD": "ETHUSD", "SOL/USD": "SOLUSD",
               "XRP/USD": "XRPUSD", "ADA/USD": "ADAUSD"}
    return mapping.get(symbol, symbol.replace("/", ""))


def fetch_yfinance(symbol: str, days: int) -> pd.DataFrame:
    import yfinance as yf
    yf_sym = symbol.replace("/", "-")
    # yfinance hourly data goes back ~730 days
    period = f"{min(days, 729)}d"
    raw = yf.download(yf_sym, period=period, interval="1h", progress=False)
    if raw.empty:
        return pd.DataFrame()
    # Flatten multi-level columns
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]
    raw = raw.rename_axis("time").reset_index()
    raw["time"] = pd.to_datetime(raw["time"], utc=True)
    return raw[["time","open","high","low","close","volume"]].dropna().sort_values("time").reset_index(drop=True)


def fetch_kraken_daily(symbol: str, days: int) -> pd.DataFrame:
    import urllib.request, json
    pair = _kraken_symbol(symbol)
    url  = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440&since=0"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    if data.get("error"):
        raise RuntimeError(f"Kraken API error: {data['error']}")
    result_key = [k for k in data["result"] if k != "last"][0]
    candles    = data["result"][result_key]
    df = pd.DataFrame(candles, columns=["time","open","high","low","close","vwap","volume","trades"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df["time"] >= cutoff][["time","open","high","low","close","volume"]].sort_values("time").reset_index(drop=True)


def load_data(symbol: str, days: int) -> pd.DataFrame:
    print(f"Fetching data for {symbol} ({days} days)...")
    try:
        df = fetch_yfinance(symbol, days)
        if len(df) > 100:
            print(f"  yfinance: {len(df):,} hourly candles | {df['time'].iloc[0].date()} → {df['time'].iloc[-1].date()}")
            return df
    except Exception as e:
        print(f"  yfinance failed: {e}")

    try:
        df = fetch_kraken_daily(symbol, days)
        if len(df) > 10:
            print(f"  Kraken daily: {len(df):,} candles | {df['time'].iloc[0].date()} → {df['time'].iloc[-1].date()}")
            return df
    except Exception as e:
        print(f"  Kraken daily failed: {e}")

    raise RuntimeError("Could not fetch data from any source.")


# ── Trade dataclass ───────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_date: str
    entry_price: float
    amount: float
    stop_price: float
    take_price: float
    exit_date: Optional[str]  = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str]  = None

    @property
    def pnl_pct(self):
        return (self.exit_price - self.entry_price) / self.entry_price * 100 if self.exit_price else None

    @property
    def pnl_usd(self):
        return self.amount * (self.exit_price - self.entry_price) if self.exit_price else None

    @property
    def is_win(self):
        return self.pnl_pct is not None and self.pnl_pct > 0


# ── Walk-forward engine ───────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, initial_balance: float,
                 risk_pct: float, stop_pct: float, take_pct: float) -> dict:

    # Pre-compute indicators on full dataset (safe — we slice by index)
    df = df.copy()
    df["rsi_ind"]  = rsi(df["close"], period=RSI_PERIOD)
    df["ema_fast"] = ema(df["close"], period=EMA_FAST)
    df["ema_slow"] = ema(df["close"], period=EMA_SLOW)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger_bands(
        df["close"], period=BB_PERIOD, std_mult=BB_STD
    )

    balance     = initial_balance
    position    = None
    trail_stop  = None
    trades: List[Trade] = []
    equity      = []

    for i in range(MIN_CANDLES, len(df)):
        row   = df.iloc[i]
        price = float(row["close"])
        date  = str(row["time"])[:16]

        # Skip if indicators not yet warmed up
        for col in ("rsi_ind", "ema_fast", "ema_slow", "bb_lower"):
            if pd.isna(row[col]):
                equity.append(balance)
                continue

        # ── Manage open position ──────────────────────────────────────────────
        if position is not None:
            trail_stop = update_trailing_stop(trail_stop, price, stop_pct)

            if price <= trail_stop:
                position.exit_date = date; position.exit_price = price; position.exit_reason = "TRAIL_STOP"
                balance += position.pnl_usd; trades.append(position); position = None; trail_stop = None

            elif price >= position.take_price:
                position.exit_date = date; position.exit_price = price; position.exit_reason = "TAKE_PROFIT"
                balance += position.pnl_usd; trades.append(position); position = None; trail_stop = None

            elif row["rsi_ind"] > RSI_SELL:
                position.exit_date = date; position.exit_price = price; position.exit_reason = "RSI_EXIT"
                balance += position.pnl_usd; trades.append(position); position = None; trail_stop = None

        # ── Look for entry ────────────────────────────────────────────────────
        if position is None and balance > 10:
            strong_up   = price > row["ema_slow"] and row["ema_fast"] > row["ema_slow"]
            bb_touch    = row["low"] <= row["bb_lower"]
            rsi_low     = row["rsi_ind"] < RSI_BUY

            if strong_up and bb_touch and rsi_low:
                trade_usd = position_size_usd(balance, risk_pct, stop_pct)
                stop      = stop_loss_price(price, stop_pct)
                take      = take_profit_price(price, take_pct)
                position  = Trade(date, price, trade_usd / price, stop, take)
                trail_stop = stop

        open_pnl = position.amount * (price - position.entry_price) if position else 0.0
        equity.append(balance + open_pnl)

    # Close any open position at end of data
    if position is not None:
        last = df.iloc[-1]
        position.exit_date  = str(last["time"])[:16]
        position.exit_price = float(last["close"])
        position.exit_reason = "END_OF_DATA"
        balance += position.pnl_usd
        trades.append(position)

    return {
        "trades":          trades,
        "final_balance":   balance,
        "initial_balance": initial_balance,
        "equity_curve":    pd.DataFrame({"equity": equity}),
    }


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(result: dict) -> dict:
    trades  = result["trades"]
    eq      = result["equity_curve"]["equity"]
    initial = result["initial_balance"]
    final   = result["final_balance"]

    if not trades:
        return {"error": "No trades executed."}

    wins   = [t for t in trades if t.is_win]
    losses = [t for t in trades if not t.is_win and t.pnl_usd is not None]
    gp     = sum(t.pnl_usd for t in wins)   if wins   else 0
    gl     = abs(sum(t.pnl_usd for t in losses)) if losses else 0

    peak   = eq.expanding().max()
    max_dd = ((eq - peak) / peak * 100).min()

    reasons = {}
    for t in trades:
        reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1

    return {
        "total_trades":     len(trades),
        "total_return_pct": (final - initial) / initial * 100,
        "win_rate_pct":     len(wins) / len(trades) * 100,
        "avg_win_pct":      sum(t.pnl_pct for t in wins)   / len(wins)   if wins   else 0,
        "avg_loss_pct":     sum(t.pnl_pct for t in losses) / len(losses) if losses else 0,
        "profit_factor":    gp / gl if gl > 0 else float("inf"),
        "max_drawdown_pct": max_dd,
        "net_pnl_usd":      final - initial,
        "final_balance":    final,
        "initial_balance":  initial,
        "exit_reasons":     reasons,
    }


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(metrics: dict, symbol: str, days: int,
                 risk_pct: float, stop_pct: float, take_pct: float):
    if "error" in metrics:
        print(f"\n⚠️  {metrics['error']}")
        return

    sep = "─" * 54
    print(f"\n{'═'*54}")
    print(f"  BACKTEST RESULTS  |  {symbol}  |  {days} days")
    print(f"  Risk: {risk_pct*100:.1f}%/trade  Stop: {stop_pct*100:.1f}%  Take: {take_pct*100:.1f}%")
    print(f"{'═'*54}")
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
    print(f"  Exit breakdown:")
    for reason, count in sorted(metrics["exit_reasons"].items()):
        print(f"    {reason:<20}: {count}")
    print(f"{'═'*54}\n")


def save_chart(result: dict, symbol: str, days: int):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        eq     = result["equity_curve"]["equity"]
        trades = result["trades"]
        init   = result["initial_balance"]

        fig, ax = plt.subplots(figsize=(14, 5))
        fig.suptitle(f"Equity Curve — {symbol} ({days} days)", fontsize=12)

        ax.plot(eq.values, color="#3498db", linewidth=1.2, label="Portfolio")
        ax.axhline(init, color="#888", linestyle="--", linewidth=0.8, label="Starting balance")
        ax.fill_between(range(len(eq)), init, eq.values,
                        where=eq.values >= init, alpha=0.12, color="#2ecc71")
        ax.fill_between(range(len(eq)), init, eq.values,
                        where=eq.values < init, alpha=0.12, color="#e74c3c")
        ax.set_ylabel("Portfolio Value ($)")
        ax.set_xlabel("Candles")
        ax.legend(fontsize=9)

        fname = f"backtest_{symbol.replace('/','-')}_{days}d.png"
        plt.tight_layout()
        plt.savefig(fname, dpi=150)
        print(f"  Chart saved: {fname}")
        plt.close()
    except ImportError:
        print("  (pip install matplotlib to generate chart)")
    except Exception as e:
        print(f"  Chart error: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Backtest the hybrid strategy")
    parser.add_argument("--symbol",  default=SYMBOL,   help="e.g. BTC/USD")
    parser.add_argument("--days",    type=int, default=730)
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--risk",    type=float, default=RISK_PCT, help="Risk pct per trade (e.g. 0.01)")
    parser.add_argument("--stop",    type=float, default=STOP_PCT)
    parser.add_argument("--take",    type=float, default=TAKE_PCT)
    args = parser.parse_args()

    df = load_data(args.symbol, args.days)
    if len(df) < MIN_CANDLES + 10:
        print(f"Not enough data ({len(df)} candles, need {MIN_CANDLES + 10})")
        sys.exit(1)

    print(f"Running backtest on {len(df):,} candles...")
    result  = run_backtest(df, args.balance, args.risk, args.stop, args.take)
    metrics = compute_metrics(result)
    print_report(metrics, args.symbol, args.days, args.risk, args.stop, args.take)
    save_chart(result, args.symbol, args.days)


if __name__ == "__main__":
    main()
