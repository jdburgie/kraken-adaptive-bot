import unittest
import pandas as pd
from bots.strategy import generate_signal, MIN_CANDLES


def make_df(closes, volumes=None):
    if volumes is None:
        volumes = [1000.0] * len(closes)
    return pd.DataFrame({"close": closes, "volume": volumes})


class TestGenerateSignal(unittest.TestCase):

    def test_hold_when_not_enough_candles(self):
        df = make_df([100.0] * 5)
        self.assertEqual(generate_signal(df), "HOLD")

    def test_hold_when_baseline_is_zero(self):
        closes = [1.0] * (MIN_CANDLES - 10) + [0.0] + [1.0] * 9 + [1.0] * (MIN_CANDLES - len([1.0] * (MIN_CANDLES - 10) + [0.0] + [1.0] * 9))
        # Simpler: just enough candles with a zero in baseline position
        closes = [1.0] * MIN_CANDLES
        closes[-(10)] = 0.0
        df = make_df(closes)
        self.assertEqual(generate_signal(df), "HOLD")

    def test_sell_on_rsi_overbought(self):
        # Steadily rising prices will produce high RSI
        closes = [100.0 + i * 2 for i in range(MIN_CANDLES)]
        df = make_df(closes)
        result = generate_signal(df)
        # Should be SELL or HOLD (not BUY) on overbought trend
        self.assertIn(result, ["SELL", "HOLD"])

    def test_hold_on_flat_market(self):
        closes = [100.0] * MIN_CANDLES
        df = make_df(closes)
        self.assertEqual(generate_signal(df), "HOLD")

    def test_no_buy_in_downtrend(self):
        # Downtrend: price consistently below EMA — should never BUY
        closes = [200.0 - i * 1.5 for i in range(MIN_CANDLES)]
        df = make_df(closes, volumes=[5000.0] * MIN_CANDLES)
        result = generate_signal(df)
        self.assertNotEqual(result, "BUY")


if __name__ == "__main__":
    unittest.main()
