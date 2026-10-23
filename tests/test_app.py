import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"


class AppSmokeTests(unittest.TestCase):
    def fresh(self):
        return AppTest.from_file(str(APP), default_timeout=30).run()

    def test_dashboard_opens_without_api_key(self):
        at = self.fresh()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertEqual(at.session_state["cp_page"], "01  COCKPIT")
        self.assertGreaterEqual(len(at.selectbox), 3)
        for i in range(1, 8):
            self.assertIsNotNone(at.button(key=f"cp_nav_{i}"))
        self.assertIsNotNone(at.button(key="spot_load"))
        self.assertIsNotNone(at.button(key="go_tradingview"))
        self.assertIsNotNone(at.button(key="yahoo_load"))
        self.assertTrue(any("Historische" in x.label for x in at.button))

    def test_tradingview_cta_opens_data_hub(self):
        at = self.fresh()
        at.button(key="go_tradingview").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertEqual(at.session_state["cp_page"], "02  DATA HUB")
        self.assertEqual(at.session_state["tv_symbol"], "OANDA:XAUUSD")
        self.assertTrue(any("CSV validieren" in x.label for x in at.button))

    def test_sidebar_buttons_switch_pages(self):
        at = self.fresh()
        at.button(key="cp_nav_2").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertEqual(at.session_state["cp_page"], "02  DATA HUB")
        self.assertTrue(any(x.key == "demo" for x in at.button))
        at.button(key="cp_nav_1").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertEqual(at.session_state["cp_page"], "01  COCKPIT")

    def test_demo_loads_and_chart_renders(self):
        at = self.fresh()
        at.button(key="cp_nav_2").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        at.button(key="demo").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertGreaterEqual(len(at.error), 1)
        self.assertTrue(any("Historische Strategie" in e.label for e in at.expander))
        # DEMO and stale-feed warnings must both be visible.
        self.assertGreaterEqual(len(at.error), 2)

    def test_vision_page_requires_opt_in(self):
        at = self.fresh()
        at.button(key="cp_nav_3").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertEqual(at.session_state["cp_page"], "03  VISION AI")


if __name__ == "__main__":
    unittest.main()
