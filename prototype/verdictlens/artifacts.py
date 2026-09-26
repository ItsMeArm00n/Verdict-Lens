"""Load the frozen local artifacts and verify their integrity before unpickling."""
import json
from pathlib import Path
import joblib
from .validation import sha256

DEFAULT_MODELS = Path(__file__).resolve().parents[1] / 'models'

def load_artifacts(directory=None):
    directory = Path(directory).resolve() if directory is not None else DEFAULT_MODELS
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for name in ('primary_model.joblib', 'challengers.joblib', 'audit_config.json'):
        path = directory / name
        if sha256(path) != manifest[name]:
            raise ValueError(f'Artifact integrity check failed: {name}')
    config = json.loads((directory / 'audit_config.json').read_text(encoding='utf-8'))
    if sha256(directory / 'primary_model.joblib') != config['primary_sha256']:
        raise ValueError('Primary model differs from the audited version.')
    primary = joblib.load(directory / 'primary_model.joblib')
    challengers = joblib.load(directory / 'challengers.joblib')
    if float(primary['threshold']) != float(config['primary_threshold']):
        raise ValueError('Primary threshold differs from the audit configuration.')
    if set(challengers) != set(config['challenger_thresholds']):
        raise ValueError('Challenger models and thresholds do not match.')
    return primary, challengers, config
