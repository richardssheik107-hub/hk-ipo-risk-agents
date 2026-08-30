# Competition Closure — v1.0.0 Final State

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Role-B runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final product-surface freeze：`006c7f302be5c278680d136371f6ef0db45fecc0`  
> Role-B benchmark SHA：`dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> Product release：**APPROVED**  
> Internal Competition Ready：**FALSE — G2 BELOW SELF-DEFINED TARGET**  
> Live Gate：`V1_RELEASE_ACCEPTANCE.md`

This document is no longer a development Roadmap. It records the final closure state and the remaining competition-submission operations that do not reopen product tuning.

## 1. Final Development truth

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

The internal G2 requirement remains:

```text
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

Result: 79/79 real LLM coverage was achieved, but G2 remains **BLOCKED**. Development tuning is closed.

## 2. Final track status

| Track | Final status | Post-release rule |
|---|---|---|
| A — Document Intelligence | **FROZEN / BELOW G2 TARGET** | no more score-driven tuning |
| B — Frontend / Product | **PASS / CLOSED** | one canonical workspace; fatal/truthful regression fixes only |
| C — Dynamic Market-X | **PASS / CLOSED** | regression protection only |
| D — Dynamic Model / SHAP | **PASS / CLOSED** | frozen identity; no retraining |
| E — Release / Submission | **OPERATIONS ONLY** | Validation / audit / package / defense assets |

## 3. Frozen product baseline

```text
Final Supervisor E1 = 3/3
M3 traceability = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
G3 Dynamic Market-X = PASS
G4 Dynamic Model / SHAP = PASS
G5 Final Frontend / Product = PASS
G6 Capability demonstrations = PASS
```

Final product-surface CI on `006c7f3...`:

```text
tests = SUCCESS
Role D runtime = SUCCESS
Team demo runtime = SUCCESS
```

## 4. Runtime and product-surface freeze

Machine source:

```text
reports/final_status/final_freeze_manifest.json
```

Two identities are intentionally separated:

```text
Role-B runtime freeze main = ab3390cc...
Final product-surface freeze = 006c7f30...
```

The later product-surface closeout unifies standard/judge launch commands on `app/streamlit_app.py`; it does not alter the frozen Role-B benchmark/runtime identity.

Release-document and packaging-only commits may follow these freezes if they do not modify frozen runtime semantics.

## 5. v1.0.0 release decision

The project is formally released as **v1.0.0 — Competition Submission Product Release**.

This means:

- the product feature set is closed;
- Role-B/Market/Model runtime identities are frozen;
- the approved frontend surface is frozen;
- current measurements are recorded without reinterpretation;
- known limitations are accepted and documented;
- the repository is suitable as the final competition product codebase.

It does **not** mean:

- G2 passed;
- `COMPETITION_READY=true`;
- offline metrics can be presented as real-LLM metrics;
- Validation has already been completed;
- unavailable channels can be shown as available.

## 6. Final product entrypoint

All supported launch commands converge on one canonical application:

```text
START_DEMO.bat       ─┐
start_demo.sh         ├─→ app/streamlit_app.py
START_JUDGE_DEMO.bat  ┤
start_judge_demo.sh  ─┘
```

The judge commands are compatibility aliases. There is no longer a second active presentation shell competing with the approved workspace.

## 7. Remaining competition-submission operations

These are the only active items after v1.0.0:

```text
1. one-shot ALL19 2024 Existing-Gold Validation
2. write reports/final_status/one_shot_validation_receipt.json
3. run exact-tree G5/G6 verification
4. fresh clone and execute validators / demo / frontend smoke
5. Blind / provenance / determinism / security / licensing / path audit
6. build final artifact index and SHA-256 manifest
7. build secure competition submission ZIP/source package
8. finalize PPT / defense script / Q&A / video or recording if required
```

No item above permits Development or Validation-driven retuning.

## 8. Submission material groups

### Product/code

- source code and allowed configs;
- README / Quickstart / Runbook;
- canonical Streamlit application and compatibility launchers;
- canonical offline replay;
- frozen model package and governed manifests;
- Market / Model / Evidence / report capability artifacts allowed by licensing.

### Measurement/governance

- final Role-B ALL79 summary;
- freeze manifest;
- one-shot Validation receipt after execution;
- G5/G6 acceptance manifests;
- Dynamic Market-X strict audit;
- Dynamic Model / SHAP strict audit;
- final CI evidence;
- security/licensing/provenance audit;
- artifact index and SHA256SUMS.

### Defense

- final PPT;
- 5–10 minute demo/recording if required;
- speaking notes;
- Q&A memo;
- fallback offline replay flow.

## 9. Non-negotiable governance

```text
Existing Gold immutable
UNJUDGED != negative
Gold never enters runtime
no issuer/stock/case/page/Gold hardcoding
Validation one-shot after freeze
no Validation-driven tuning
2025 Blind outcome not used for optimization
Market PIT-safe
missing != zero
no fabricated Evidence
uncalibrated model score != probability
fallback != real-provider success
no secrets / licensed PDFs / raw EOD / raw provider journal in public/submission package
```

## 10. Closure definition

Product development is **CLOSED**.

The remaining work is operational release/submission work only. Any future algorithmic improvement belongs to a post-competition version and must not silently alter the v1.0.0 frozen benchmark identity.
