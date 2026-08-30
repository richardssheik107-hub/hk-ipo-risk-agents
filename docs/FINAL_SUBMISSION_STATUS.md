# Final Submission Status — v1.0.0

> Release: `v1.0.0`  
> Release date: `2026-08-30`  
> Role-B runtime freeze main SHA: `ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final product-surface freeze SHA: `006c7f302be5c278680d136371f6ef0db45fecc0`  
> Role-B benchmark SHA: `dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> Product release: **APPROVED**  
> Internal `COMPETITION_READY`: **FALSE — G2 below self-defined target**

This is the final competition-submission status for v1.0.0. Product development is closed. Remaining work is local/authorized submission governance and presentation-material preparation.

## 1. Final Development truth

| Mode | Cases | M1 | M2 | Interpretation |
|---|---:|---:|---:|---|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** | best deterministic/offline engineering reference |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** | formal provider-backed Development result |

Internal G2 threshold:

```text
M1 >= 80%
M2 >= 85%
real_llm_cases = 79/79
```

Therefore G2 remains **BLOCKED**. v1.0.0 release approval does not change this gate.

## 2. Frozen product capabilities

- real prospectus PDF parsing and physical-page Evidence;
- Financial / Legal / Business multi-agent document analysis;
- deterministic Calculation and specialized Verifier;
- Document Supervisor and Final Supervisor;
- conflict detection and bounded re-check;
- governed Dynamic Market-X with PIT-safe missingness/provenance;
- frozen Role-D V2 inference and native SHAP;
- Offline Demo Replay;
- Historical Governed IPO;
- Fresh New-IPO Analysis;
- one canonical Streamlit workspace;
- standard/judge compatibility launchers that both enter `app/streamlit_app.py`;
- Evidence screenshots / trace / single-case / batch reports;
- G5 product acceptance PASS;
- G6 capability manifest 8/8 PASS.

## 3. Final gate state

| Gate | Status | Meaning at v1.0.0 |
|---|---|---|
| G0 Runtime / contracts / CI | PASS | final product surface green on core workflows |
| G1 Stable final-three baseline | PASS | canonical demo/regression baseline protected |
| G2 ALL79 Document Intelligence | **BLOCKED** | accepted known limitation |
| G3 Dynamic Market-X | PASS | governed runtime closed |
| G4 Dynamic Model / SHAP | PASS | V2 frozen inference + SHAP closed |
| G5 Final Frontend / Product | PASS | one canonical truthful product workspace |
| G6 Capability demonstrations | PASS | 8/8 qualitative proofs |
| G7 Freeze / Validation / package | **PARTIAL** | runtime freeze complete; local Validation/package actions remain |

## 4. Final integration / CI truth

The final product-surface commit is:

```text
006c7f302be5c278680d136371f6ef0db45fecc0
fix(frontend): unify judge launcher with approved workspace
```

On that commit:

```text
tests = SUCCESS
Role D runtime = SUCCESS
Team demo runtime = SUCCESS
```

The UI closeout did not reopen Role-B tuning or modify the frozen Development benchmark.

## 5. Machine-readable source of truth

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/submission_closeout_status.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json
```

`reports/final_status/one_shot_validation_receipt.json` does not yet exist and must only be created by the actual one-shot Validation execution.

## 6. Completed release closeout

- final Role-B benchmark recorded without metric reinterpretation;
- Role-B runtime identity promoted into the integrated release line;
- Development optimization closed;
- runtime freeze manifest recorded;
- G3/G4/G5/G6 closed;
- final standard/judge launch paths unified onto the approved canonical workspace;
- final product-surface CI green;
- documentation source-of-truth hierarchy established;
- package version promoted to `1.0.0`;
- v1.0.0 release notes and v1 release acceptance finalized;
- development owner documents closed into final-state records.

## 7. Remaining local / authorized submission actions

These cannot be replaced by repository text edits and do not reopen product development:

1. **One-shot Validation** — run ALL19 2024 Existing-Gold Validation once under the frozen identity.
2. **Validation receipt** — write `reports/final_status/one_shot_validation_receipt.json` with `one_shot=true`, `post_hoc_tuning=false`, `blind_2025_y_accessed=false`.
3. **Exact-tree G5/G6 check** — run `python scripts/check_final_product_capabilities.py` on the exact final submission tree.
4. **Fresh clone verification** — install and run validators/demo/frontend smoke from a second clean clone.
5. **Security / licensing / provenance / path audit** — verify no secrets, licensed PDFs, raw market data, raw provider journals or local paths leak into the package.
6. **Final artifact index** — path / owner / gate / required / size / SHA-256 / allowed status.
7. **Secure competition package** — source/config/docs/artifacts allowed by the platform + `SHA256SUMS.txt`.
8. **Defense materials** — final PPT, speaking script, Q&A memo, key Evidence screenshots and video/recording if required.

## 8. Recommended competition material set

### Core submission

- source code and allowed configuration;
- `README.md`;
- `docs/RELEASE_NOTES_V1.0.0.md`;
- `docs/V1_RELEASE_ACCEPTANCE.md`;
- `docs/FINAL_SUBMISSION_STATUS.md`;
- `docs/SUBMISSION_RUNBOOK.md`;
- `docs/TEAM_QUICKSTART.md`;
- final technical/project description;
- competition PPT / demo video if required.

### Technical evidence

- final Role-B benchmark summary;
- freeze manifest;
- one-shot Validation receipt after execution;
- G5/G6 manifests;
- Market-X strict audit;
- Dynamic Model / SHAP strict audit;
- frozen Role-D model/feature/alert manifests;
- approved Evidence screenshot manifests/images;
- canonical demo replay;
- final CI evidence;
- final artifact index + `SHA256SUMS.txt`.

## 9. Known limitations to state explicitly

- self-defined G2 target was not met;
- real LLM gated performance is below best offline on the final Development benchmark;
- strict schema/Evidence-scope guards can reject otherwise plausible LLM augmentation;
- source-edition / exact-anchor provenance constrains some M2 units;
- Dynamic Market-X honestly degrades outside governed PIT coverage;
- Role-D V2 remains an uncalibrated triage signal and ROC-AUC is below 0.5;
- remote LLM prose is not byte-for-byte deterministic;
- restricted market data and prospectus PDFs are not redistributed publicly.

## 10. Final release statement

**v1.0.0 is approved as the final competition submission product release.**

It is acceptable to submit and demonstrate this version with its documented limitations. It is not acceptable to claim G2 PASS, `COMPETITION_READY=true`, or to substitute offline scores for real-LLM scores.

All future algorithmic work belongs to a post-competition version and must not rewrite the v1.0.0 frozen benchmark truth.
