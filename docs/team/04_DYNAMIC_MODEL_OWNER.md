# Person 4 — Dynamic Model / Prediction / SHAP Owner — CLOSED

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final status: **G4 PASS / ROLE-D V2 PROMOTED AND FROZEN**

## Final model decision

Role-D V2 is the effective frozen model identity for the competition product. The promotion decision is complete; this track is no longer open for model selection or retraining.

Historical frozen PR-F is retained as provenance and rollback history, not as the active generalized model identity.

## Frozen V2 summary

Governed 2024 evaluation recorded for the promoted V2:

```text
Precision = 0.3529
Recall = 0.5217
F1 = 0.4211
PR-AUC = 0.3812
ROC-AUC = 0.4875
```

The model remains an **uncalibrated triage signal**. Its score is not a break probability and must not be described as one.

## Final runtime path

```text
governed feature vector
+ models/role_d_v2 frozen package
+ feature manifest
+ frozen alert policy
→ runtime inference (load only; no fitting)
→ uncalibrated_model_score
→ native pred_contrib / SHAP
→ ModelSignal
→ Final Supervisor / UI
```

The generalized runtime is not a per-case lookup. Cases satisfying the feature contract can execute the frozen inference path; cases outside governed coverage fail closed with an explicit reason.

## G4 acceptance

Strict audit facts retained for v1.0.0:

```text
governed cases = 562
inference available = 540
available outside per-case handoff = 537
inference error = 0
degenerate SHAP = 0
published parity = 70/70
published parity mismatch = 0
max score delta = 0.0
max SHAP delta ≈ 2.2e-16
```

Machine source:

```text
reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json
models/role_d_v2/model_manifest.json
models/role_d_v2/feature_manifest.json
models/role_d_v2/alert_policy.json
models/role_d_v2/SHA256SUMS.txt
```

Frozen model SHA-256:

```text
320e810e85dcdb7e6caa40f9ef2b20157005e7a1d1af38ad7d586dd0feee72e2
```

## Governance

- runtime loads the frozen model; it does not retrain;
- no Validation-driven model tuning;
- no 2025 Blind outcome access for optimization;
- feature order/identity is manifest-bound;
- SHAP comes from the active inference result, not copied case handoffs;
- unavailable model input is not converted to a fake score;
- model score is not a probability.

## Known limitation

The promoted V2 improves the governed high-recall operating point over the older frozen PR-F, but ROC-AUC remains below 0.5 and the score is uncalibrated. v1.0.0 therefore presents the model only as an auxiliary triage signal alongside Document Evidence and Market context.

## Post-release rule

No model retraining, feature selection or alert-policy tuning is allowed in the v1.0.0 competition line. Only frozen-package integrity/runtime regression fixes are permitted.
