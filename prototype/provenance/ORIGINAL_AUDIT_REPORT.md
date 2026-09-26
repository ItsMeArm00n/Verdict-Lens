# VerdictLens inspection and audit results

## Delivered result

A working deterministic auditor combines two trained alternative models with threshold sensitivity, local input sensitivity and data-quality checks. It preserves the primary decision and produces REVIEW or NO_FLAGS_IN_CHECKS with inspectable evidence. No LLM or network connection is required.

## Exact source inspection

The `/mnt/data` path was not mounted in this Windows task. The matching `VerdictLens_primary_model.zip` was found in the preceding task’s saved outputs. Its 16 original members are included unchanged. The source location and SHA-256 are recorded in `audit/package_inventory.json`.

Archive SHA-256: `01bd60c583b5707af2c62eac98c9fa1373c23d0affab82cc29e06ade659c808c`

| Original member | Bytes | Contents |
|---|---:|---|
| cleaned_labeled_data.csv | 10,905,487 | 149,391 labeled rows, source IDs and fixed split labels; missing values retained before imputation. |
| data_dictionary.json | 2,015 | Original variable descriptions, including the delinquency target. |
| evaluation.png | 170,880 | Primary test ROC, precision-recall, reliability and confusion-matrix figure. |
| example_application.json | 363 | One training applicant for primary inference. |
| excluded_rows.csv | 30,780 | 609 removed duplicate row IDs and reasons. |
| holdout_predictions.csv | 1,399,761 | 29,879 original test predictions, outcomes, decisions and threshold. |
| metrics.json | 6,122 | Data provenance, cleaning, splits, candidates, threshold, medians, versions and metrics. |
| model_support.py | 2,292 | Fixed input rules, feature order and inference helper; required for serialized pipeline loading. |
| predict.py | 649 | Primary JSON inference CLI. |
| primary_model.joblib | 85,955 | Complete pipeline, policy threshold, features, target and metadata. |
| requirements.txt | 101 | Original pinned Python dependency versions. |
| RESULTS.md | 6,805 | Original primary-model results summary. |
| split_manifest.csv | 2,100,202 | Original source row IDs mapped to train, validation and test. |
| train.py | 11,747 | Primary training, candidate selection, threshold selection, evaluation and export code. |
| verification.json | 226 | Original verification assertions; independently rechecked where described below. |
| xgboost_model.json | 464,812 | Native booster only; excludes input transformer, imputer and decision policy. |

### Saved primary model

The joblib bundle has keys `pipeline`, `threshold`, `features`, `target`, and `metadata`. Its pipeline is PrepareInputs → median SimpleImputer with missing indicators → XGBClassifier. The selected booster has 400 trees, depth 3, learning rate 0.04, minimum child weight 10, subsample 0.85, column subsample 0.9 and L2 regularization 5. Natural class prevalence is preserved; no oversampling or class weighting was used.

Input preparation selects ten named features in saved order, rejects negative and infinite values, and turns age zero into missing. The imputer adds missing indicators for age, MonthlyIncome and NumberOfDependents, producing 13 booster inputs. Unusual ratios and late counts 96/98 were retained rather than guessed away.

There is no separate scaler, imputer file or LLM. Preprocessing is embedded in the joblib pipeline. There is no fitted probability calibrator in the primary bundle. The native JSON reproduces pipeline predictions on 100 rows only when passed the correctly transformed 13-column input.

The exact primary threshold is **0.178669735789299**. The rule is REJECT at or above this value, otherwise APPROVE. It was selected for maximum positive-class F1 on original validation rows. This is an illustrative policy, not a threshold justified by lending costs.

| Ordered feature | Training imputation median |
|---|---:|
| RevolvingUtilizationOfUnsecuredLines | 0.15493609600000002 |
| age | 52.0 |
| NumberOfTime30-59DaysPastDueNotWorse | 0.0 |
| DebtRatio | 0.367558459 |
| MonthlyIncome | 5400.0 |
| NumberOfOpenCreditLinesAndLoans | 8.0 |
| NumberOfTimes90DaysLate | 0.0 |
| NumberRealEstateLoansOrLines | 1.0 |
| NumberOfTime60-89DaysPastDueNotWorse | 0.0 |
| NumberOfDependents | 0.0 |

## Audit training and policy

Both challengers fit the original 89,634 training rows. The original validation set was split, keeping identical predictor profiles together, into 14,938 calibration rows and 14,940 threshold-selection rows. The original 29,879 test rows remain outside fitting and policy selection.

Logistic regression uses median imputation and missing indicators, log1p transforms, standardization and L2 regularization (C=1). Random forest uses 180 trees, depth limit 16, minimum leaf size 25 and 80% feature sampling. Both use sigmoid calibration on the calibration subset. Their own thresholds maximize F1 on the separate policy subset. No vote is interpreted as truth.

Review rules were set before challenger holdout evaluation: any challenger decision disagreement, decision flip under ±1/±2 percentage-point threshold changes, decision flip in configured local probes, or flagged input quality triggers REVIEW. The rules are demo heuristics, not a trained correctness classifier.

## Holdout results

| Model | ROC AUC | Average precision | Brier score ↓ | Precision | Recall | F1 | Own threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| primary | 0.8696 | 0.4152 | 0.0483 | 0.3952 | 0.5549 | 0.4617 | 0.178670 |
| logistic | 0.8389 | 0.3724 | 0.0516 | 0.3821 | 0.5040 | 0.4346 | 0.127009 |
| random_forest | 0.8659 | 0.4135 | 0.0495 | 0.3685 | 0.5774 | 0.4499 | 0.101377 |

Test positive prevalence is about 6.70%; average precision should be read against that baseline. Calibration bins and log loss are included in evaluation.json. The challenger reliability bins show overprediction in several lower-risk bins and underprediction at the high end. Sigmoid calibration has not eliminated calibration error. The primary has better test Brier score than both challengers; there is no claim that the challengers improve lending decisions.

| Full-test signal | Applicants | Rate |
|---|---:|---:|
| policy_disagreement | 1,562 | 5.23% |
| common_threshold_disagreement | 1,588 | 5.31% |
| threshold_sensitive | 593 | 1.98% |

Complete end-to-end audits were also run on a uniformly sampled 200-row test cohort (seed 20260926): **46 / 200 flagged for review**. Counts overlap by signal; the full cohort IDs and counts are saved. This small cohort measures prototype behavior, not deployment review demand or audit accuracy.

## Applicant demonstrations

These examples were deliberately selected to exercise different behaviors. They are not a representative performance sample. The last two modify a held-out applicant synthetically.

| Example | Primary risk | Primary decision | Audit status | Flags |
|---|---:|---|---|---|
| low_risk | 0.23% | APPROVE | NO_FLAGS_IN_CHECKS | None |
| high_risk | 92.68% | REJECT | REVIEW | INPUT_QUALITY_REVIEW |
| nearest_threshold | 17.87% | REJECT | REVIEW | MODEL_POLICY_DISAGREEMENT, COMMON_THRESHOLD_DISAGREEMENT, THRESHOLD_SENSITIVE, INPUT_SENSITIVE |
| model_disagreement | 17.44% | APPROVE | REVIEW | MODEL_POLICY_DISAGREEMENT, THRESHOLD_SENSITIVE, INPUT_SENSITIVE |
| missing_inputs | 0.40% | APPROVE | REVIEW | INPUT_QUALITY_REVIEW |
| ambiguous_late_count | 6.46% | APPROVE | REVIEW | INPUT_QUALITY_REVIEW, MODEL_POLICY_DISAGREEMENT, COMMON_THRESHOLD_DISAGREEMENT |

## Verification and limits

Original-test predictions reproduce with maximum absolute difference 2.98e-08. Original training medians match the saved imputer. Split manifests match; no identical cleaned predictor profiles cross original partitions or the two new validation roles. Native booster predictions match the complete pipeline when preprocessing is applied.

Behavioral tests cover threshold equality, invalid inputs, missing values, age zero, ambiguous counts, deterministic reloads, column ordering, unchanged inputs, preservation of primary decisions, coupled income/debt scenarios and flag-to-evidence consistency. See test_results.txt for the actual test outcome.

The original test benchmark had already been evaluated before this task. We reused it without fitting or selecting audit thresholds on it; future iteration against these scores should use a new external or prospective evaluation. No audit-error ground truth, causal recourse validation or comprehensive fairness analysis exists here. All models share source data and may share blind spots.

The tail checks are marginal training-range checks, not a multivariate out-of-distribution detector. Missing-value quartiles are diagnostic alternatives, not estimates of the applicant’s actual values. Age sensitivity does not establish unlawful discrimination. No overall review score is invented.

## Later website integration

Use one Python service to validate inputs, load the primary and audit artifacts, and return structured results. The browser displays the unchanged primary decision, review flags and numerical evidence. Gemini may optionally paraphrase a minimized evidence payload, with server-side credentials and a deterministic fallback; it must never alter the audit. See INTEGRATION.md. Full UI/UX is not implemented.

Method references: [probability calibration](https://scikit-learn.org/stable/modules/calibration.html) and [decision-threshold tuning](https://scikit-learn.org/stable/modules/classification_threshold.html).
