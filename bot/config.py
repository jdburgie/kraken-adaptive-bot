import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

# Paper mode by default. Must be explicitly disabled to trade real money,
# and real trading requires API keys (enforced in exchange.get_exchange).
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}

SYMBOL = os.environ["SYMBOL"]

if not SYMBOL:
    raise ValueError("SYMBOL not set in environment")

TRADE_USD = float(os.getenv("TRADE_USD", 20))

TIMEFRAME = "5m"