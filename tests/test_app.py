import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"

class AppSmokeTests(unittest.TestCase):
    def test_dashboard_opens_without_api_key(self):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertGreaterEqual(len(at.success), 1)
        self.assertTrue(any("Historische" in x.label for x in at.button))

    def test_demo_loads_and_chart_renders(self):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.radio[0].set_value("02  DATA HUB").run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        at.button(key="demo").click().run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertGreaterEqual(len(at.error), 1)

    def test_vision_page_requires_opt_in(self):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.radio[0].set_value("03  VISION AI").run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))

if __name__ == "__main__":
    unittest.main()
