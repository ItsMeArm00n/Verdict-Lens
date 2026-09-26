"""Compare challengers under their own policies and the primary threshold."""
from .validation import decision

def model_check(frame, challengers, config, primary):
    results = []
    for name, model in challengers.items():
        probability = float(model.predict_proba(frame)[0, 1])
        threshold = config['challenger_thresholds'][name]
        results.append({'model': name, 'risk_estimate': probability,
            'own_policy_threshold': threshold, 'own_policy_decision': decision(probability, threshold),
            'at_primary_threshold_decision': decision(probability, primary['threshold']),
            'signed_difference_from_primary': probability-primary['risk_estimate']})
    return results
