"""TickerLayer recent-candle validation tests. Mocked only; no API key/network."""
from datetime import datetime,timedelta,timezone
import unittest
from tickerlayer_data import fetch_xauusd,parse_commodity_bars,INTERVALS
from quality import inspect_candles

CLOCK=datetime(2026,10,23,20,30,tzinfo=timezone.utc)

def payload(n=150, tf_min=5, *, clock=CLOCK):
    out=[]
    for i in range(n):
        start=clock-timedelta(minutes=tf_min*(n-i))
        t=int(start.timestamp()*1000)
        op=3995+i*.07
        out.append({"t":t,"o":op,"h":op+.22,"l":op-.23,"c":op+.1,"v":20+i})
    return {"symbol":"XAUUSD","results":list(reversed(out)),"next_offset":None}

class Fake:
    def __init__(self,code=200,data=None):
        self.status_code=code
        self._data=data
    def json(self):
        return self._data

class TickerLayerTests(unittest.TestCase):
    def test_recent_complete_m5_bars_are_valid(self):
        df=parse_commodity_bars(payload(),"5m",now=CLOCK)
        self.assertEqual(len(df),149) # latest candle hasn't passed 30s settlement lag
        self.assertAlmostEqual(df.close.iloc[-1],3995+.07*148+.1)
        audit=inspect_candles(df,"TickerLayer","5m",now=CLOCK)
        self.assertEqual(audit.state,"VERZÖGERT / UNBESTÄTIGT")

    def test_never_use_open_last_bar(self):
        data=payload()
        data["results"].insert(0,{"t":int((CLOCK-timedelta(minutes=2)).timestamp()*1000),
                                    "o":4000.,"h":4001.,"l":3998.,"c":4000.,"v":0})
        df=parse_commodity_bars(data,"5m",now=CLOCK)
        self.assertEqual(len(df),149)
        self.assertLess(df.time.iloc[-1].to_pydatetime(),CLOCK-timedelta(minutes=5))

    def test_stale_data_never_fresh(self):
        past=CLOCK-timedelta(days=4)
        df=parse_commodity_bars(payload(clock=past),"5m",now=CLOCK)
        self.assertEqual(inspect_candles(df,"TickerLayer","5m",now=CLOCK).state,"HISTORISCH")

    def test_missing_symbol_rejected(self):
        d=payload()
        d["symbol"]="GC=F"
        with self.assertRaises(ValueError):
            parse_commodity_bars(d,"5m",now=CLOCK)

    def test_malformed_prices_dropped(self):
        d=payload()
        d["results"][11]["h"]=-1
        df=parse_commodity_bars(d,"5m",now=CLOCK)
        self.assertEqual(len(df),148)

    def test_mocked_rest_bars_only(self):
        captured=[]
        def fake_get(url,**kw):
            captured.append((url,kw))
            return Fake(200,payload())
        df=fetch_xauusd("fake-key-test-is-long", "5m",now=CLOCK,request_get=fake_get)
        self.assertEqual(len(df),149)
        self.assertIn("/commodities/agg/XAUUSD/5/minute/",captured[0][0])
        self.assertEqual(captured[0][1]["headers"]["x-api-key"],"fake-key-test-is-long")
        self.assertEqual(captured[0][1]["params"]["sort"],"desc")

    def test_no_key_rejected_before_network(self):
        with self.assertRaises(ValueError):
            fetch_xauusd("", "5m",request_get=lambda *a,**kw:self.fail("network was used"))

    def test_rate_limit_is_clear(self):
        with self.assertRaisesRegex(RuntimeError,"Abfragelimit"):
            fetch_xauusd("fake-key-test-is-long","5m",now=CLOCK,request_get=lambda *a,**kw:Fake(429))

    def test_invalid_1d_rejected(self):
        with self.assertRaises(ValueError):
            fetch_xauusd("fake-key-test-is-long","1d")

if __name__=="__main__":
    unittest.main()
