import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "AVAX/USD")
TRADE_USD = float(os.getenv("TRADE_USD", 20))
TIMEFRAME = os.getenv("TIMEFRAME", "5m")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}
