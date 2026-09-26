# VerdictLens Streamlit Prototype

This folder contains the original working proof of concept. It validates the complete local flow with a simple Streamlit interface and preserves the deterministic Python package, frozen artifacts, tests, and verification evidence used before the final interface was built.

## What this version demonstrates

```text
Applicant data
  → primary_prediction(applicant)
  → XGBoost risk estimate
  → APPROVE or REJECT
  → audit(applicant)
  → model, threshold, input, and quality evidence
  → NO_FLAGS_IN_CHECKS or REVIEW
  → optional Gemini wording
```

The machine-learning workflow runs locally and deterministically. Gemini is optional in this prototype and is used only for explanation.

## Requirements

- Python 3.11
- A terminal or PowerShell window
- Internet access during dependency installation
- A Gemini API key only if you want generated explanations

## Install it

Open a terminal in `prototype/` and create an isolated Python environment:

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

For Windows Command Prompt:

```bat
.venv\Scripts\activate
```

Install the pinned dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Start the site

```powershell
python -m streamlit run app.py
```

Streamlit normally opens a browser automatically. Otherwise, visit [http://localhost:8501](http://localhost:8501). Keep the terminal running while using the site. Press `Ctrl+C` to stop it.

## Use the prototype

1. Enter all ten applicant fields or open the JSON importer.
2. Optionally load the bundled example.
3. Run the primary loan decision.
4. Review the risk estimate, fixed threshold, margin, and `APPROVE` or `REJECT` result.
5. Run VerdictLens.
6. Inspect challenger decisions, threshold tests, input probes, quality findings, flags, and limitations.
7. Optionally ask Gemini to explain the completed result.

## Use the Python package directly

The public API is intentionally small:

```python
from verdictlens import primary_prediction, audit, run

applicant = {
    "RevolvingUtilizationOfUnsecuredLines": 0.536575875,
    "age": 35,
    "NumberOfTime30-59DaysPastDueNotWorse": 1,
    "DebtRatio": 0.692470557,
    "MonthlyIncome": 7556.0,
    "NumberOfOpenCreditLinesAndLoans": 16,
    "NumberOfTimes90DaysLate": 0,
    "NumberRealEstateLoansOrLines": 1,
    "NumberOfTime60-89DaysPastDueNotWorse": 0,
    "NumberOfDependents": 0,
}

primary = primary_prediction(applicant)
result = audit(applicant)
same_complete_flow = run(applicant)
```

All returned values are JSON serializable. `run(applicant)` and `audit(applicant)` execute the same full audit flow.

## Run from JSON without the website

Run the bundled examples:

```powershell
python -m verdictlens
```

Audit your own JSON file:

```powershell
python -m verdictlens --input examples\sample_applicants.json
```

Save the structured output:

```powershell
python -m verdictlens --input examples\sample_applicants.json --output reports\my_results.json
```

The input may be one applicant object or an array of applicant objects.

## JSON schema

Every applicant must contain the ten exact field names below:

```json
{
  "RevolvingUtilizationOfUnsecuredLines": 0.536575875,
  "age": 35,
  "NumberOfTime30-59DaysPastDueNotWorse": 1,
  "DebtRatio": 0.692470557,
  "MonthlyIncome": 7556.0,
  "NumberOfOpenCreditLinesAndLoans": 16,
  "NumberOfTimes90DaysLate": 0,
  "NumberRealEstateLoansOrLines": 1,
  "NumberOfTime60-89DaysPastDueNotWorse": 0,
  "NumberOfDependents": 0
}
```

Validation rules:

- Field names are exact and case-sensitive.
- Numeric values must be finite and nonnegative.
- Age and count fields must be whole numbers.
- `MonthlyIncome` and `NumberOfDependents` may be `null` when unavailable.
- Missing or extra required structure is rejected before prediction.
- Late-payment values `96` and `98` are accepted but flagged as ambiguous historical codes.

## Models

| Model | Purpose | Frozen threshold |
|---|---|---:|
| XGBoost | Primary serious-delinquency risk model | 17.8669736% |
| Logistic regression | Challenger with a simpler additive model family | 12.7008693% |
| Random forest | Challenger with a different nonlinear model family | 10.1377354% |

The primary model alone controls the original decision. A risk below its threshold is `APPROVE`; a risk at or above it is `REJECT`. Challenger models supply comparison evidence and never replace the primary output.

### Training data and splits

The frozen artifacts were trained from a preserved cleaned dataset containing **149,391 labeled rows** and ten applicant features. A separate file records **609 excluded duplicate IDs**. The target is binary serious delinquency, and positive cases represent about **6.70%** of the untouched test set.

| Data partition | Rows | Used for |
|---|---:|---|
| Training | 89,634 | Fitting all three model families |
| Calibration | 14,938 | Sigmoid calibration for the two challengers |
| Policy | 14,940 | Selecting challenger thresholds by F1 |
| Test | 29,879 | Final untouched evaluation |

Identical cleaned predictor profiles were kept together when the validation data was divided into calibration and policy subsets. The test set was not used to fit the models, calibrate probabilities, or select audit thresholds.

### Preprocessing and model parameters

- **Primary XGBoost:** fixed ten-feature order → age-zero handling → median imputation with missing indicators → XGBoost. The booster uses 400 trees, depth 3, learning rate 0.04, minimum child weight 10, subsample 0.85, column subsample 0.90, and L2 regularization 5.
- **Logistic regression:** median imputation, missing indicators, `log1p` transformations, standardization, and L2 regularization with `C=1`.
- **Random forest:** 180 trees, maximum depth 16, minimum leaf size 25, and 80% feature sampling.
- **Calibration:** both challengers use sigmoid calibration on the calibration subset. The saved primary has no separate fitted probability calibrator.
- **Class handling:** natural prevalence was retained; no oversampling and no class weighting were used.
- **Thresholds:** each threshold maximizes positive-class F1 on its designated validation or policy data. The thresholds are demonstration policies, not lending-cost-optimized cutoffs.

This project does not fine-tune a foundation model. The three predictive models are trained conventional supervised-learning models. Gemini is a downstream wording layer only.

### Holdout performance

| Model | ROC AUC | Average precision | Brier ↓ | Precision | Recall | F1 | Threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| XGBoost | **0.8696** | **0.4152** | **0.0483** | **0.3952** | 0.5549 | **0.4617** | 0.178670 |
| Logistic regression | 0.8389 | 0.3724 | 0.0516 | 0.3821 | 0.5040 | 0.4346 | 0.127009 |
| Random forest | 0.8659 | 0.4135 | 0.0495 | 0.3685 | **0.5774** | 0.4499 | 0.101377 |

Accuracy is omitted because the dataset is imbalanced. ROC AUC, average precision, precision, recall, F1, and Brier score give a more honest picture of ranking, rare-class detection, decision tradeoffs, and probability quality. These results evaluate prediction performance; they do not measure fairness or prove that an audit flag is correct.

For the full provenance record, training medians, reliability observations, signal rates, and evaluation caveats, see [`provenance/ORIGINAL_AUDIT_REPORT.md`](provenance/ORIGINAL_AUDIT_REPORT.md).

## Audit result

VerdictLens returns:

- `primary`: the preserved XGBoost score, threshold, decision, and signed margin.
- `challengers`: both alternative model scores and decisions.
- `threshold_sensitivity`: decisions at offsets of −2, −1, 0, +1, and +2 percentage points.
- `input_sensitivity`: controlled local probes, new scores, deltas, and whether the decision flipped.
- `input_quality`: structured findings for missing, ambiguous, or unusual values.
- `flags`: the exact reasons a case needs review.
- `status`: `NO_FLAGS_IN_CHECKS` or `REVIEW`.
- `limitations`: boundaries that must travel with the result.
- `explanation`: deterministic summary text.

### Review flags

| Flag | Meaning |
|---|---|
| `INPUT_QUALITY_REVIEW` | At least one input-quality finding exists |
| `MODEL_POLICY_DISAGREEMENT` | A challenger disagrees using its own threshold |
| `COMMON_THRESHOLD_DISAGREEMENT` | A challenger disagrees at the primary threshold |
| `THRESHOLD_SENSITIVE` | A nearby configured threshold changes the decision |
| `INPUT_SENSITIVE` | At least one controlled input probe changes the decision |

Any flag sets the audit status to `REVIEW`. No flags sets it to `NO_FLAGS_IN_CHECKS`. The primary decision remains unchanged in both cases.

## Optional Gemini explanation

Paste a key into the Streamlit sidebar, or set it for the current terminal session.

PowerShell:

```powershell
$env:GEMINI_API_KEY="your_key_here"
python -m streamlit run app.py
```

Command Prompt:

```bat
set GEMINI_API_KEY=your_key_here
python -m streamlit run app.py
```

The default model is `gemini-3.1-flash-lite`, with configured Flash fallbacks for temporary capacity errors. Never place a real key in `.env.example` or commit it to Git.

## Run the tests

From this `prototype/` directory:

```powershell
python -m unittest discover -s tests -v
```

If Python reports that `tests` is not importable, confirm that the prompt ends in `\prototype>` before running the command.

The suite covers original saved behavior, deterministic results, strict validation, JSON import, offline core execution, artifact integrity, Streamlit integration, and Gemini prompt boundaries. The preserved verification summary is in [`reports/VERIFICATION.md`](reports/VERIFICATION.md).

## Folder guide

```text
prototype/
├── app.py                    Streamlit interface
├── verdictlens/              Prediction and audit package
├── models/                   Frozen artifacts, manifest, and policy configuration
├── examples/                 Ready-to-run applicant JSON
├── tests/                    Automated regression and behavior tests
├── reports/                  Verification report and sample results
├── provenance/               Original audit archive and report
├── model_support.py          Compatibility class required by serialized pipelines
└── requirements.txt          Pinned Python dependencies
```

Do not remove `model_support.py`; the frozen joblib artifacts require it when loading.

## Boundaries

This prototype does not provide lending advice, a causal explanation, a fairness certificate, legal compliance, or a production-ready risk assessment. Challenger agreement can still be wrong because models trained on related historical data may share the same blind spots.
