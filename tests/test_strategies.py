"""New multi-strategy and screenshot-zone validation tests (offline, no paid calls)."""
import unittest
import pandas as pd

from strategies import evaluate_setups, analyze_strategies
from vision import validate_vision_plan


def synthetic_pullback():
    n=80
    close=[100+i*.015 for i in range(n)]
    close[-2]=100.25
    close[-1]=100.85
    rows=[]
    for i,c in enumerate(close):
        if i==n-2:
            op,hi,lo=100.30,100.42,100.00
        elif i==n-1:
            op,hi,lo=100.30,100.95,100.23
        else:
            op,hi,lo=c-.07,c+.10,c-.12
        rows.append(dict(open=op, high=hi,low=lo,close=c,
                        EMA20=100.35,EMA50=99.4,ATR14=.5,RSI14=52.))
    return pd.DataFrame(rows)


def raw_image_plan():
    return dict(signal="LONG", setup_type="PULLBACK", trend="aufwärts",
                data_quality="gut", market_regime="Trend", proposed_entry=100.,
                entry_zone_low=99.8,entry_zone_high=100.1,
                stop_loss=98., take_profit=103.,take_profit_2=105.,
                legible_price_scale=True,legible_recent_candles=True,
                entry_trigger="5m Schluss über der vorigen Kerze",
                detected_symbol="OANDA:XAUUSD",detected_timeframe="5m",
                screenshot_time="unbekannt",risk_flags=[])


class StrategyV3Tests(unittest.TestCase):
    def test_pullback_makes_coherent_zone(self):
        df=synthetic_pullback()
        meta={'atr':.5,'rsi':52.,'checks':{'long_trend':True,'short_trend':False,
             'long_confirmations':0,'short_confirmations':0}}
        base={'signal':'NO TRADE'}
        found=evaluate_setups(df,base,meta,'Scalping')
        pb=next(s for s in found if s['setup']=='PULLBACK')
        self.assertEqual(pb['state'],'BESTÄTIGT')
        self.assertEqual(pb['side'],'LONG')
        self.assertTrue(pb['stop']<pb['zone_low']<=pb['entry']<=pb['zone_high']<pb['tp1']<pb['tp2'])

    def test_each_strategy_is_distinct(self):
        df=synthetic_pullback()
        meta={'atr':.5,'rsi':52.,'checks':{'long_trend':True,'short_trend':False,
             'long_confirmations':0,'short_confirmations':0}}
        found=evaluate_setups(df,{'signal':'NO TRADE'},meta,'Daytrading')
        self.assertEqual([s['setup'] for s in found],['BREAKOUT','PULLBACK','RANGE'])
        self.assertNotEqual(found[0]['state'],'BESTÄTIGT')

    def test_image_valid_plan_has_two_targets(self):
        plan=validate_vision_plan(raw_image_plan())
        self.assertEqual(plan['signal'],'LONG')
        self.assertEqual(plan['setup_type'],'PULLBACK')
        self.assertEqual(plan['take_profit_2'],105.)
        self.assertEqual(plan['entry_zone_low'],99.8)

    def test_image_missing_scale_forces_no_trade(self):
        raw=raw_image_plan()
        raw['legible_price_scale']=False
        p=validate_vision_plan(raw)
        self.assertEqual(p['signal'],'NO TRADE')
        self.assertIsNone(p['take_profit_2'])
        self.assertIsNone(p['entry_zone_low'])

    def test_image_bad_target_order_forces_no_trade(self):
        raw=raw_image_plan()
        raw['take_profit_2']=101.
        self.assertEqual(validate_vision_plan(raw)['signal'],'NO TRADE')

    def test_image_missing_trigger_forces_no_trade(self):
        raw=raw_image_plan()
        raw.pop('entry_trigger')
        self.assertEqual(validate_vision_plan(raw)['signal'],'NO TRADE')

    def test_image_unknown_market_forces_no_trade(self):
        raw=raw_image_plan()
        raw['detected_symbol']='unbekannt'
        self.assertEqual(validate_vision_plan(raw)['signal'],'NO TRADE')


if __name__=='__main__':
    unittest.main()
