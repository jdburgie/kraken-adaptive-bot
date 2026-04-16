from indicators import rsi, volatility

def generate_signal(df):
    df = df.copy()

    df['rsi'] = rsi(df['close'])
    vol = volatility(df).iloc[-1]

    latest = df.iloc[-1]
    price_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]

    # ENTRY CONDITIONS
    if (
        price_change < -0.03 and
        latest['rsi'] < 35 and
        vol > 0.01
    ):
        return "BUY"

    # EXIT CONDITIONS
    if latest['rsi'] > 65 or price_change > 0.05:
        return "SELL"

    return "HOLD"