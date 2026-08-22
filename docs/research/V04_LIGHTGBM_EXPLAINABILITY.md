# V04 PR-F — LightGBM and Explainability

> Status: **ENGINEERING PREPARATION / WAITING FORMAL PR-D DATASET**  
> Owner: **D — Quant / ML Research**

## Fixed model policy

`v04_pr_f_lightgbm_policy_v1` uses deterministic single-threaded LightGBM
Classifier and Regressor models. Hyperparameters are fixed in code before 2024
Validation is evaluated. Missing numeric values use LightGBM's native missing
handling; explicit missing indicators remain separate features.

Full Production M/P/PM is trained on Development and evaluated once on 2024.
Oracle-intersection M/P/O/PM/OM remains Development-only stratified OOF because
the current reviewed Oracle inventory contains no 2024 rows. No 2025 outcome is
accepted.

## Explainability

Each result contains:

```text
global gain importance
global split importance
global mean absolute SHAP contribution
component-level mean absolute SHAP contribution
top ten signed drivers for every evaluated IPO
model text SHA-256
```

SHAP contributions use LightGBM's native `pred_contrib` implementation. This
does not require the optional Python `shap` plotting package and remains exactly
bound to the saved model and feature manifest.

Feature drivers are grouped by the canonical prefixes:

```text
market_core
market_extended       # only if later governed and explicitly included
production_document
oracle_document       # evaluation-only
```

IDs, stock codes, document IDs, Evidence IDs and target values never enter the
feature vector or importance tables.

## Implementation

```text
src/ipo_risk/modeling/lightgbm_modeling.py
scripts/run_v04_pr_f.py
tests/unit/test_v04_pr_f_lightgbm.py
```

Formal execution:

```bash
python scripts/run_v04_pr_f.py \
  --pr-d-dir reports/v04_pr_d \
  --output-dir reports/v04_pr_f
```

The generated model scores are not described as calibrated real-world
probabilities. Formal conclusions require the frozen PR-D data and PR-E/PR-F
measured reports.
