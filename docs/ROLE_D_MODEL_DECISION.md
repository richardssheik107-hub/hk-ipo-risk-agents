# Role-D Model Decision — v1.0.0 Final

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final decision: **PROMOTE V2 — EFFECTIVE AND FROZEN**

## 1. Final decision

Role-D V2 is the active frozen model identity for the competition product. The older frozen PR-F remains in the repository as historical provenance/rollback evidence.

No further promote/retain decision is open in v1.0.0.

## 2. Governed evaluation record

| Metric | Frozen PR-F | Promoted V2 |
|---|---:|---:|
| Precision | 0.3333 | **0.3529** |
| Recall | 0.0435 | **0.5217** |
| F1 | 0.0769 | **0.4211** |
| PR-AUC | 0.3364 | **0.3812** |
| ROC-AUC | 0.4246 | **0.4875** |
| Alert count | 3 | 34 |

The V2 model improves the governed high-recall operating point but remains an **uncalibrated triage signal**. ROC-AUC remains below 0.5; this limitation is retained in release documentation.

## 3. Frozen runtime identity

```text
model package = models/role_d_v2
model SHA-256 = 320e810e85dcdb7e6caa40f9ef2b20157005e7a1d1af38ad7d586dd0feee72e2
score semantics = uncalibrated_model_score
runtime = load-only frozen inference
explainability = native pred_contrib / SHAP
```

The runtime consumes a governed feature vector bound to the frozen feature manifest and alert policy. It does not retrain.

## 4. Generalized runtime status

Dynamic inference and native SHAP are **closed / PASS**, not an open future goal.

Final strict audit facts:

```text
governed cases = 562
inference available = 540
available outside per-case handoff = 537
inference error = 0
degenerate SHAP = 0
published parity = 70/70
mismatch count = 0
max score delta = 0.0
max SHAP delta ≈ 2.2e-16
```

Machine source:

```text
reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json
```

## 5. Product interpretation

Allowed wording:

> The promoted V2 is a frozen, reproducible, Development-selected triage model with governed dynamic inference and native SHAP. It materially improves recall over the older frozen PR-F operating point, while remaining uncalibrated and limited in discrimination.

Do not claim:

- the score is a break probability;
- the model predicts post-listing returns with high accuracy;
- unavailable inputs imply low risk;
- SHAP is copied from a precomputed case lookup;
- the model may be retrained during the competition release.

## 6. Governance

- Development selection is frozen;
- no Validation-driven tuning;
- 2025 Blind outcomes are not used for optimization;
- model/feature/alert identities are hash-bound;
- missing features remain explicit;
- runtime only loads the frozen package;
- UI must preserve `uncalibrated_model_score` semantics.

## 7. v1.0.0 closure

Role-D model selection, packaging, dynamic inference and SHAP are complete. Future modeling experiments belong to a later version and must not rewrite the v1.0.0 model identity or evaluation record.
