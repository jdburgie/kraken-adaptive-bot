import argparse
import os
import sys
import time

import ccxt
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DEFAULT_FALLBACK_EXCHANGES = "coinbase,kraken"
DEFAULT_QUOTE_FALLBACKS = "USD,USDC,USDT"


def create_exchange(exchange_id):
    try:
        exchange_class = getattr(ccxt, exchange_id)
    except AttributeError as exc:
        raise ValueError(f"{exchange_id} is not a supported ccxt exchange id") from exc
    return exchange_class({"enableRateLimit": True})


def parse_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def candidate_symbols(symbol, quote_fallbacks):
    if "/" not in symbol:
        return [symbol]

    base, quote = symbol.split("/", 1)
    quotes = dedupe([quote, *quote_fallbacks])
    return [f"{base}/{candidate_quote}" for candidate_quote in quotes]


def short_error(exc):
    return " ".join(str(exc).split())[:500]


def select_market(exchange_ids, symbols):
    attempts = []

    for exchange_id in exchange_ids:
        try:
            exchange = create_exchange(exchange_id)
            exchange.load_markets()
        except Exception as exc:
            attempts.append(f"{exchange_id}: {short_error(exc)}")
            continue

        for symbol in symbols:
            if symbol in exchange.markets:
                return exchange, exchange_id, symbol, attempts

        attempts.append(f"{exchange_id}: none of {', '.join(symbols)} is available")

    attempt_text = "\n  - ".join(attempts)
    raise RuntimeError(f"Unable to find a working OHLCV market. Attempts:\n  - {attempt_text}")


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
    parser.add_argument(
        "--fallback-exchanges",
        default=DEFAULT_FALLBACK_EXCHANGES,
        help="Comma-separated exchange ids to try if the primary exchange is blocked or unavailable.",
    )
    parser.add_argument(
        "--quote-fallbacks",
        default=DEFAULT_QUOTE_FALLBACKS,
        help="Comma-separated quote assets to try when the requested symbol is unavailable.",
    )
    args = parser.parse_args()

    exchanges = dedupe([args.exchange, *parse_csv(args.fallback_exchanges)])
    symbols = candidate_symbols(args.symbol, parse_csv(args.quote_fallbacks))
    exchange, exchange_id, symbol, attempts = select_market(exchanges, symbols)

    if exchange_id != args.exchange or symbol != args.symbol:
        print(f"Using {exchange_id} {symbol} instead of {args.exchange} {args.symbol}")
    for attempt in attempts:
        print(f"Skipped {attempt}", file=sys.stderr)

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

    rows = fetch_ohlcv(exchange, symbol, args.timeframe, since, limit)
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} candles from {exchange_id} {symbol} {args.timeframe} to {args.output}")


if __name__ == "__main__":
    main()
