# Project Specification — v1.0.0 Competition Product

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Product status: **FROZEN / FORMALLY RELEASED FOR COMPETITION SUBMISSION**  
> Role-B runtime freeze: `ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`

## 1. Product goal

Starting from Hong Kong IPO prospectuses, governed pre-listing market context and a frozen model signal, the product generates evidence-grounded risk analysis, Financial/Legal/Business attribution, physical-page Evidence, Agent Trace, Market-X, model/SHAP signals, supervisory reasoning and reviewable reports/UI/API output.

```text
PDF
→ governed Evidence
→ Financial / Legal / Business analysis
→ verification / document supervision
+ governed MarketContext
+ governed ModelSignal
→ conflict / targeted re-check
→ Final Supervisor
→ Trace / Report / UI / API
```

Human Review remains an optional product surface, not a mandatory release gate.

## 2. Final competition product state

| Area | v1.0.0 status |
|---|---|
| Document Intelligence | ALL79 complete; internal G2 target not met; frozen |
| Final Frontend / Product | PASS; one canonical workspace |
| Dynamic Market-X | PASS |
| Dynamic Model / Prediction / SHAP | PASS |
| Capability demonstrations | PASS 8/8 |
| Role-B runtime freeze | COMPLETE |
| Product-surface freeze | COMPLETE |
| One-shot Validation / final competition package | post-release governed operation |

The v1.0.0 product release is approved even though the repository's stricter internal `COMPETITION_READY` condition remains false because G2 is below target.

## 3. Document risk scope

Current production risk families include:

- cash runway / cash-burn pressure;
- continuous loss;
- revenue growth;
- customer / supplier concentration;
- redemption / special shareholder rights;
- material litigation / compliance;
- precommercial product.

Additional competition capabilities such as core-pipeline progress, text embellishment, related-party transaction and comparable-IPO valuation are represented as governed qualitative demonstrations where no Existing Gold is available; they are not mixed into M1/M2.

## 4. Final Role-B measurement

```text
Real LLM gated ALL79
cases = 79/79
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%

Best offline ALL79
cases = 79/79
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%
```

Internal G2 target:

```text
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

G2 therefore remains BLOCKED. The real-provider result and offline engineering reference remain explicitly separated.

Machine source:

```text
reports/v045_role_b/document_benchmark_summary.json
```

## 5. Dynamic Market-X — G3 PASS

v1.0.0 includes a governed historical + Dynamic PIT Market runtime.

```text
identity
→ validated frozen Market artifact
or Dynamic PIT Market source
→ feature builder
→ provenance / schema / hash / cutoff validation
→ MarketContext
```

Final strict audit facts include 562 governed cases, 0 integrity violations, 438 frozen-path cases and 124 Dynamic PIT cases.

When legal historical coverage is insufficient, `PARTIAL / UNAVAILABLE` is a correct output. Missing Market features are never converted to zero or guessed values.

## 6. Frozen Model / SHAP — G4 PASS

Role-D V2 is promoted and frozen.

```text
governed feature vector
+ frozen model / feature / alert manifests
→ runtime inference (no retraining)
→ uncalibrated_model_score
→ native SHAP / signed drivers
→ ModelSignal
```

Strict runtime audit:

```text
governed cases = 562
inference available = 540
available outside per-case handoff = 537
inference error = 0
published parity = 70/70
mismatch = 0
```

The model is a triage signal, not a probability forecast. Its known discrimination limitation remains disclosed.

## 7. Final Frontend / Product — G5 PASS

v1.0.0 supports:

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

The final presentation contract has one canonical workspace:

```text
START_DEMO.*       ─┐
START_JUDGE_DEMO.*  ├─→ app/streamlit_app.py
```

The judge launch commands are compatibility aliases, not a second presentation shell.

Canonical product information architecture:

```text
首页
→ 新建分析
→ 案例工作台
   ├─ 案例概览
   ├─ 原文证据
   ├─ 市场与模型
   └─ 综合结论与报告
→ 后台
```

All availability states are sourced from the runtime contract. UI code does not mint or fill missing Market/Model/Evidence values.

## 8. Stable release baseline

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
Evidence screenshots = 17/17 precise
seven-stage = 21/21
canonical replay = 66 files
G3/G4/G5/G6 = PASS
```

Final product-surface commit `006c7f3...`:

```text
tests = SUCCESS
Role D runtime = SUCCESS
Team demo runtime = SUCCESS
```

## 9. Non-negotiable governance

- Evidence for formal risk claims comes from real governed source material;
- LLM output is Evidence-scope constrained;
- UI does not guess page/bbox;
- exact numeric claims are backed by deterministic calculation where required;
- Market features are PIT-safe and missing is not zero;
- model scores are `uncalibrated_model_score`, not probabilities;
- Existing Gold remains immutable;
- Gold does not enter runtime;
- `UNJUDGED != negative`;
- no issuer/stock/case/page/Gold hardcoding;
- Validation is one-shot after freeze and cannot drive tuning;
- 2025 Blind outcomes are not used for optimization;
- secrets, licensed PDFs, raw market data, raw provider journals and absolute local paths are excluded from the public/submission package.

## 10. Release and readiness semantics

v1.0.0 uses two separate concepts:

```text
Product release = APPROVED
Internal COMPETITION_READY = FALSE
```

The product is complete enough to be formally versioned, demonstrated and packaged for the competition. The stricter internal readiness flag remains false because G2 did not meet the self-defined M1/M2 threshold and G7 still has local Validation/package operations pending.

See:

```text
docs/V1_RELEASE_ACCEPTANCE.md
docs/FINAL_SUBMISSION_STATUS.md
docs/SUBMISSION_RUNBOOK.md
```
