# V04 PR-E — Baseline and Oracle Diagnostic

> Status: **ENGINEERING PREPARATION / WAITING FORMAL PR-D DATASET**  
> Owner: **D — Quant / ML Research**

## Models

The first governed baseline policy is `v04_pr_e_baseline_policy_v1`:

```text
Classification  Logistic Regression, fixed decision threshold 0.5
Regression      Linear Regression and Ridge(alpha=1.0)
Preprocessing   Development-fit median imputer + StandardScaler
Seed            20260822
```

Validation never fits an imputer, scaler, coefficient, target boundary or model
decision. All-missing Development columns retain their width and are reported;
their adjacent missing indicators remain separate inputs.

## Evaluation tracks

Full Production uses the untouched 2024 Validation split for M/P/PM. The value
question is reported as `PM - M` for ROC-AUC and PR-AUC, alongside classification
and raw-return regression metrics.

The current reviewed Oracle inventory has no 2024 cases. Oracle M/P/O/PM/OM is
therefore evaluated only as seeded, stratified Development OOF diagnostic. It is
explicitly not described as 2024 Validation and cannot be directly substituted
for the Full Production holdout result.

## Metrics

Classification:

```text
ROC-AUC, PR-AUC, Brier, accuracy, precision, recall, F1
```

Regression:

```text
MAE, RMSE, R2
```

Every result retains cohort, feature group, protocol, sample count, feature
count, coefficients, intercept, and the all-missing Development feature list.
The score is not presented as a calibrated real-world probability.

## Implementation

```text
src/ipo_risk/modeling/baselines.py
scripts/run_v04_pr_e.py
tests/unit/test_v04_pr_e_baselines.py
```

Formal execution:

```bash
python scripts/run_v04_pr_e.py \
  --pr-d-dir reports/v04_pr_d \
  --output-dir reports/v04_pr_e
```

This code does not establish project value until it is run on the formally
frozen PR-D artifacts.
