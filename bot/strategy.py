from indicators import rsi, volatility
from logger import logger

def generate_signal(df, in_position=False):

    df = df.copy()
    df['rsi'] = rsi(df['close'])

    latest = df.iloc[-1]
    prev = df.iloc[-3]

    price_change = (
        latest['close'] - prev['close']
    ) / prev['close']

    from bot.logger import logger

    logger.info(
        f"DEBUG → change: {price_change:.4f}, RSI: {latest['rsi']:.2f}"
    )

    # IF HOLDING A POSITION:
    if in_position:

        # SELL FIRST
        if price_change > 0.001 or latest['rsi'] > 58:
            return "SELL"

        return "HOLD"

    # IF NOT IN POSITION:
    else:

        if price_change < -0.001 or latest['rsi'] < 50:
            return "BUY"

        return "HOLD"
    