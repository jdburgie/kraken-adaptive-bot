import time
import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.config import SYMBOL, TIMEFRAME, TRADE_USD
from bot.exchange import get_exchange
from bot.logger import logger
from bot.paper import PaperTrader
from bot.strategy import find_trend_pullback_entry

exchange = get_exchange()

paper = PaperTrader(starting_balance=100)

def fetch_data():
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=250)
    df = pd.DataFrame(ohlcv, columns=[
        "time", "open", "high", "low", "close", "volume"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df


def get_balance():
    balance = exchange.fetch_balance()
    return balance['USD']['free']


def buy(setup):
    result = paper.buy(SYMBOL, setup.entry, TRADE_USD, stop=setup.stop, target=setup.target)
    logger.info(result)


def sell(price):
    result = paper.sell(SYMBOL, price)
    logger.info(result)


while True:
    try:
        df = fetch_data()
        price = df['close'].iloc[-1]
        position = paper.position

        if position is not None:
            stop = position.get("stop")
            target = position.get("target")

            if stop is not None and price <= stop:
                logger.info(f"Signal: SELL_STOP | Price: {price} | Stop: {stop}")
                sell(price)
            elif target is not None and price >= target:
                logger.info(f"Signal: SELL_TARGET | Price: {price} | Target: {target}")
                sell(price)
            else:
                logger.info(f"Signal: HOLD | Price: {price}")

        else:
            setup = find_trend_pullback_entry(df)

            if setup:
                logger.info(
                    f"Signal: BUY | Entry: {setup.entry:.4f} | "
                    f"Stop: {setup.stop:.4f} | Target: {setup.target:.4f}"
                )
                buy(setup)
            else:
                logger.info(f"Signal: HOLD | Price: {price}")

        status = paper.status()
        logger.info(f"Balance: {status['balance']:.2f} | Position: {status['position']}")

        time.sleep(60)

    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(10)
