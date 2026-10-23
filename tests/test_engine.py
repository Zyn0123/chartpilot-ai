import unittest
from engine import normalize_analysis, extract_json

class AnalysisTests(unittest.TestCase):
    def test_json(self):
        self.assertEqual(extract_json('```json\n{"signal":"NO TRADE"}\n```')['signal'], 'NO TRADE')
    def test_incomplete_trade_is_rejected(self):
        a = normalize_analysis({'signal':'LONG','data_quality':'gut','proposed_entry':100,'stop_loss':None,'take_profit':120})
        self.assertEqual(a['signal'], 'NO TRADE')
        self.assertIsNone(a['proposed_entry'])
    def test_bad_direction_is_rejected(self):
        a = normalize_analysis({'signal':'SHORT','data_quality':'gut','proposed_entry':100,'stop_loss':95,'take_profit':110})
        self.assertEqual(a['signal'], 'NO TRADE')
    def test_valid_short_rr(self):
        a = normalize_analysis({'signal':'SHORT','data_quality':'gut','proposed_entry':100,'stop_loss':105,'take_profit':90})
        self.assertEqual(a['signal'], 'SHORT')
        self.assertEqual(a['risk_reward'],2.0)
    def test_poor_quality_forces_no_trade(self):
        a = normalize_analysis({'signal':'LONG','data_quality':'schwach','proposed_entry':100,'stop_loss':95,'take_profit':110})
        self.assertEqual(a['signal'],'NO TRADE')
    def test_unrecognized_signal(self):
        a = normalize_analysis({'signal':'BUY EVERYTHING','data_quality':'gut'})
        self.assertEqual(a['signal'],'NO TRADE')

if __name__ == '__main__':
    unittest.main()
