import unittest

import pandas as pd

from bots.strategy import generate_signal


class TestGenerateSignal(unittest.TestCase):
    def test_hold_when_not_enough_candles(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        self.assertEqual(generate_signal(df), "HOLD")

    def test_sell_on_large_price_increase(self):
        df = pd.DataFrame({"close": [100 + i for i in range(20)]})
        self.assertEqual(generate_signal(df), "SELL")

    def test_hold_when_baseline_is_zero(self):
        closes = [1] * 10 + [0] + [1] * 9
        df = pd.DataFrame({"close": closes})
        self.assertEqual(generate_signal(df), "HOLD")


if __name__ == "__main__":
    unittest.main()
