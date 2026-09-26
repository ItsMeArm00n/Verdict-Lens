"""Gemini remains an explanation-only consumer of completed audit evidence."""
import json
import unittest
from types import SimpleNamespace
from pathlib import Path

from verdictlens.gemini_explanation import (
    build_prompt, explanation_payload, generate_explanation, model_candidates,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeModels:
    def __init__(self):
        self.call = None

    def generate_content(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(text="  The audit suggests human review.  ")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


class CapacityError(Exception):
    code = 503


class FallbackModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs["model"])
        if len(self.calls) == 1:
            raise CapacityError("503 UNAVAILABLE: high demand")
        return SimpleNamespace(text="## Primary decision\nRejected.\n\n## VerdictLens audit\nReview.")


class GeminiExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        saved = json.loads((ROOT / "tests/expected_results.json").read_text())
        cls.result = saved[2]["audit"]

    def test_payload_excludes_raw_applicant_and_probe_values(self):
        payload = explanation_payload(self.result)
        serialized = json.dumps(payload)
        self.assertNotIn("MonthlyIncome", serialized)
        self.assertNotIn('"changes"', serialized)
        self.assertEqual(payload["primary"], self.result["primary"])
        self.assertEqual(payload["flags"], self.result["flags"])

    def test_prompt_sets_explanation_boundary(self):
        prompt = build_prompt(self.result)
        self.assertIn("cannot alter", prompt.lower())
        self.assertIn("does not prove", prompt.lower())
        self.assertIn("## Primary decision", prompt)
        self.assertIn("## VerdictLens audit", prompt)
        self.assertIn(self.result["primary"]["decision"], prompt)

    def test_generation_uses_completed_result_and_returns_text(self):
        client = FakeClient()
        text = generate_explanation(
            self.result, "test-key", model="test-model", client_factory=lambda key: client
        )
        self.assertEqual(text, "The audit suggests human review.")
        self.assertEqual(client.models.call["model"], "test-model")
        self.assertIn("Audit JSON", client.models.call["contents"])

    def test_503_uses_next_flash_model(self):
        client = SimpleNamespace(models=FallbackModels())
        text = generate_explanation(
            self.result, "test-key", client_factory=lambda key: client
        )
        self.assertIn("## Primary decision", text)
        self.assertEqual(client.models.calls[:2], list(model_candidates())[:2])

    def test_missing_key_is_rejected_before_client_creation(self):
        with self.assertRaisesRegex(ValueError, "API key"):
            generate_explanation(self.result, "", client_factory=lambda key: FakeClient())


if __name__ == "__main__":
    unittest.main()
