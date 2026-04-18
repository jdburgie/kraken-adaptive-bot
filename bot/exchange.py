import ccxt
try:
    from bot.config import API_KEY, API_SECRET
except ImportError:
    from config import API_KEY, API_SECRET

def get_exchange():
    return ccxt.kraken({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True
    })
