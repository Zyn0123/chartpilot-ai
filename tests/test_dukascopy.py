"""Offline checks for the public Dukascopy BID minute format: no network tests."""
import lzma
import struct
import unittest
from datetime import datetime, timezone

import pandas as pd

from dukascopy_data import daily_url, decode_day, aggregate, fetch_spot_gold


def compressed_minutes(count=350, *, minute_gap=False):
    records=[]
    for i in range(count):
        k = i+1 if minute_gap and i>=3 else i
        op=3995000+i
        close=op+4
        low=op-50
        high=op+50
        records.append(struct.pack(">IIIIIf",k*60,op,close,low,high,14.5))
    return lzma.compress(b"".join(records),format=lzma.FORMAT_ALONE)


class DummyResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code=status_code
        self.content=content


class DukascopyTests(unittest.TestCase):
    def setUp(self):
        self.day=datetime(2026,10,22,tzinfo=timezone.utc)

    def test_source_month_is_zero_based(self):
        self.assertEqual(
            daily_url(self.day),
            "https://datafeed.dukascopy.com/datafeed/XAUUSD/2026/09/22/BID_candles_min_1.bi5"
        )

    def test_bars_decode_into_correct_high_low_close(self):
        df=decode_day(compressed_minutes(350),self.day)
        self.assertEqual(len(df),350)
        self.assertAlmostEqual(df.close.iloc[0],3995.004)
        self.assertAlmostEqual(df.high.iloc[0],3995.05)
        self.assertAlmostEqual(df.low.iloc[0],3994.95)

    def test_invalid_compressed_data_fails(self):
        with self.assertRaises(ValueError):
            decode_day(b"not lzma",self.day)

    def test_partial_resample_bars_are_excluded(self):
        df=decode_day(compressed_minutes(353),self.day)
        five=aggregate(df,"5m")
        self.assertEqual(len(five),70)
        self.assertEqual(five.time.dt.tz.zone if hasattr(five.time.dt.tz,'zone') else str(five.time.dt.tz),
                         "UTC")

    def test_missing_minute_skips_partial_5m(self):
        df=decode_day(compressed_minutes(350,minute_gap=True),self.day)
        result=aggregate(df,"5m")
        self.assertEqual(len(result),69)

    def test_mocked_historical_download_offline(self):
        url=daily_url(self.day)
        calls=[]
        def fake_get(link,**kwargs):
            calls.append(link)
            if link==url:
                return DummyResponse(200,compressed_minutes(350))
            return DummyResponse(404,b"")
        data=fetch_spot_gold("5m",today=self.day,days_back=1,request_get=fake_get)
        self.assertEqual(len(data),70)
        self.assertEqual(calls,[url])

    def test_empty_archive_rejected(self):
        with self.assertRaises(RuntimeError):
            fetch_spot_gold("5m",today=self.day,days_back=1,
                            request_get=lambda url,**kwargs:DummyResponse(404,b""))

    def test_rate_limit_reported(self):
        with self.assertRaisesRegex(RuntimeError,"429/503"):
            fetch_spot_gold("5m",today=self.day,days_back=1,
                            request_get=lambda url,**kwargs:DummyResponse(429,b"too many"))

    def test_unsupported_interval_rejected(self):
        with self.assertRaises(ValueError):
            fetch_spot_gold("4h")


if __name__ == "__main__":
    unittest.main()
