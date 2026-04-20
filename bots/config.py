import os
from dotenv import load_dotenv

load_dotenv()

API_KEY    = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

SYMBOL    = os.getenv("SYMBOL",    "BTC/USD")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}

# ── Risk management ─────────────────────────────────────────────────────────
# RISK_PCT: fraction of account balance AT RISK per trade.
# Position size is calculated so that if stop loss is hit, we lose exactly
# RISK_PCT * balance.  Start at 0.01 (1%) while learning.
RISK_PCT      = float(os.getenv("RISK_PCT",      0.01))   # 1% of balance at risk
STOP_PCT      = float(os.getenv("STOP_PCT",      0.030))  # 3.0% trailing stop
TAKE_PCT      = float(os.getenv("TAKE_PCT",      0.08))   # 8% take profit

# ── Strategy parameters ──────────────────────────────────────────────────────
EMA_FAST      = int(os.getenv("EMA_FAST",   50))    # fast EMA (trend confirmation)
EMA_SLOW      = int(os.getenv("EMA_SLOW",   200))   # slow EMA (primary trend filter)
BB_PERIOD     = int(os.getenv("BB_PERIOD",  20))    # Bollinger Band period
BB_STD        = float(os.getenv("BB_STD",   2.0))   # Bollinger Band std multiplier
RSI_PERIOD    = int(os.getenv("RSI_PERIOD", 14))
RSI_BUY       = float(os.getenv("RSI_BUY",  42.0))  # enter when RSI below this
RSI_SELL      = float(os.getenv("RSI_SELL", 70.0))  # exit when RSI above this

# ── Candles ──────────────────────────────────────────────────────────────────
CANDLE_LIMIT  = int(os.getenv("CANDLE_LIMIT", 250))  # must exceed EMA_SLOW + buffer
