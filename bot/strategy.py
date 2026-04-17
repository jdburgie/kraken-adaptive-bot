from indicators import rsi, volatility

def generate_signal(df):
    df = df.copy()

    df['rsi'] = rsi(df['close'])
    vol = volatility(df).iloc[-1]

    latest = df.iloc[-1]
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]

    # ENTRY CONDITIONS
    if (
        price_change < -0.02 and   # was -0.03
        latest['rsi'] < 40 and     # was 35
        vol > 0.005                # was stricter
    ):
        return "BUY"

    if latest['rsi'] < 45 and price_change < -0.015:
        return "BUY"

    if latest['rsi'] > 60 or price_change > 0.03:
        return "SELL"
    
    return "HOLD"