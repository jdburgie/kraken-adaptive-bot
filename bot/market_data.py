import pandas as pd


REQUIRED_COLUMNS = ["time", "open", "high", "low", "close", "volume"]


def load_ohlcv_csv(path):
    df = pd.read_csv(path)

    if "timestamp" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"timestamp": "time"})

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {', '.join(missing)}")

    df = df[REQUIRED_COLUMNS].copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=REQUIRED_COLUMNS).sort_values("time").reset_index(drop=True)
    return df
