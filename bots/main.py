import time

import pandas as pd

from bots.config import DRY_RUN, SYMBOL, TIMEFRAME, TRADE_USD
from bots.exchange import get_exchange
from bots.logger import logger
from bots.strategy import generate_signal


def fetch_data(exchange, limit=50):
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"],
    )


def get_base_asset(symbol):
    return symbol.split("/")[0]


def buy(exchange, price):
    amount = TRADE_USD / price
    logger.info(f"BUY signal at {price} | amount={amount:.6f}")
    if not DRY_RUN:
        exchange.create_market_buy_order(SYMBOL, amount)


def sell(exchange, price):
    base_asset = get_base_asset(SYMBOL)

    if DRY_RUN:
        logger.info(f"SELL signal at {price} | dry-run, no order placed")
        return

    balance = exchange.fetch_balance()
    amount = float(balance.get(base_asset, {}).get("free", 0))

    if amount <= 0:
        logger.info(f"SELL signal at {price} | no {base_asset} balance available")
        return

    logger.info(f"SELL signal at {price} | amount={amount:.6f}")
    exchange.create_market_sell_order(SYMBOL, amount)


def run_bot(poll_interval=60):
    exchange = get_exchange()
    logger.info(f"Starting bot for {SYMBOL} on {TIMEFRAME} (dry_run={DRY_RUN})")

    while True:
        try:
            df = fetch_data(exchange)
            signal = generate_signal(df)
            price = df["close"].iloc[-1]

            logger.info(f"Signal: {signal} | Price: {price}")

            if signal == "BUY":
                buy(exchange, price)
            elif signal == "SELL":
                sell(exchange, price)

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as exc:
            logger.error(f"Error: {exc}")
            time.sleep(10)


if __name__ == "__main__":
    run_bot()
