import pandas as pd


def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.where(delta > 0, 0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def bollinger_bands(series, period=20, std_mult=2.0):
    """Returns (upper, mid, lower) as a tuple of Series."""
    mid   = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid + std_mult * sigma, mid, mid - std_mult * sigma


def atr(df, period=14):
    """Average True Range — measures candle-level volatility."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def volume_spike(df, window=20, threshold=1.5):
    avg = df["volume"].rolling(window).mean()
    return df["volume"].iloc[-1] > avg.iloc[-1] * threshold
