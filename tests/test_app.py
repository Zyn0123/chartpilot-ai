import unittest
from pathlib import Path

class AppSmokeTests(unittest.TestCase):
    def test_dashboard_opens_without_api_key(self):
        from streamlit.testing.v1 import AppTest
        app = Path(__file__).resolve().parent.parent / "app.py"
        at = AppTest.from_file(str(app), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0, str([x.message for x in at.exception]))
        self.assertTrue(any("Kostenlose" in x.message or "API" in x.message for x in at.success))
        self.assertTrue(any("Historische" in x.label for x in at.button))

if __name__ == "__main__":
    unittest.main()
