import unittest
import pandas as pd
from pathlib import Path
from offline import load_ohlc, analyze_ohlc

def sample(n=80, break_kind=None):
    rows = []
    for i in range(n):
        c = 100+i*.03
        if break_kind == 'long' and i>=n-2: c = 111+(i-(n-2))
        if break_kind == 'short' and i>=n-2: c = 85-(i-(n-2))
        rows.append({'Open':c-.08,'High':c+.22,'Low':c-.25,'Close':c})
    return pd.DataFrame(rows)

class OfflineTests(unittest.TestCase):
    def test_demo_file_loads(self):
        file=Path(__file__).resolve().parent.parent/'sample'/'demo_simuliert_5m.csv'
        df=load_ohlc(file.read_bytes())
        self.assertEqual(len(df),150)
        self.assertIn('time', df.columns)
    def test_semicolon_de_decimal(self):
        lines=['Open;High;Low;Close']+['100,5;101,5;99,5;100,8']*60
        df=load_ohlc('\n'.join(lines).encode())
        self.assertAlmostEqual(df.close.iloc[-1],100.8)
    def test_invalid_candle_rejected(self):
        df=sample(); df.loc[0,'High']=0
        with self.assertRaises(ValueError):
            load_ohlc(df.to_csv(index=False).encode())
    def test_not_enough_candles(self):
        with self.assertRaises(ValueError):
            load_ohlc(sample(50).to_csv(index=False).encode())
    def test_flat_is_no_trade(self):
        a,_,_=analyze_ohlc(sample().rename(columns=lambda x:x.lower()),'Gold','Scalping','5m')
        self.assertEqual(a['signal'],'NO TRADE')
    def test_long_setup_has_valid_stop(self):
        a,_,_=analyze_ohlc(sample(break_kind='long').rename(columns=lambda x:x.lower()),'Gold','Scalping','5m')
        self.assertEqual(a['signal'],'LONG')
        self.assertLess(a['stop_loss'],a['proposed_entry'])
        self.assertLess(a['proposed_entry'],a['take_profit'])
    def test_short_setup_is_consistent(self):
        a,_,_=analyze_ohlc(sample(break_kind='short').rename(columns=lambda x:x.lower()),'Gold','Scalping','5m')
        self.assertEqual(a['signal'],'SHORT')
        self.assertLess(a['take_profit'],a['proposed_entry'])
        self.assertLess(a['proposed_entry'],a['stop_loss'])
    def test_no_trade_explains_unmet_breakout_conditions(self):
        a,_,meta=analyze_ohlc(sample().rename(columns=lambda x:x.lower()),'Gold','Scalping','5m')
        checks=meta['checks']
        self.assertEqual(a['signal'],'NO TRADE')
        self.assertEqual(checks['needed_confirmations'],2)
        self.assertLess(checks['long_confirmations'],2)
        self.assertLess(checks['short_confirmations'],2)
        self.assertLess(checks['short_threshold'],checks['long_threshold'])

    def test_long_trade_has_two_breakout_confirmations(self):
        a,_,meta=analyze_ohlc(sample(break_kind='long').rename(columns=lambda x:x.lower()),'Gold','Scalping','5m')
        self.assertEqual(a['signal'],'LONG')
        self.assertTrue(meta['checks']['long_trend'])
        self.assertEqual(meta['checks']['long_confirmations'],2)

if __name__=='__main__':
    unittest.main()
