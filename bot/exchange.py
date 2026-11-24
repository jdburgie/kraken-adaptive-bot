import ccxt
try:
    from bot.config import API_KEY, API_SECRET, DRY_RUN
except ImportError:
    from config import API_KEY, API_SECRET, DRY_RUN


def resolve_credentials(api_key, api_secret, dry_run):
    """ccxt auth config from keys. Refuse live trading without keys."""
    if api_key and api_secret:
        return {"apiKey": api_key, "secret": api_secret}
    if not dry_run:
        raise RuntimeError(
            "KRAKEN_API_KEY and KRAKEN_API_SECRET are required when DRY_RUN=false"
        )
    return {}


def get_exchange():
    config = {"enableRateLimit": True}
    config.update(resolve_credentials(API_KEY, API_SECRET, DRY_RUN))
    return ccxt.kraken(config)
