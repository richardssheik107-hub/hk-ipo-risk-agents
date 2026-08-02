import json
import unittest
from pathlib import Path

from risk_mvp.service import evaluate


class MvpTest(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((Path("data") / "simulated_ipo_cases.json").read_text(encoding="utf-8"))

    def test_high_risk_case_has_evidence_and_review(self):
        report = evaluate(self.cases[0])
        self.assertEqual(report.risk_level, "高")
        self.assertTrue(report.review_required)
        self.assertGreaterEqual(len(report.evidence), 5)

    def test_low_risk_case_is_below_high_threshold(self):
        report = evaluate(self.cases[2])
        self.assertLess(report.risk_probability_5d, 0.35)


if __name__ == "__main__":
    unittest.main()
