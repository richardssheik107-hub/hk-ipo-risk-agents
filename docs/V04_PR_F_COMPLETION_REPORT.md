# V04 PR-F Completion Report — LightGBM + Explainability

> Status: **COMPLETE / FROZEN**
>
> Owner: **D — Quant / ML Research**
>
> Formal execution date: **2026-08-23**
>
> Formal execution revision: `854294769cd8162bb989d019addf10d653e663e8`

## 1. Gate result

PR-F consumed the frozen PR-D, Oracle v2 and formal PR-E runtime artifacts
without rematerializing or rewriting them. The governed run completed with:

```text
status                    complete_frozen_inputs
formal_gate_passed        true
full Production           354 Development / 70 Validation
Oracle v2 intersection    77 Development / 19 Validation
LightGBM results          8
saved models              16
2025 Blind y accessed     NO
```

The committed freeze summary is
`reports/frozen/v04_pr_f_lightgbm_manifest.json`. Models, per-case predictions,
detailed SHAP output and runtime results remain local and ignored.

## 2. Governance correction and fixed policy

The inherited PR-F implementation inferred cohort year from `case_id`. That is
not valid because the identifier encodes prospectus source year. PR-F now binds
the exact 424-case official listing-year map already frozen by PR-E, including
31 cross-year cases. Missing, drifted, out-of-range or 2025 mappings fail closed.

```text
Classifier             deterministic single-threaded LightGBM
Regressor              deterministic single-threaded LightGBM
Training               2020-2023 Development
Evaluation             untouched 2024 Validation
Classification cutoff  0.5
Random seed            20260822
Hyperparameter tuning  none on 2024 Validation
```

## 3. Full Production 2024 result

| Features | ROC-AUC | PR-AUC | Brier | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M | 0.4246 | 0.3364 | 0.2613 | 0.4257 | 0.6085 | -0.0562 |
| P | 0.5000 | 0.3286 | 0.2261 | 0.4053 | 0.5925 | -0.0014 |
| PM | 0.4246 | 0.3364 | 0.2613 | 0.4257 | 0.6085 | -0.0562 |

`PM` is byte-for-byte predictive-equivalent to `M` under the frozen tree
policy. Every Production Document feature has zero split/gain/SHAP importance,
so Production Document X adds no increment in this LightGBM run:

```text
PM - M ROC-AUC       0.0000
PM - M PR-AUC        0.0000
PM - M Brier         0.0000
PM - M regression    0.0000 on MAE / RMSE / R2
paired bootstrap CI  [0.0000, 0.0000] for ROC-AUC gain
```

This is a frozen-model finding, not proof that prospectus information is
intrinsically non-predictive. It indicates that the current Production feature
representation supplies no usable splits under this policy and sample size.

## 4. Oracle v2 2024 diagnostic

| Features | ROC-AUC | PR-AUC | Brier | MAE | RMSE | R2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| M | 0.4286 | 0.2770 | 0.2192 | 0.3797 | 0.6092 | -0.1815 |
| P | 0.5000 | 0.2632 | 0.1942 | 0.3501 | 0.5606 | -0.0004 |
| O | 0.3714 | 0.2373 | 0.2358 | 0.3785 | 0.5716 | -0.0403 |
| PM | 0.4286 | 0.2770 | 0.2192 | 0.3797 | 0.6092 | -0.1815 |
| OM | 0.4143 | 0.2526 | 0.2561 | 0.4421 | 0.6346 | -0.2822 |

Oracle addition (`OM - M`) is negative on the 19-case Validation intersection:

```text
ROC-AUC gain      -0.0143   95% paired bootstrap [-0.3171, 0.2917]
PR-AUC gain       -0.0244   95% paired bootstrap [-0.2948, 0.1238]
Brier reduction   -0.0369
```

The intervals are wide and cross zero. This does not establish either a
positive Oracle ceiling or absence of signal; it confirms that the current
Oracle holdout is too small and unstable for repeated tuning.

## 5. Explainability, calibration and error analysis

Every evaluated IPO has signed top-ten native LightGBM `pred_contrib` drivers.
Global outputs include gain, split, mean absolute SHAP and component totals.
Market-only/combined Production importance is led by pre-listing Market Core
features. Oracle OM importance is led by expert-document summary features plus
Market Core context.

Calibration is assessment-only: no calibrator was fitted on Validation. Full
Production M/PM expected calibration error is 0.1731; Oracle OM is 0.2782.
Scores therefore remain explicitly labeled **uncalibrated model scores**, not
real-world probabilities.

Deterministic error analysis records false positives, false negatives and the
ten largest absolute 5D-return errors for each cohort/group. Full Production
M/PM produced 2 false positives and 22 false negatives at the frozen 0.5 cutoff,
showing that the fixed classifier is poorly suited for direct probability or
decision use without a future governed calibration/threshold study.

## 6. Reproducibility and validation

```text
PR-F run_manifest.json       dcaa27ff64d3268e85f7f46fa16fac8621107a420297a6059d4824866e97c035
PR-F model_results.json      d6b4cae7d4cb8b78430b6b9beb25a866d4709e19c41fc9b6c60b6a07a6e4f41f
PR-F model_comparison.json   c033c4f8ed849255eb4369ecfe413a384ab9f1d8a20f4b6899f45683785efd27
16-model set                 3e39ba67e163a7a5e96ffb3c1df82d5a640abb8c286e85e431d463f6e16b1e2e
```

A `--resume` rerun produced byte-identical hashes for all runtime outputs and
16 models. Validation completed:

```text
targeted PR-E / PR-F / Oracle tests   16 passed
full pytest                           1422 passed / 2 existing warnings
project validation                   completed
competition data validation          passed
compileall                            passed
git diff --check                      passed
```

## 7. Gate decision

PR-F is **COMPLETE / FROZEN**. PR-G may consume the frozen PR-E/PR-F research
artifacts to build the Market Agent and Final Supervisor contract. PR-G must
preserve the uncalibrated-score semantics, surface uncertainty, and must not
describe these scores as probabilities or access 2025 Blind y.
