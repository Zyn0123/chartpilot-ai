"""Offline OANDA Practice candle tests. No token is used in CI."""
import unittest
import pandas as pd

from oanda_data import parse_oanda_candles, fetch_oanda_practice, PRACTICE_API


class Response:
    def __init__(self,status=200,data=None):
        self.status_code=status
        self._data=data
    def json(self):
        return self._data


def payload(n=80):
    times=pd.date_range("2026-10-23 11:00:00",periods=n,freq="5min",tz="UTC")
    candles=[]
    for i,t in enumerate(times):
        p=3995+i*.04
        candles.append({
            "time":t.isoformat(),"complete":True,
            "mid":{"o":f"{p:.3f}","h":f"{p+.3:.3f}",
                   "l":f"{p-.2:.3f}","c":f"{p+.05:.3f}"},
            "volume":100+i
        })
    return {"instrument":"XAU_USD","granularity":"M5","candles":candles}


class OandaTests(unittest.TestCase):
    def test_m5_prices_valid(self):
        df=parse_oanda_candles(payload(),"M5")
        self.assertEqual(len(df),80)
        self.assertAlmostEqual(df.close.iloc[-1],3998.21,places=2)
        self.assertTrue(df.time.dt.tz is not None)

    def test_incomplete_last_bar_dropped(self):
        p=payload()
        p["candles"][-1]["complete"]=False
        self.assertEqual(len(parse_oanda_candles(p,"M5")),79)

    def test_reject_wrong_instrument(self):
        p=payload()
        p["instrument"]="EUR_USD"
        with self.assertRaises(ValueError):
            parse_oanda_candles(p,"M5")

    def test_reject_wrong_granularity(self):
        with self.assertRaises(ValueError):
            parse_oanda_candles(payload(),"M15")

    def test_read_only_request_and_parameters(self):
        calls=[]
        def get(url,**kwargs):
            calls.append((url,kwargs))
            return Response(200,payload())
        df=fetch_oanda_practice("test-token-for-mocked-request", "5m", request_get=get)
        self.assertEqual(len(df),80)
        self.assertEqual(calls[0][0],PRACTICE_API+"/v3/instruments/XAU_USD/candles")
        self.assertEqual(calls[0][1]["params"]["count"],400)
        self.assertEqual(calls[0][1]["params"]["price"],"M")
        self.assertEqual(calls[0][1]["params"]["granularity"],"M5")

    def test_invalid_token_never_makes_call(self):
        with self.assertRaises(ValueError):
            fetch_oanda_practice("", "5m",request_get=lambda *a,**k: self.fail("called"))

    def test_authentication_error_sanitized(self):
        with self.assertRaisesRegex(ValueError,"Token"):
            fetch_oanda_practice("token-for-example-sanitized", "5m",
                                 request_get=lambda *a,**k:Response(401,None))


if __name__=="__main__":
    unittest.main()
