"""Load the frozen local artifacts and verify their integrity before unpickling."""
import hashlib
import json
from pathlib import Path
import joblib
from .validation import sha256

DEFAULT_MODELS = Path(__file__).resolve().parents[1] / 'models'

def canonical_json_sha256(path):
    """Hash JSON meaning rather than platform-dependent whitespace/line endings."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    canonical = json.dumps(
        data, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False,
    ).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()

def load_artifacts(directory=None):
    directory = Path(directory).resolve() if directory is not None else DEFAULT_MODELS
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for name in ('primary_model.joblib', 'challengers.joblib'):
        path = directory / name
        if sha256(path) != manifest[name]:
            raise ValueError(f'Artifact integrity check failed: {name}')
    config_path = directory / 'audit_config.json'
    if canonical_json_sha256(config_path) != manifest['audit_config.canonical_sha256']:
        raise ValueError('Artifact integrity check failed: audit_config.json')
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if sha256(directory / 'primary_model.joblib') != config['primary_sha256']:
        raise ValueError('Primary model differs from the audited version.')
    primary = joblib.load(directory / 'primary_model.joblib')
    challengers = joblib.load(directory / 'challengers.joblib')
    if float(primary['threshold']) != float(config['primary_threshold']):
        raise ValueError('Primary threshold differs from the audit configuration.')
    if set(challengers) != set(config['challenger_thresholds']):
        raise ValueError('Challenger models and thresholds do not match.')
    return primary, challengers, config
