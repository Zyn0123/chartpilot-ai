import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from market_data import MARKETS, PERIODS, prepare_history, fetch_history, age_notice


class MarketDataTests(unittest.TestCase):
    def sample(self, n=75):
        dates = pd.date_range("2026-10-20 09:00:00", periods=n, freq="5min", tz="UTC", name="Datetime")
        close = [100.0 + i * .03 for i in range(n)]
        return pd.DataFrame({
            "Open": [v-.05 for v in close],
            "High": [v+.2 for v in close],
            "Low": [v-.2 for v in close],
            "Close": close,
            "Volume": [120+i for i in range(n)],
        }, index=dates)

    def test_normalize_yahoo_bars(self):
        df = prepare_history(self.sample(), "GC=F")
        self.assertEqual(len(df),75)
        self.assertEqual(set(["open","high","low","close","time"]) - set(df.columns), set())
        self.assertTrue(df["time"].is_monotonic_increasing)

    def test_reject_short_feed(self):
        with self.assertRaises(ValueError):
            prepare_history(self.sample(50), "GC=F")

    def test_missing_fields(self):
        with self.assertRaises(ValueError):
            prepare_history(self.sample().drop(columns=["High"]), "GC=F")

    def test_empty_market_feed(self):
        with self.assertRaises(ValueError):
            prepare_history(pd.DataFrame(), "GC=F")

    def test_unsupported_symbol(self):
        with self.assertRaises(ValueError):
            fetch_history("USER-INPUT","5m")

    def test_unsupported_interval(self):
        with self.assertRaises(ValueError):
            fetch_history("GC=F","3m")

    def test_age_notice(self):
        df=prepare_history(self.sample(),"GC=F")
        self.assertIn("Letzte Kerze",age_notice(df))

    def test_available_market_mapping(self):
        self.assertEqual(MARKETS["Gold-Future (GC=F) · nicht XAUUSD Spot"],"GC=F")
        self.assertEqual(PERIODS["5m"],"5d")

if __name__ == "__main__":
    unittest.main()
