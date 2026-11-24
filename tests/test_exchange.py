"""Runnable check for the DRY_RUN credential gate: python tests/test_exchange.py"""
import os
import sys

os.environ.setdefault("SYMBOL", "BTC/USD")  # bot.config reads SYMBOL at import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.exchange import resolve_credentials

# keys present -> auth attached, in either mode
assert resolve_credentials("k", "s", True) == {"apiKey": "k", "secret": "s"}
assert resolve_credentials("k", "s", False) == {"apiKey": "k", "secret": "s"}

# no keys + dry run -> empty config (bot still fetches public OHLCV keyless)
assert resolve_credentials("", "", True) == {}
assert resolve_credentials(None, None, True) == {}

# no (or partial) keys + live -> refuse to build the client
for bad in (("", ""), (None, None), ("k", ""), ("", "s")):
    try:
        resolve_credentials(bad[0], bad[1], False)
    except RuntimeError:
        pass
    else:
        raise AssertionError(f"live mode without full keys must raise: {bad!r}")

print("exchange credential gate: OK")
