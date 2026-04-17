import time
import pandas as pd
from paper import PaperTrader

from exchange import get_exchange
from config import SYMBOL, TIMEFRAME, TRADE_USD
from strategy import generate_signal
from logger import logger

exchange = get_exchange()

in_position = False
entry_price = None

paper = PaperTrader(starting_balance=100)

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
    result = paper.buy(price, TRADE_USD)
    logger.info(result)


def sell(price):
    result = paper.sell(price)
    logger.info(result)


while True:
    try:
        df = fetch_data()
        signal = generate_signal(df)
        price = df['close'].iloc[-1]

        logger.info(f"Signal: {signal} | Price: {price}")

        if signal == "BUY" and not paper.position:
            buy(price)

        elif signal == "SELL" and paper.position:
            sell(price)
        
        else:
            logger.info("Heartbeat: loop running")

        status = paper.status()
        logger.info(f"Balance: {status['balance']:.2f} | Position: {status['position']}")

        # time.sleep(60)
        time.sleep(10)

    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(10)