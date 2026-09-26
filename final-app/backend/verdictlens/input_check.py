"""Input quality checks and the original deterministic sensitivity probes."""
import pandas as pd
from .preprocessing import FEATURES
from .validation import LATE_FIELDS, decision

def quality_check(applicant, config):
    quality = []
    for feature, value in applicant.items():
        reference = config['reference'][feature]
        if value is None or (feature == 'age' and value == 0):
            quality.append({'code': 'IMPUTED_INPUT', 'feature': feature})
        elif value < reference['min'] or value > reference['max']:
            quality.append({'code': 'OUTSIDE_TRAINING_RANGE', 'feature': feature})
        elif value < reference['q01'] or value > reference['q99']:
            quality.append({'code': 'TRAINING_TAIL', 'feature': feature})
        if feature in LATE_FIELDS and value in [96, 98]:
            quality.append({'code': 'AMBIGUOUS_LATE_COUNT', 'feature': feature})
    return quality

def scenarios(a, config):
    """Local diagnostic probes, not causal recourse or global robustness proof."""
    cases = []
    def add(name, changes, kind):
        b = dict(a)
        b.update(changes)
        cases.append((name, changes, kind, b))
    for f in ['RevolvingUtilizationOfUnsecuredLines', 'DebtRatio']:
        if a[f] is not None and a[f] > 0:
            for factor in [0.95, 1.05]:
                add(f'{f}_x{factor}', {f:a[f]*factor}, 'measurement_sensitivity')
    income, ratio = a['MonthlyIncome'], a['DebtRatio']
    if income is not None and income > 0 and ratio is not None:
        for factor in [0.95, 1.05]:
            add(f'income_x{factor}_fixed_debt_payments',
                {'MonthlyIncome':income*factor,'DebtRatio':ratio/factor}, 'conditional_scenario')
    for f in FEATURES:
        if a[f] is None or (f == 'age' and a[f] == 0):
            for q in ['q25','q75']:
                add(f'{f}_missing_to_{q}', {f:config['reference'][f][q]}, 'missing_value_sensitivity')
    if a['age'] is not None and a['age'] > 1:
        for delta in [-1,1]:
            add(f'age_record_delta_{delta}', {'age':a['age']+delta}, 'record_sensitivity_not_actionable')
    return cases


def sensitivity_check(applicant, config, pipeline, primary):
    cases = scenarios(applicant, config)
    if not cases:
        return []
    probabilities = pipeline.predict_proba(pd.DataFrame([s[3] for s in cases], columns=FEATURES))[:, 1]
    probes = []
    for (name, changes, kind, _), probability in zip(cases, probabilities):
        probability = float(probability)
        outcome = decision(probability, primary['threshold'])
        probes.append({'scenario': name, 'kind': kind, 'changes': changes,
            'risk_estimate': probability, 'risk_delta': probability-primary['risk_estimate'],
            'decision': outcome, 'decision_flipped': outcome != primary['decision']})
    return probes
