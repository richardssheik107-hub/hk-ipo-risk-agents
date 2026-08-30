# HK IPO Risk Agents v1.0.0 — Competition Submission Release

> Release date: `2026-08-30`  
> Release type: **final competition submission product release**  
> Role-B runtime freeze: `ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final product-surface freeze: `006c7f302be5c278680d136371f6ef0db45fecc0`  
> Role-B benchmark commit: `dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`

## Release decision

`v1.0.0` marks the end of feature development for the competition version of HK IPO Risk Agents. It is a formal product release, not a claim that every internal research target was met.

The repository's self-defined `COMPETITION_READY` gate remains false because G2 did not reach the internal M1/M2 threshold. This release keeps that limitation explicit rather than weakening the benchmark or replacing real-provider results with offline results.

The final frontend closeout also removes a second presentation shell: standard and judge launch commands now open the same approved `app/streamlit_app.py` workspace. The judge launchers remain as compatibility commands with the same fail-fast runtime and clone-ready checks.

## Final Development measurements

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

The provider-backed result is the formal real-LLM Development measurement. The offline result is retained separately as an engineering reference.

## What ships in v1.0.0

- Real prospectus PDF parsing with physical-page Evidence identity.
- Financial, Legal and Business agents.
- Deterministic Calculation plus specialized Verifier paths.
- Document supervision and Final Supervisor.
- Conflict detection and bounded targeted re-check.
- Governed Dynamic Market-X with PIT-safe provenance and honest missingness.
- Frozen Role-D V2 inference with native SHAP / signed drivers.
- `uncalibrated_model_score` semantics; scores are not probabilities.
- Offline Demo Replay.
- Historical Governed IPO mode.
- Fresh New-IPO Analysis mode.
- One canonical Streamlit reader workspace with standard/judge compatibility launchers.
- Evidence screenshots, trace, single-case reports and batch reports.
- API/UI capability surfaces.
- Hash-bound G5 product acceptance and G6 capability manifests.

## Stable regression baseline

```text
Final Supervisor E1 = 3/3
M3 traceability = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
G3 / G4 / G5 / G6 = PASS
```

On the final product-surface freeze `006c7f3...`, GitHub Actions `tests`, `Role D runtime` and `Team demo runtime` all completed successfully.

## Gate truth at release

| Gate | Status |
|---|---|
| G0 Runtime / contracts / CI | PASS |
| G1 Stable final-three baseline | PASS |
| G2 ALL79 Document Intelligence | **BLOCKED** |
| G3 Dynamic Market-X | PASS |
| G4 Dynamic Model / SHAP | PASS |
| G5 Final Frontend / Product | PASS |
| G6 Capability demonstrations | PASS |
| G7 Freeze / Validation / package | **PARTIAL** |

The v1.0.0 product release does not alter these gate results.

## Known limitations

- The self-defined G2 target was not met.
- Real LLM gated performance is below the best deterministic/offline result, showing that the current strict schema/Evidence-scope augmentation path can introduce negative value on some units.
- Some M2 misses remain constrained by source-edition / exact-anchor provenance.
- Dynamic Market-X can return `PARTIAL` or `UNAVAILABLE` when governed pre-listing history is insufficient.
- The frozen model is an uncalibrated triage signal; it is not a probability and is not a promise of post-listing performance.
- Remote LLM prose is not byte-for-byte deterministic.
- Licensed prospectuses, raw EOD, restricted market data, raw provider journals and secrets are not distributed in the public repository.

## Governance

- Existing Gold remains immutable.
- `UNJUDGED != negative`.
- Gold does not enter runtime Retriever / Prompt / Agent paths.
- No issuer/case/page/Gold-text hardcoding is accepted.
- Market features remain PIT-safe and missing values are not zero-filled.
- Fallback is never reported as real-provider success.
- 2025 Blind outcomes are not used for optimization.

## Post-release competition packaging tasks

The product release is complete, but the competition submission environment still needs to perform the governed packaging steps that require authorized/local execution:

1. one-shot ALL19 2024 Existing-Gold Validation under the frozen identity;
2. write `reports/final_status/one_shot_validation_receipt.json`;
3. run exact-tree G5/G6 verification on the final submission commit;
4. fresh-clone verification in a clean directory;
5. security / licensing / provenance / path audit;
6. build final artifact index and SHA-256 manifest;
7. create the secure competition submission package;
8. prepare final PPT, defense script, Q&A and recording/video if required.

These steps must not reopen Development tuning.

## Launch

```text
Windows canonical UI: START_DEMO.bat
Windows judge alias:   START_JUDGE_DEMO.bat
Unix canonical UI:     ./start_demo.sh
Unix judge alias:      ./start_judge_demo.sh
```

All four commands ultimately launch `app/streamlit_app.py`; the judge commands are maintained for presentation compatibility, not as a separate UI implementation.

See `README.md`, `docs/V1_RELEASE_ACCEPTANCE.md`, `docs/FINAL_SUBMISSION_STATUS.md`, `docs/FRONTEND_JUDGE_FACING_HANDOFF.md` and `docs/SUBMISSION_RUNBOOK.md` for the final source-of-truth documents.
