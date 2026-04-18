import ccxt

from bots.config import API_KEY, API_SECRET


def get_exchange():
    return ccxt.kraken(
        {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "enableRateLimit": True,
        }
    )
