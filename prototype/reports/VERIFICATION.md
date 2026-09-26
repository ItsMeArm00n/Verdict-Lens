# Local-flow verification

All 14 tests passed (Python 3.11.9).
The original primary-model ZIP and the refactored primary artifact have identical SHA-256 hashes.
The audit configuration and challenger bytes are unchanged from the audit prototype.

| Sample | Primary decision | Risk | Audit status |
|---|---|---:|---|
| low_risk | APPROVE | 0.225750% | NO_FLAGS_IN_CHECKS |
| high_risk | REJECT | 92.680311% | REVIEW |
| nearest_threshold | REJECT | 17.868994% | REVIEW |
| model_disagreement | APPROVE | 17.443831% | REVIEW |
| missing_inputs | APPROVE | 0.397102% | REVIEW |
| ambiguous_late_count | APPROVE | 6.463675% | REVIEW |

Original saved outputs are compared with a numerical tolerance of 1e-12; labels, flags and structure must match exactly.
See verification.json for exact equality results per sample and the tested dependency versions.

Verified: public callable flow, original behavior, strict JSON, invalid-input errors, no input mutation,
repeatability, no network connection, artifact tamper rejection, and single/batch CLI execution from another working directory.
A local Streamlit workflow prototype is included. No retraining, hosted API or LLM integration was added.
