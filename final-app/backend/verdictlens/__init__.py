"""Deterministic, local VerdictLens inference and audit entry points."""
from functools import lru_cache
from .auditor import Auditor
from .preprocessing import FEATURES

@lru_cache(maxsize=1)
def _default_auditor():
    return Auditor()

def primary_prediction(applicant):
    """Return only the primary model prediction."""
    return _default_auditor().primary_prediction(applicant)

def audit(applicant):
    """Return primary prediction and deterministic audit evidence."""
    return _default_auditor().audit(applicant)

def run(applicant):
    """Run the complete local flow; returns a JSON-serializable dictionary."""
    return _default_auditor().run(applicant)

__all__ = ['Auditor', 'FEATURES', 'primary_prediction', 'audit', 'run']
