"""Run with: python -m unittest discover -s audit -p test_audit.py -v"""
import copy
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from verdictlens import Auditor, FEATURES
from verdictlens.validation import decision, validate

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auditor = Auditor()
        cls.app = dict(zip(FEATURES,[.2,45,0,.3,6000,8,0,1,0,1]))

    def test_boundary_semantics(self):
        t = self.auditor.threshold
        self.assertEqual(decision(t,t),'REJECT')
        self.assertEqual(decision(np.nextafter(t,0),t),'APPROVE')

    def test_invalid_inputs(self):
        for value in [-1,float('inf'),float('nan'),True,'6000']:
            a = dict(self.app,MonthlyIncome=value)
            with self.assertRaises(ValueError): self.auditor.audit(a)
        a = dict(self.app,age=45.5)
        with self.assertRaises(ValueError): self.auditor.audit(a)
        a = dict(self.app); del a['age']
        with self.assertRaises(ValueError): self.auditor.audit(a)
        a = dict(self.app,SeriousDlqin2yrs=1)
        with self.assertRaises(ValueError): self.auditor.audit(a)

    def test_repeatability_reordering_and_no_mutation(self):
        before = copy.deepcopy(self.app)
        a = self.auditor.audit(self.app)
        b = self.auditor.audit(dict(reversed(list(self.app.items()))))
        self.assertEqual(a,b)
        self.assertEqual(before,self.app)
        self.assertEqual(a,Auditor().audit(self.app))
        json.dumps(a,allow_nan=False)

    def test_primary_preserved(self):
        r = self.auditor.audit(self.app)
        p = float(self.auditor.primary['pipeline'].predict_proba(pd.DataFrame([self.app]))[0,1])
        self.assertEqual(r['primary']['risk_estimate'],p)
        self.assertEqual(r['primary']['decision'],decision(p,self.auditor.threshold))
        self.assertEqual(r['status'],'REVIEW' if r['flags'] else 'NO_FLAGS_IN_CHECKS')

    def test_missing_zero_and_ambiguous_counts(self):
        for field,value,code in [('MonthlyIncome',None,'IMPUTED_INPUT'),('age',0,'IMPUTED_INPUT'),
                ('NumberOfTimes90DaysLate',98,'AMBIGUOUS_LATE_COUNT')]:
            r = self.auditor.audit(dict(self.app,**{field:value}))
            self.assertIn({'code':code,'feature':field},r['input_quality'])
            self.assertEqual(r['status'],'REVIEW')
        r = self.auditor.audit(dict.fromkeys(FEATURES,None))
        self.assertEqual(len([q for q in r['input_quality'] if q['code']=='IMPUTED_INPUT']),10)
        json.dumps(r,allow_nan=False)

    def test_coupled_scenario(self):
        for _,changes,kind,a in self.auditor.scenarios(self.app):
            validate(a)
            if kind == 'conditional_scenario':
                self.assertAlmostEqual(a['MonthlyIncome']*a['DebtRatio'],self.app['MonthlyIncome']*self.app['DebtRatio'])

    def test_report_flags_match_evidence(self):
        samples = json.loads((Path(__file__).resolve().parents[1] / 'examples/sample_applicants.json').read_text())
        for app in samples:
            r = self.auditor.audit(app)
            d = r['primary']['decision']
            self.assertEqual('THRESHOLD_SENSITIVE' in r['flags'],any(s['decision']!=d for s in r['threshold_sensitivity']))
            self.assertEqual('INPUT_SENSITIVE' in r['flags'],any(s['decision_flipped'] for s in r['input_sensitivity']))
            self.assertEqual('MODEL_POLICY_DISAGREEMENT' in r['flags'],any(s['own_policy_decision']!=d for s in r['challengers']))

if __name__ == '__main__': unittest.main()
