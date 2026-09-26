# VerdictLens working prototype

This directory is reserved for the working local Streamlit prototype. Copy the contents of the current `VerdictLens with site` project into this folder while keeping this README as the technical guide.

## Prototype scope

The prototype demonstrates the complete workflow:

```text
Applicant input
    → Primary loan-risk prediction
    → APPROVE or REJECT
    → Deterministic VerdictLens audit
    → Stable under current checks or Review required
    → Optional Gemini explanation
```

It is intentionally a functional validation interface. The final visual and interaction design belongs in [`../final-app/`](../final-app/).

## Expected contents

After copying the prototype, this directory should contain:

```text
prototype/
├── app.py
├── verdictlens/
├── models/
├── examples/
├── tests/
├── reports/
├── requirements.txt
├── model_support.py
└── README.md
```

Keep `model_support.py`; the frozen model pipelines use it as a serialization compatibility import.

## Requirements

- Python 3.11
- A local terminal
- Internet access for the initial dependency installation
- An optional Gemini API key for generated explanations

The primary decision and VerdictLens audit work without Gemini and without an internet connection after dependencies are installed.

## Installation

Open a terminal in this directory:

```bash
python -m venv .venv
```

Activate the environment on Windows Command Prompt:

```bat
.venv\Scripts\activate
```

Or in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

## Start the local site

```bash
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) if the browser does not open automatically. Keep the terminal running while using the site and press `Ctrl+C` to stop it.

## Optional Gemini explanation

Gemini runs only after the structured audit is complete. It explains the primary decision mechanics first, then explains the audit findings. It cannot change any model output or audit flag.

The quickest prototype setup is to paste a key into the password field in the Streamlit sidebar. For regular local use, configure an environment variable before starting the application.

Windows Command Prompt:

```bat
set GEMINI_API_KEY=your_key_here
python -m streamlit run app.py
```

PowerShell:

```powershell
$env:GEMINI_API_KEY="your_key_here"
python -m streamlit run app.py
```

Never commit a real API key. The repository ignores `.env` and `.streamlit/secrets.toml`.

## JSON test cases

The site accepts one applicant object or a list of applicant objects. Every object must contain exactly these ten fields:

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

Use JSON `null` only when `MonthlyIncome` or `NumberOfDependents` is unavailable. Count fields and age must be whole numbers. All supplied numeric values must be finite and nonnegative.

For multiple cases, place complete applicant objects inside a JSON array. Open **Import applicant JSON**, validate the data, then select a case to load into the form.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The test suite covers the preserved model results, validation, determinism, offline core execution, artifact integrity, the Streamlit workflow, JSON imports, Gemini prompt boundaries, and temporary-capacity fallback behavior.

## Decision and audit outputs

The primary XGBoost model produces a serious-delinquency risk estimate and one binary decision:

- `APPROVE` when estimated risk is below the frozen threshold.
- `REJECT` when estimated risk is at or above the frozen threshold.

VerdictLens then produces:

- `NO_FLAGS_IN_CHECKS`, displayed as **Stable under current checks**.
- `REVIEW`, displayed as **Review required**.

A review result can include:

- `INPUT_QUALITY_REVIEW`
- `MODEL_POLICY_DISAGREEMENT`
- `COMMON_THRESHOLD_DISAGREEMENT`
- `THRESHOLD_SENSITIVE`
- `INPUT_SENSITIVE`

The audit status does not replace or reverse the primary decision.

## Boundaries

This prototype is intended for technical demonstration and testing. It does not provide lending advice, causal explanations, fairness certification, legal compliance review, or production-ready risk assessment.
