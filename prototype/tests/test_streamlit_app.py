"""Smoke-test the Streamlit workflow without opening a browser."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class StreamlitAppTests(unittest.TestCase):
    def load(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(app.exception, [])
        return app

    @staticmethod
    def button(app, label):
        return next(button for button in app.button if button.label == label)

    def test_page_loads_and_primary_decision_runs(self):
        app = self.load()
        self.assertEqual(app.title[0].value, "VerdictLens")
        self.button(app, "Run loan decision").click().run()
        self.assertEqual(app.exception, [])
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertIn(metrics["Decision"], {"APPROVE", "REJECT"})
        self.assertTrue(metrics["Estimated risk"].endswith("%"))
        self.assertIn("Margin to threshold", metrics)

    def test_full_audit_runs(self):
        app = self.load()
        self.button(app, "Run VerdictLens audit").click().run()
        self.assertEqual(app.exception, [])
        self.assertEqual(len(app.metric), 4)
        self.assertGreaterEqual(len(app.dataframe), 1)
        self.assertGreaterEqual(len(app.json), 1)


if __name__ == "__main__":
    unittest.main()
