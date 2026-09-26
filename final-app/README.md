# VerdictLens final application

> **Status:** Planned. The final interface has not been implemented yet.

This directory will contain the fully designed VerdictLens application after the workflow, model integration, audit semantics, and explanation boundary have been validated in the working [`prototype`](../prototype/) directory.

## Goal

The final application will turn the validated prototype into a clear, accessible review experience without changing the deterministic audit contract.

The design should help a user answer four questions in order:

1. What decision did the primary model make?
2. How far was the risk estimate from the decision threshold?
3. What did VerdictLens find when it challenged that decision?
4. Which evidence, limitations, or follow-up actions should a human reviewer consider?

## Planned experience

- Clear separation between the primary decision and the audit result
- Accessible risk, threshold, and decision-margin presentation
- Human-readable audit flags with expandable technical evidence
- Challenger-model comparisons
- Threshold and input-sensitivity views
- Input-quality warnings
- JSON case import for repeatable demonstrations
- Optional Gemini explanation clearly separated from computed evidence
- Exportable structured audit results
- Responsive and accessible visual design

## Engineering boundary

The final interface should reuse the validated VerdictLens Python package rather than copying or reimplementing audit rules. The structured result remains the source of truth:

```text
applicant
    → primary_prediction(applicant)
    → audit(applicant)
    → structured final result
    → interface and optional explanation
```

Gemini remains downstream from the completed audit. It may improve readability but must never set or modify scores, thresholds, decisions, statuses, or flags.

## Definition of done

- The final interface consumes the same deterministic audit contract as the prototype.
- Existing core and behavioral tests continue to pass.
- The interface clearly distinguishes `APPROVE`/`REJECT` from `Stable`/`Review required`.
- All interactive states are readable in light and dark environments.
- API keys and local secrets remain outside version control.
- Screenshots, setup instructions, and known limitations are documented here.
- The application is tested with stable approvals, stable rejections, contested approvals, contested rejections, missing inputs, and malformed JSON.

## Development notes

Document major design decisions in this README as implementation begins. Include screenshots or short recordings only after the corresponding workflow is functional and tested.
