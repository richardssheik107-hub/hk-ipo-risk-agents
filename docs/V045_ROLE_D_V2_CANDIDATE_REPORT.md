# V0.4.5 Role D v2 Candidate — Feature Pruning and High-Recall Policy

> Status: **RESEARCH CANDIDATE / A REVIEW REQUIRED**
>
> Owner: **D — Quant / Outcome / Evaluation**

## Scope

This candidate does not overwrite frozen PR-F. It adds a reproducible,
Development-selected study for improving the 5D significant-drop operating
point while preserving the original model and 2025 Blind boundary.

Selection protocol:

```text
train 2020       -> evaluate 2021
train 2020-2021  -> evaluate 2022
train 2020-2022  -> evaluate 2023
```

Feature groups and the F2 alert budget are selected only from those expanding
Development folds. The selected candidate is then evaluated on 2024 once.

## Selected candidate

The frozen deterministic LightGBM parameters are retained. The 30-position
Market Core vector is pruned to seven regime features:

```text
ipo_count_30d
ipo_count_60d
recent_ipo_break_rate
recent_ipo_return_5d
same_industry_ipo_count_180d
same_industry_recent_break_rate
same_industry_recent_return_5d
```

The primary model-selection metric is macro forward-year PR-AUC. The selected
seven-feature group scores `0.3711`, versus `0.3344` for all 30 features. The
Development-selected alert fraction is `0.475`.

## 2024 Validation result

| Metric | Frozen PR-F | Alert-only fix | v2 candidate |
|---|---:|---:|---:|
| ROC-AUC | 0.4246 | 0.4246 | **0.4875** |
| PR-AUC | 0.3364 | 0.3364 | **0.3812** |
| Brier | 0.2613 | 0.2613 | **0.2502** |
| Precision | 0.3333 | 0.2941 | **0.3529** |
| Recall | 0.0435 | 0.4348 | **0.5217** |
| F1 | 0.0769 | 0.3509 | **0.4211** |
| Alert count | 3 | 34 | 34 |

The candidate identifies 12 of 23 significant drops, compared with 10 for the
alert-only fix and one for frozen threshold `0.5`.

## Interpretation

The candidate improves ranking, calibration error and the high-recall operating
point by removing noisy/redundant Market Core positions. It remains a triage
model: ROC-AUC is still slightly below `0.5`, and the score remains explicitly
uncalibrated.

Target-offer facts, additional aligned-return aggregates, stronger tree
regularization, Random Forest, Extra Trees, histogram boosting and a return
regressor risk score were checked on Development only and rejected because
they did not improve the frozen temporal-selection objective.

## Governance and verification

```text
2024 labels used for feature/model/alert selection   NO
2025 Blind y accessed                               NO
frozen PR-F overwritten                             NO
original Role D Gate                                PASS
full test suite                                     1902 passed
deterministic repeat hashes                         PASS
```

Formal promotion requires A review. Until promotion, product code must continue
to describe this as a candidate rather than a replacement frozen PR-F signal.
