"""Strict applicant validation and shared decision policy."""
import hashlib
import json
import math
from pathlib import Path
from .preprocessing import FEATURES

COUNT_FIELDS = [f for f in FEATURES if f.startswith('Number')] + ['age']
LATE_FIELDS = [f for f in FEATURES if 'PastDue' in f or f == 'NumberOfTimes90DaysLate']

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')

def decision(p, threshold):
    return 'REJECT' if p >= threshold else 'APPROVE'

def validate(applicant):
    if not isinstance(applicant, dict):
        raise ValueError('Each applicant must be a JSON object.')
    missing, extra = set(FEATURES)-set(applicant), set(applicant)-set(FEATURES)
    if missing or extra:
        raise ValueError(f'Feature mismatch: missing={sorted(missing)}, extra={sorted(extra)}')
    result = {}
    for name in FEATURES:
        value = applicant[name]
        if value is None:
            result[name] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{name} must be a finite nonnegative number or null.')
        if name in COUNT_FIELDS and value != int(value):
            raise ValueError(f'{name} must be an integer or null.')
        result[name] = float(value)
    return result

