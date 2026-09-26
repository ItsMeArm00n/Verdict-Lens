"""Validate the JSON format accepted by the Streamlit importer."""
import json
import unittest
from verdictlens.case_import import parse_json_cases


DEFAULTS = {
    "RevolvingUtilizationOfUnsecuredLines": 0.536575875,
    "age": 35,
    "NumberOfTime30-59DaysPastDueNotWorse": 1,
    "DebtRatio": 0.692470557,
    "MonthlyIncome": 7556.0,
    "NumberOfOpenCreditLinesAndLoans": 16,
    "NumberOfTimes90DaysLate": 0,
    "NumberRealEstateLoansOrLines": 1,
    "NumberOfTime60-89DaysPastDueNotWorse": 0,
    "NumberOfDependents": 0,
}


class JsonImportTests(unittest.TestCase):
    def test_single_object_and_list(self):
        self.assertEqual(len(parse_json_cases(json.dumps(DEFAULTS))), 1)
        self.assertEqual(len(parse_json_cases(json.dumps([DEFAULTS, DEFAULTS]))), 2)

    def test_empty_list_and_feature_mismatch_fail(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_json_cases("[]")
        with self.assertRaisesRegex(ValueError, "Feature mismatch"):
            parse_json_cases('{"age": 40}')

    def test_invalid_json_reports_location(self):
        with self.assertRaisesRegex(ValueError, "line"):
            parse_json_cases("{bad json}")


if __name__ == "__main__":
    unittest.main()
