import os
from dotenv import load_dotenv
# git check

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "AVAX/USD")
TRADE_USD = float(os.getenv("TRADE_USD", 20))

TIMEFRAME = "5m"