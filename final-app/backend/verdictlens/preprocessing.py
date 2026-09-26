"""Input preparation shared by training and saved-model inference."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

FEATURES = [
    'RevolvingUtilizationOfUnsecuredLines', 'age',
    'NumberOfTime30-59DaysPastDueNotWorse', 'DebtRatio', 'MonthlyIncome',
    'NumberOfOpenCreditLinesAndLoans', 'NumberOfTimes90DaysLate',
    'NumberRealEstateLoansOrLines', 'NumberOfTime60-89DaysPastDueNotWorse',
    'NumberOfDependents',
]
TARGET = 'SeriousDlqin2yrs'

class PrepareInputs(BaseEstimator, TransformerMixin):
    """Fixed, non-learned rules; accepts raw named features, excludes identifiers."""
    def fit(self, X, y=None):
        self.transform(X)
        self.feature_names_in_ = np.asarray(FEATURES, dtype=object)
        self.n_features_in_ = len(FEATURES)
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            raise TypeError('Pass a pandas DataFrame with the named dataset fields.')
        missing = sorted(set(FEATURES) - set(X.columns))
        if missing:
            raise ValueError(f'Missing feature columns: {missing}')
        out = X[FEATURES].apply(pd.to_numeric, errors='raise').astype(float).copy()
        if np.isinf(out.to_numpy()).any():
            raise ValueError('Infinite input values are not supported.')
        if (out < 0).any().any():
            raise ValueError('Dataset features must be nonnegative or missing.')
        # Zero is an invalid age; retain the row and impute inside the pipeline.
        out.loc[out['age'].eq(0), 'age'] = np.nan
        # Preserve unusual late-payment counts and large ratios: their encoding
        # is not explained by the supplied dictionary, so do not guess replacements.
        return out

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FEATURES, dtype=object)

def predict_applications(bundle, applications):
    frame = pd.DataFrame([applications] if isinstance(applications, dict) else applications)
    probability = bundle['pipeline'].predict_proba(frame)[:, 1]
    return pd.DataFrame({
        'serious_delinquency_risk': probability,
        'decision': np.where(probability >= bundle['threshold'], 'REJECT', 'APPROVE'),
        'threshold': bundle['threshold'],
    })
