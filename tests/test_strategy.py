import unittest
import pandas as pd
import numpy as np
from bots.strategy import generate_signal, MIN_CANDLES


def flat_df(price, n, volume=1000.0):
    return pd.DataFrame({
        "open":   [price] * n,
        "high":   [price * 1.001] * n,
        "low":    [price * 0.999] * n,
        "close":  [price] * n,
        "volume": [volume] * n,
    })


class TestGenerateSignal(unittest.TestCase):

    def test_hold_when_not_enough_candles(self):
        df = flat_df(50000, 10)
        self.assertEqual(generate_signal(df), "HOLD")

    def test_hold_on_flat_market(self):
        df = flat_df(50000, MIN_CANDLES + 10)
        self.assertEqual(generate_signal(df), "HOLD")

    def test_no_buy_in_downtrend(self):
        """Price below both EMAs — should never BUY."""
        # Steadily declining prices — price will be below slow EMA
        prices = [100_000 - i * 200 for i in range(MIN_CANDLES + 10)]
        df = pd.DataFrame({
            "open":   prices, "high": [p * 1.001 for p in prices],
            "low":    [p * 0.999 for p in prices], "close": prices,
            "volume": [1000.0] * len(prices),
        })
        self.assertNotEqual(generate_signal(df), "BUY")

    def test_sell_when_rsi_overbought(self):
        """Rapidly rising prices push RSI above RSI_SELL — expect SELL or HOLD, never BUY."""
        prices = [50_000 + i * 500 for i in range(MIN_CANDLES + 10)]
        df = pd.DataFrame({
            "open":   prices, "high": [p * 1.002 for p in prices],
            "low":    [p * 0.998 for p in prices], "close": prices,
            "volume": [1000.0] * len(prices),
        })
        result = generate_signal(df)
        self.assertIn(result, ["SELL", "HOLD"])

    def test_returns_valid_signal(self):
        df = flat_df(50000, MIN_CANDLES + 20)
        self.assertIn(generate_signal(df), ["BUY", "SELL", "HOLD"])


if __name__ == "__main__":
    unittest.main()
