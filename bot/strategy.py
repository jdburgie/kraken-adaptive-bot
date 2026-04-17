from indicators import rsi, volatility
from logger import logger

def generate_signal(df):
    df = df.copy()

    df['rsi'] = rsi(df['close'])

    latest = df.iloc[-1]
    prev = df.iloc[-3]

    price_change = (latest['close'] - prev['close']) / prev['close']

    # DEBUG LOG
    logger.info(f"DEBUG → change: {price_change:.4f}, RSI: {latest['rsi']:.2f}")

    # VERY LOOSE CONDITIONS (FOR TESTING)
    if price_change < -0.005 or latest['rsi'] < 45:
        return "BUY"

    if price_change > 0.005 or latest['rsi'] > 55:
        return "SELL"

    return "HOLD"

# def generate_signal(df):
#     df = df.copy()

#     df['rsi'] = rsi(df['close'])
#     vol = volatility(df).iloc[-1]

#     latest = df.iloc[-1]
#     price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]

#     # ENTRY CONDITIONS
#     if (
#         price_change < -0.02 and   # was -0.03
#         latest['rsi'] < 40 and     # was 35
#         vol > 0.005                # was stricter
#     ):
#         return "BUY"

#     if latest['rsi'] < 45 and price_change < -0.015:
#         return "BUY"

#     if latest['rsi'] > 60 or price_change > 0.03:
#         return "SELL"
    
#     logger.info(f"DEBUG → change: {price_change:.4f}, RSI: {latest['rsi']:.2f}, vol: {vol:.4f}")

#     return "HOLD"