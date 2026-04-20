import pandas as pd


def rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def ema(series, period=50):
    return series.ewm(span=period, adjust=False).mean()


def volatility(df, window=10):
    return df["close"].pct_change().rolling(window).std()


def volume_spike(df, window=20, threshold=1.5):
    """Returns True on the latest candle if volume is above threshold x average."""
    avg_vol = df["volume"].rolling(window).mean()
    return df["volume"].iloc[-1] > (avg_vol.iloc[-1] * threshold)