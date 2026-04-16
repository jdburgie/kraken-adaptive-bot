import time
import pandas as pd

from exchange import get_exchange
from config import SYMBOL, TIMEFRAME, TRADE_USD
from strategy import generate_signal
from logger import logger

exchange = get_exchange()

in_position = False
entry_price = None


def fetch_data():
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50)
    df = pd.DataFrame(ohlcv, columns=[
        "time", "open", "high", "low", "close", "volume"
    ])
    return df


def get_balance():
    balance = exchange.fetch_balance()
    return balance['USD']['free']


def buy(price):
    logger.info(f"BUY signal at {price}")
    # exchange.create_market_buy_order(SYMBOL, TRADE_USD / price)


def sell(price):
    logger.info(f"SELL signal at {price}")
    # exchange.create_market_sell_order(SYMBOL, "all")


while True:
    try:
        df = fetch_data()
        signal = generate_signal(df)
        price = df['close'].iloc[-1]

        logger.info(f"Signal: {signal} | Price: {price}")

        if signal == "BUY":
            buy(price)

        elif signal == "SELL":
            sell(price)

        time.sleep(60)

    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(10)