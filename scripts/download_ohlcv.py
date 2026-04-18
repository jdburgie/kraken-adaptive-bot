import argparse
import os
import sys
import time

import ccxt
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def create_exchange(exchange_id):
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def fetch_ohlcv(exchange, symbol, timeframe, since, limit):
    rows = []
    next_since = since
    request_limit = min(1000, limit)

    while len(rows) < limit:
        batch = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=next_since,
            limit=min(request_limit, limit - len(rows)),
        )

        if not batch:
            break

        new_rows = [row for row in batch if not rows or row[0] > rows[-1][0]]
        if not new_rows:
            break

        rows.extend(new_rows)
        next_since = rows[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)

    return rows


def main():
    parser = argparse.ArgumentParser(description="Download OHLCV candles for backtesting.")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="SOL/USDT")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--output", default="data/sol_ohlcv.csv")
    args = parser.parse_args()

    exchange = create_exchange(args.exchange)
    exchange.load_markets()

    if args.symbol not in exchange.markets:
        raise ValueError(f"{args.symbol} is not available on {args.exchange}")

    since = exchange.milliseconds() - args.days * 24 * 60 * 60 * 1000
    candles_per_day = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "1h": 24,
        "4h": 6,
        "1d": 1,
    }.get(args.timeframe, 288)
    limit = args.days * candles_per_day

    rows = fetch_ohlcv(exchange, args.symbol, args.timeframe, since, limit)
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} candles from {args.exchange} {args.symbol} {args.timeframe} to {args.output}")


if __name__ == "__main__":
    main()
