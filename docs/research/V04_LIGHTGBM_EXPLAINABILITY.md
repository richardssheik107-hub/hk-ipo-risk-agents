# V04 PR-F — LightGBM and Explainability

> Status: **ENGINEERING COMPLETE / WAITING FORMAL PR-E GATE**
> Owner: **D — Quant / ML Research**

## Fixed model policy

`v04_pr_f_lightgbm_policy_v1` uses deterministic single-threaded LightGBM
Classifier and Regressor models. Hyperparameters are fixed in code before 2024
Validation is evaluated. Missing numeric values use LightGBM's native missing
handling; explicit missing indicators remain separate features.

Full Production M/P/PM and Oracle-v2 M/P/O/PM/OM are trained on 2020–2023
Development and evaluated once on untouched 2024 Validation. Oracle v2 provides
77 Development and 19 Validation rows. Random or shuffled cross-validation is
not used. PR-F refuses to start unless the formal PR-E manifest has
`formal_gate_passed=true`; no 2025 outcome is accepted.

## Explainability

Each result contains:

```text
global gain importance
global split importance
global mean absolute SHAP contribution
component-level mean absolute SHAP contribution
top ten signed drivers for every evaluated IPO
per-IPO classification and return predictions
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
  --oracle-v2-dir reports/v04_oracle_v2_matrices \
  --pr-e-manifest reports/v04_pr_e/run_manifest.json \
  --output-dir reports/v04_pr_f
```

The generated model scores are not described as calibrated real-world
probabilities. Formal conclusions require the local frozen bulk inputs plus the
measured PR-E/PR-F reports. Missing or checksum-drifted matrices fail closed.
