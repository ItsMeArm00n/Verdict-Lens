"""One local flow from applicant to primary prediction to structured audit result."""
import pandas as pd
from .artifacts import load_artifacts
from .explanations import explain
from .input_check import quality_check, scenarios, sensitivity_check
from .model_check import model_check
from .prediction import predict
from .preprocessing import FEATURES
from .threshold_check import threshold_check
from .validation import validate

class Auditor:
    """Load once, reuse for many applicants. The primary decision is never overridden."""

    def __init__(self, directory=None):
        self.primary, self.challengers, self.config = load_artifacts(directory)
        self.threshold = float(self.primary['threshold'])

    def primary_prediction(self, applicant):
        return predict(applicant, self.primary)

    def scenarios(self, applicant):
        return scenarios(validate(applicant), self.config)

    def audit(self, applicant):
        """Compute the primary once and return its decision with all audit evidence."""
        applicant = validate(applicant)
        primary = self.primary_prediction(applicant)
        frame = pd.DataFrame([applicant], columns=FEATURES)
        quality = quality_check(applicant, self.config)
        models = model_check(frame, self.challengers, self.config, primary)
        thresholds = threshold_check(primary, self.config['threshold_offsets'])
        probes = sensitivity_check(applicant, self.config, self.primary['pipeline'], primary)
        outcome = primary['decision']
        flags = []
        if quality:
            flags.append('INPUT_QUALITY_REVIEW')
        if any(m['own_policy_decision'] != outcome for m in models):
            flags.append('MODEL_POLICY_DISAGREEMENT')
        if any(m['at_primary_threshold_decision'] != outcome for m in models):
            flags.append('COMMON_THRESHOLD_DISAGREEMENT')
        if any(t['decision'] != outcome for t in thresholds):
            flags.append('THRESHOLD_SENSITIVE')
        if any(p['decision_flipped'] for p in probes):
            flags.append('INPUT_SENSITIVE')
        result = {'schema_version': '1.0', 'audit_version': self.config['audit_version'],
            'primary': primary, 'status': 'REVIEW' if flags else 'NO_FLAGS_IN_CHECKS',
            'flags': flags, 'input_quality': quality, 'challengers': models,
            'threshold_sensitivity': thresholds, 'input_sensitivity': probes,
            'limitations': ['Review flags do not prove a wrong or unfair decision.',
                'Sensitivity probes are local diagnostics, not causal advice or a fairness certification.',
                'All models share historical data and may share errors; no automated decision override.']}
        result['explanation'] = explain(result)
        return result

    def run(self, applicant):
        """Public end-to-end flow: applicant -> primary_prediction -> audit result."""
        return self.audit(applicant)

    explain = staticmethod(explain)
