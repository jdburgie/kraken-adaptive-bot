import time

import pandas as pd

from bots.config import SYMBOL, TIMEFRAME
from bots.exchange import get_exchange
from bots.logger import logger
from bots.strategy import generate_signal

exchange = get_exchange()


def fetch_data(limit=50):
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=limit)
    return pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"],
    )


def buy(price):
    logger.info(f"BUY signal at {price}")
    # exchange.create_market_buy_order(SYMBOL, TRADE_USD / price)


def sell(price):
    logger.info(f"SELL signal at {price}")
    # exchange.create_market_sell_order(SYMBOL, "all")


def run_bot(poll_interval=60):
    while True:
        try:
            df = fetch_data()
            signal = generate_signal(df)
            price = df["close"].iloc[-1]

            logger.info(f"Signal: {signal} | Price: {price}")

            if signal == "BUY":
                buy(price)
            elif signal == "SELL":
                sell(price)

            time.sleep(poll_interval)
        except Exception as exc:
            logger.error(f"Error: {exc}")
            time.sleep(10)


if __name__ == "__main__":
    run_bot()
