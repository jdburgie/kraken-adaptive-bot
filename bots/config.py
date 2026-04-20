import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "BTC/USD")
TRADE_USD = float(os.getenv("TRADE_USD", 50))
TIMEFRAME = os.getenv("TIMEFRAME", "5m")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}

# Risk management
RISK_PCT = float(os.getenv("RISK_PCT", 0.02))       # 2% of balance per trade
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.025))   # 2.5% stop loss
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.05))  # 5% take profit

# Trend filter
EMA_PERIOD = int(os.getenv("EMA_PERIOD", 50))

# Candles to fetch (must cover EMA period + strategy lookback)
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT", 100))
