import ccxt

from bots.config import API_KEY, API_SECRET, DRY_RUN


def get_exchange():
    config = {"enableRateLimit": True}

    # API credentials are required for private endpoints (balances/orders).
    # Keep dry-run mode usable even when keys are not configured.
    if API_KEY and API_SECRET:
        config["apiKey"] = API_KEY
        config["secret"] = API_SECRET
    elif not DRY_RUN:
        raise RuntimeError("KRAKEN_API_KEY and KRAKEN_API_SECRET are required when DRY_RUN=false")

    return ccxt.kraken(config)
