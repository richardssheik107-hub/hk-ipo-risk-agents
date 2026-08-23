# V04 PR-E Completion Report — Baseline + Oracle Diagnostic

> Status: **COMPLETE / FROZEN**
>
> Owner: **D — Quant / ML Research**
>
> Formal execution date: **2026-08-23**
>
> Formal execution revision: `01473c0b1c002751fc3a15832302747067cccc2a`

## 1. Gate result

PR-E consumed the frozen PR-D six-matrix runtime package and the frozen Oracle
v2 98-artifact runtime package without rematerializing either upstream. The
governed Oracle matrix builder produced the required ten fair-intersection
matrices, and the formal baseline run completed with:

```text
status                    complete_frozen_inputs
formal_gate_passed        true
full Production           354 Development / 70 Validation
Oracle v2 intersection    77 Development / 19 Validation
formal model results      48
2025 Blind y accessed     NO
```

The small committed freeze summary is
`reports/frozen/v04_pr_e_baseline_manifest.json`. Bulk matrices and detailed
runtime results remain local and ignored.

## 2. Cohort-year governance correction

The first formal attempt correctly failed before model fitting because the
baseline implementation inferred cohort year from `case_id`. A v0.4 case ID
encodes the prospectus source year, which is not always the official listing
year. The frozen 424-row modeling cohort contains 31 such cross-year cases:

```text
Development cross-year cases    26
Validation cross-year cases       5
Total                            31
```

PR-E now resolves the time split from
`data/catalog/ipo_official_master_bridge.csv` using
`official_listed_date.year`, validates the exact 424-case mapping, rejects
missing/duplicate/out-of-range entries, and records both source SHA-256 and the
aggregate mapping hash. No public Schema or frozen PR-D matrix was changed.

```text
cohort-year policy   v04_official_listing_year_bridge_v1
catalog SHA-256      c0696f480d54397c169b43085ad77939edde538be3ee5ec3a2ae8ce8b2489a2d
mapping hash         4888c0630d46ed8db57613301d0c4a3b7a1c339bc882891a7bb6da4484edb781
```

## 3. Frozen evaluation protocol

```text
Development diagnostics
  train 2020       → evaluate 2021
  train 2020–2021  → evaluate 2022
  train 2020–2022  → evaluate 2023

Formal Validation
  fit 2020–2023    → evaluate 2024 once
```

Models and preprocessing remain frozen:

```text
Classification   Logistic Regression / threshold 0.5
Regression       Linear Regression / Ridge(alpha=1.0)
Preprocessing    Development-fit median imputation + StandardScaler
Random seed      20260822
```

## 4. Full Production 2024 classification

| Features | ROC-AUC | PR-AUC | Brier |
| --- | ---: | ---: | ---: |
| M | 0.5671 | 0.3624 | 0.2365 |
| P | 0.4884 | 0.3237 | 0.2306 |
| PM | 0.5513 | 0.3554 | 0.2420 |

Frozen Production increment (`PM - M`):

```text
ROC-AUC     -0.0157
PR-AUC      -0.0070
M - PM Brier  -0.0056
```

Therefore, the current Production Document features do **not** add robust
incremental 2024 classification value over Market-only under the frozen
baseline policy.

The regression comparison is directionally positive but small:

| Model | MAE reduction | RMSE reduction | R2 gain |
| --- | ---: | ---: | ---: |
| Linear | 0.0165 | 0.0123 | 0.0422 |
| Ridge | 0.0160 | 0.0126 | 0.0430 |

## 5. Oracle v2 2024 diagnostic

The Oracle comparison uses the same 19-case Validation intersection for every
feature group.

| Features | ROC-AUC | PR-AUC | Brier |
| --- | ---: | ---: | ---: |
| M | 0.6571 | 0.5472 | 0.1789 |
| P | 0.5357 | 0.2778 | 0.1906 |
| O | 0.4429 | 0.2623 | 0.2568 |
| PM | 0.6857 | 0.5477 | 0.1752 |
| OM | 0.6000 | 0.4854 | 0.2712 |

Oracle Validation diagnostics:

```text
Document Signal Ceiling: OM - M
  ROC-AUC   -0.0571
  PR-AUC    -0.0618

Pipeline Gap: OM - PM
  ROC-AUC   -0.0857
  PR-AUC    -0.0624
```

Oracle showed positive Development forward signal (`OM - M ROC-AUC +0.1459`,
`PR-AUC +0.1238`) but it did not persist on the 19-case 2024 intersection.
This is evidence of instability, not evidence that Oracle or Production has a
validated classification ceiling. The small Validation cohort requires
cautious interpretation and must not be repeatedly tuned against.

## 6. Reproducibility and audit

```text
Oracle governed matrix set
  cef14476f2312c8e10f7a5af3935ff3d5f5b776c2bf68f12a95983cf07768fcd

PR-E runtime files
  run_manifest.json       f60cc143d7710ae45978cfb07cb74968089ccffe687a673f2faa248c5d8508c4
  baseline_results.json   4444ea914295ecd9544e8f2d2db126e541b6dc1da60e5b05e648c49a3f9f659e
  value_diagnostic.json   c0d1882773863d1fcd6fa6155a9a09f02001e39ad60a5c92f2a87d33c286b863
```

A `--resume` rerun produced byte-identical hashes for all three PR-E runtime
files. The result metadata contains only 2020, 2021, 2022, 2023 and 2024; no
consumed or generated matrix contains a 2025 case ID.

Validation completed:

```text
targeted PR-E / Oracle-v2 tests   10 passed
full pytest                       1400 passed / 2 existing warnings
project validation               completed
competition data validation      passed
compileall                        passed
git diff --check                  passed
```

## 7. Gate decision

PR-E is **COMPLETE / FROZEN**. PR-F may now consume the PR-E freeze and run the
predefined LightGBM + native SHAP policy. PR-F must not reinterpret the PR-E
result as permission to tune repeatedly on 2024 Validation or access 2025
Blind y.
