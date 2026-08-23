# V04 PR-E — Baseline and Oracle Diagnostic

> Status: **ENGINEERING COMPLETE / FORMAL RUN PENDING LOCAL FROZEN BULK INPUTS**
> Owner: **D — Quant / ML Research**

## Gate boundary

PR-E consumes, but never rewrites:

~~~text
frozen PR-D Production matrices
+ frozen Oracle v2 feature artifacts
→ governed Oracle-intersection matrix builder
→ Linear / Ridge / Logistic baselines
→ M / P / O / PM / OM diagnostic
~~~

The committed PR-D freeze manifest binds the six Full Production matrix files
used by PR-E. Every file SHA-256 is verified before model fitting. The merged
Oracle v2 freeze binds 98 feature artifacts and a strict 96-case outcome-usable
set: 77 Development and 19 Validation. The governed matrix builder verifies
both freezes, reconstructs the fair M/P/O/PM/OM intersection, and emits a
separate ten-file matrix manifest. Formal PR-E verifies that manifest before
fitting any model.

The immutable PR-A Oracle v1 snapshot has 55 eligible Development rows and no
Validation rows. It remains historical. The formal current Oracle ceiling is
Oracle v2 from merged PR #97, with 77 Development and 19 Validation rows.

## Fixed model policy

Policy: v04_pr_e_baseline_policy_v1.

~~~text
Classification  Logistic Regression, fixed decision threshold 0.5
Regression      Linear Regression and Ridge(alpha=1.0)
Preprocessing   Development-fit median imputer + StandardScaler
Seed            20260822
~~~

Validation never fits an imputer, scaler, coefficient, target boundary, feature
policy or model decision. All-missing Development columns retain their width
and are reported; adjacent missing indicators remain separate inputs.

## Evaluation protocols

Formal 2024 evaluation:

~~~text
2020–2023 Development fit
→ untouched 2024 Validation
~~~

Development diagnostics use expanding-year forward chaining:

~~~text
train 2020       → evaluate 2021
train 2020–2021  → evaluate 2022
train 2020–2022  → evaluate 2023
~~~

Random or shuffled cross-validation is prohibited. Each fold fits its own
imputer, scaler and model using earlier years only.

Full Production evaluates M/P/PM. The frozen Oracle v2 intersection evaluates
M/P/O/PM/OM using the same case set, target, split, preprocessing and model
family. Cross-group case/target drift fails closed.

## Value diagnostic

The report calculates:

~~~text
Production Increment = PM - M
Document Signal Ceiling = OM - M
Pipeline Gap = OM - PM
~~~

Each comparison is reported for ROC-AUC and PR-AUC on both the 2024 holdout and
the Development forward-chaining diagnostic. Formal conclusions require the
frozen Oracle v2 2024 intersection; Development-only Oracle v1 results cannot
substitute for it.

## Metrics

Classification:

~~~text
ROC-AUC, PR-AUC, Brier, accuracy, precision, recall, F1
~~~

Regression:

~~~text
MAE, RMSE, R2
~~~

Every result retains cohort, feature group, protocol, train/evaluation years,
fold counts, feature count, coefficients, intercept and all-missing Development
features. Scores are not described as calibrated real-world probabilities.

## Implementation

~~~text
src/ipo_risk/modeling/baselines.py
src/ipo_risk/modeling/oracle_v2_matrices.py
scripts/build_v04_oracle_v2_matrices.py
scripts/run_v04_pr_e.py
tests/unit/test_v04_oracle_v2_matrices.py
tests/unit/test_v04_pr_e_baselines.py
~~~

Formal execution first builds the bound Oracle intersection:

~~~bash
python scripts/build_v04_oracle_v2_matrices.py \
  --pr-d-dir reports/v04_pr_d \
  --oracle-v2-dir reports/v04_oracle_v2 \
  --output-dir reports/v04_oracle_v2_matrices
~~~

Then run PR-E:

~~~bash
python scripts/run_v04_pr_e.py \
  --pr-d-dir reports/v04_pr_d \
  --pr-d-freeze-manifest reports/frozen/v04_pr_d_canonical_dataset_manifest.json \
  --oracle-v2-dir reports/v04_oracle_v2_matrices \
  --oracle-v2-freeze-manifest reports/frozen/v04_oracle_v2_manifest.json \
  --oracle-v2-matrix-manifest reports/v04_oracle_v2_matrices/run_manifest.json \
  --output-dir reports/v04_pr_e
~~~

The allow-production-only flag is an explicit readiness mode. Its manifest
records formal_gate_passed=false and cannot be used to mark PR-E complete.

Bulk matrices and generated model results remain runtime artifacts. Only a
small, independently reviewed freeze summary may be committed after the real
run.

The repository intentionally does not commit the six PR-D bulk matrices or the
98 Oracle v2 feature files. A checkout without those governed local artifacts
must fail closed and cannot publish measured PR-E metrics.
