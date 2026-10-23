"""Checks for the new terminal's risk controls, TradingView import and vision fail-closed behavior."""
import unittest
from datetime import datetime, timezone

import pandas as pd

from offline import load_ohlc
from quality import inspect_candles, freshness_blocks_live
from backtest import run_backtest
from vision import analyze_screenshot


def bars(n=100, start=100):
    rows=[]
    for i in range(n):
        c=start+.075*i
        rows.append({"open":c-.1,"high":c+.3,"low":c-.3,"close":c,
                     "time":pd.Timestamp("2026-10-20",tz="UTC")+pd.Timedelta(minutes=5*i)})
    return pd.DataFrame(rows)

class V2Tests(unittest.TestCase):
    def test_tradingview_seconds_epoch(self):
        df=bars(75)
        text=df.copy()
        text["time"]=text["time"].astype("int64")//10**9
        loaded=load_ohlc(text.to_csv(index=False).encode())
        self.assertEqual(len(loaded),75)
        self.assertEqual(str(loaded.time.iloc[0].year),"2026")

    def test_tradingview_milliseconds_epoch(self):
        df=bars(75)
        text=df.copy()
        text["time"]=text["time"].astype("int64")//10**6
        loaded=load_ohlc(text.to_csv(index=False).encode())
        self.assertEqual(loaded.time.iloc[0].year,2026)

    def test_tradingview_duplicate_time_rejected(self):
        text=bars(75)
        text.loc[1,"time"]=text.loc[0,"time"]
        with self.assertRaises(ValueError):
            load_ohlc(text.to_csv(index=False).encode())

    def test_stale_or_unknown_not_live(self):
        old=bars(75)
        audit=inspect_candles(old,"Import","5m",now=datetime(2026,10,23,tzinfo=timezone.utc))
        self.assertEqual(audit.state,"HISTORISCH")
        self.assertTrue(freshness_blocks_live(audit))

    def test_demo_marked_demo(self):
        self.assertEqual(inspect_candles(bars(75),"DEMO","5m",is_demo=True).state,"DEMO")

    def test_backtest_flat_no_lookahead(self):
        metrics,trades=run_backtest(bars(95),"Gold","Scalping","5m",.15,95)
        self.assertGreaterEqual(metrics["trades"],0)
        if not trades.empty:
            self.assertTrue((trades["Ausstieg Kerze"]>=trades["Einstieg Kerze"]).all())
            self.assertTrue((trades["Einstieg Kerze"]>=66).all())

    def test_backtest_rejects_bad_cost(self):
        with self.assertRaises(ValueError):
            run_backtest(bars(90),"Gold","Scalping","5m",-1)

    def test_vision_rejects_missing_key_without_request(self):
        with self.assertRaises(ValueError):
            analyze_screenshot(b"image", "image/png", "")

    def test_vision_rejects_bad_mime_without_request(self):
        with self.assertRaises(ValueError):
            analyze_screenshot(b"image", "application/pdf", "key-this-is-not-real")

if __name__=="__main__":
    unittest.main()
