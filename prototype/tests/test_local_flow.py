"""End-to-end regression, offline execution, CLI contract and artifact checks."""
import copy
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verdictlens import Auditor, primary_prediction, audit, run
from verdictlens.artifacts import DEFAULT_MODELS

ROOT = Path(__file__).resolve().parents[1]


class LocalFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = json.loads((ROOT / 'examples/sample_applicants.json').read_text())
        cls.expected = json.loads((ROOT / 'tests/expected_results.json').read_text())
        cls.auditor = Auditor()

    def assert_result_close(self, actual, expected):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_result_close(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assert_result_close(a, b)
        elif isinstance(expected, float):
            self.assertAlmostEqual(actual, expected, delta=1e-12)
        else:
            self.assertEqual(actual, expected)

    def test_original_sample_results_preserved(self):
        self.assertEqual(len(self.samples), len(self.expected))
        for sample, expected in zip(self.samples, self.expected):
            with self.subTest(sample=expected['sample']):
                self.assertEqual(sample, expected['applicant'])
                self.assert_result_close(self.auditor.run(sample), expected['audit'])

    def test_public_functions_and_no_mutation(self):
        applicant = copy.deepcopy(self.samples[0])
        before = copy.deepcopy(applicant)
        result = run(applicant)
        self.assertEqual(primary_prediction(applicant), result['primary'])
        self.assertEqual(audit(applicant), result)
        self.assertEqual(self.auditor.run(applicant), result)
        self.assertEqual(applicant, before)
        json.dumps(result, allow_nan=False)

    def test_no_network_required(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network used')), \
             patch.object(socket, 'create_connection', side_effect=AssertionError('Network used')):
            offline = Auditor()
            for applicant in self.samples:
                self.assertEqual(offline.run(applicant), self.auditor.run(applicant))

    def test_artifact_tampering_fails_before_loading(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ['primary_model.joblib', 'challengers.joblib', 'audit_config.json', 'manifest.json']:
                shutil.copyfile(DEFAULT_MODELS / name, directory / name)
            with (directory / 'challengers.joblib').open('ab') as handle:
                handle.write(b'changed')
            with patch('verdictlens.artifacts.joblib.load') as loader:
                with self.assertRaisesRegex(ValueError, 'challengers.joblib'):
                    Auditor(directory)
                loader.assert_not_called()

    def test_audit_config_integrity_is_line_ending_independent(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ['primary_model.joblib', 'challengers.joblib', 'audit_config.json', 'manifest.json']:
                shutil.copyfile(DEFAULT_MODELS / name, directory / name)
            content = (directory / 'audit_config.json').read_text(encoding='utf-8')
            (directory / 'audit_config.json').write_text(
                content.replace('\r\n', '\n'), encoding='utf-8', newline='\n'
            )
            self.assertEqual(Auditor(directory).run(self.samples[0]), self.auditor.run(self.samples[0]))

    def test_audit_config_content_tampering_still_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ['primary_model.joblib', 'challengers.joblib', 'audit_config.json', 'manifest.json']:
                shutil.copyfile(DEFAULT_MODELS / name, directory / name)
            config_path = directory / 'audit_config.json'
            config = json.loads(config_path.read_text(encoding='utf-8'))
            config['primary_threshold'] = 0.5
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
            with patch('verdictlens.artifacts.joblib.load') as loader:
                with self.assertRaisesRegex(ValueError, 'audit_config.json'):
                    Auditor(directory)
                loader.assert_not_called()

    def test_cli_single_batch_invalid_and_independent_working_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            def invoke(data):
                input_path = directory / 'input.json'
                input_path.write_text(json.dumps(data))
                return subprocess.run([sys.executable, '-m', 'verdictlens', '--input', str(input_path)],
                                      cwd=directory, env=env, text=True, capture_output=True)
            single = invoke(self.samples[0])
            self.assertEqual(single.returncode, 0, single.stderr)
            self.assertEqual(json.loads(single.stdout), self.auditor.run(self.samples[0]))
            batch = invoke(self.samples)
            self.assertEqual(batch.returncode, 0, batch.stderr)
            self.assertEqual(json.loads(batch.stdout), [self.auditor.run(a) for a in self.samples])
            invalid = invoke({'age': 40})
            self.assertEqual(invalid.returncode, 2)
            self.assertIn('Feature mismatch', invalid.stderr)
            self.assertEqual(invalid.stdout, '')


if __name__ == '__main__':
    unittest.main()
