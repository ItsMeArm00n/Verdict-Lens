"""Primary model inference using its original preprocessing and threshold."""
import pandas as pd
from .preprocessing import FEATURES
from .validation import decision, validate

def predict(applicant, bundle):
    applicant = validate(applicant)
    frame = pd.DataFrame([applicant], columns=FEATURES)
    probability = float(bundle['pipeline'].predict_proba(frame)[0, 1])
    threshold = float(bundle['threshold'])
    return {'risk_estimate': probability, 'threshold': threshold,
            'decision': decision(probability, threshold), 'signed_margin': probability-threshold}
