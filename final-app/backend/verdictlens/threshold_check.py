"""Evaluate the frozen threshold offsets without changing the primary decision."""
from .validation import decision

def threshold_check(primary, offsets):
    thresholds = [float(min(1, max(0, primary['threshold'] + offset))) for offset in offsets]
    return [{'threshold': t, 'decision': decision(primary['risk_estimate'], t)} for t in thresholds]
