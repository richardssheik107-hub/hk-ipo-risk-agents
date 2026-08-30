# Changelog

This file is the release-level changelog. Detailed experiment-by-experiment history remains available in Git history and the governed research/ledger artifacts.

## 1.0.0 — 2026-08-30

**Competition Submission Product Release**

### Product

- Finalized the end-to-end HK IPO risk intelligence product around real prospectus Evidence.
- Financial / Legal / Business multi-agent document analysis.
- Deterministic Calculation and specialized Verifier paths.
- Document supervision, conflict detection, bounded re-check and Final Supervisor.
- Judge-facing and standard Streamlit workspaces.
- Offline Demo Replay, Historical Governed IPO and Fresh New-IPO Analysis modes.
- Evidence screenshots, trace, single-case and batch reports.

### Market / Model

- Governed Dynamic Market-X with PIT-safe provenance and honest missingness.
- Frozen Role-D V2 package with runtime inference and native SHAP.
- Model scores remain `uncalibrated_model_score`; they are not probabilities.
- Missing Market/Model inputs fail closed rather than being zero-filled or guessed.

### Final Development measurement

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | 70/102 = 68.63% | 103/191 = 53.93% |
| Real LLM gated | 79/79 | 61/102 = 59.80% | 93/191 = 48.69% |

The real-LLM gated result is the formal provider-backed Development measurement. The offline result is retained separately as an engineering reference.

The repository's self-defined G2 threshold (M1 >=80%, M2 >=85%, real LLM 79/79) was not met, so G2 remains **BLOCKED**. v1.0.0 is therefore a formal product/submission release with a documented internal quality-gate gap, not a claim that `COMPETITION_READY=true`.

### Governance / Release

- Existing Gold remains immutable; `UNJUDGED != negative`.
- Gold does not enter runtime Retriever / Prompt / Agent paths.
- No issuer/case/page/Gold-text hardcoding is accepted.
- 2025 Blind outcomes are not used for optimization.
- Runtime identity is frozen and recorded in `reports/final_status/final_freeze_manifest.json`.
- Final Role-B benchmark truth is recorded in `reports/v045_role_b/document_benchmark_summary.json`.
- G3 Dynamic Market-X = PASS.
- G4 Dynamic Model / SHAP = PASS.
- G5 Final Frontend / Product = PASS.
- G6 Capability demonstrations = PASS.
- G7 remains PARTIAL until governed one-shot Validation and final competition packaging are completed in the authorized environment.

### Known limitations

- Real LLM augmentation under strict schema/Evidence-scope guards underperforms the best offline path on the final Development benchmark.
- Source-edition / exact-anchor provenance limits some Evidence coverage.
- Dynamic Market-X may return `PARTIAL` / `UNAVAILABLE` outside governed PIT coverage.
- Role-D V2 remains an uncalibrated triage signal and ROC-AUC remains below 0.5.
- Remote LLM prose is not byte-for-byte deterministic.
- Licensed prospectuses, raw market data, secrets and raw provider journals are intentionally not distributed in the public release.

### Release documentation

- `docs/RELEASE_NOTES_V1.0.0.md`
- `docs/V1_RELEASE_ACCEPTANCE.md`
- `docs/FINAL_SUBMISSION_STATUS.md`
- `docs/SUBMISSION_RUNBOOK.md`
- `docs/TEAM_QUICKSTART.md`

## 0.3.0 — Multi-Agent Risk Analysis

Introduced the multi-agent Financial / Legal / Business risk-analysis product line and the first broad competition-oriented risk workflow.

## 0.2.0 — Real Document Slice

Moved from architecture-only work to a real-document path with prospectus parsing and a functioning evidence-grounded risk slice.

## 0.1.0 — Architecture MVP

Initial architecture MVP, contracts and early agent/runtime scaffolding.

---

Historical v0.4.x development was an intensive competition integration/optimization phase rather than a standalone final GitHub release. Its detailed Batch/Bundle experiments, parser/retrieval fixes, Evidence work, replay implementation, Market-X, Model/SHAP, frontend and governance changes remain traceable through Git history and `docs/V046_ROLE_B_EXPERIMENT_LEDGER.md` / `reports/` artifacts.
