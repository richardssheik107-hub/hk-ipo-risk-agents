# v0.4 PR-G — A Gate Review

> Review date: **2026-08-24**  
> Reviewer: **A — Tech Lead / Pipeline**  
> Reviewed main revision: `1b2260b9081ad4af71ba49d33710828a24dcbeac`  
> PR-G implementation PR: **#104**  
> Decision: **GATE REVIEW PASS — local freeze materialization still required**

## 1. Decision

A accepts the PR-G implementation and governance design as the correct baseline integration layer.

The following PR-G requirements are satisfied by merged code, tests, CI and the real-PDF attestation recorded in `V04_PR_G_COMPLETION_REPORT.md`:

- frozen PR-F evidence is consumed fail-closed;
- model output remains `uncalibrated_model_score`, never probability;
- Final Supervisor creates no new RiskItem or Evidence;
- referenced risk/evidence ids are input subsets;
- uncertainty is explicit and deterministic;
- conflicts are preserved rather than silently dropped;
- mock market numbers cannot be surfaced as real market facts;
- v0.4 wiring is opt-in and legacy v0.3 configs remain unchanged;
- a real 706-page prospectus completed the v0.4 PDF → 13-section Final Report path;
- PR #104 head CI completed successfully (`tests` and `expert-annotation-phase2`).

Therefore **PR-G implementation review = PASS**.

The freeze builder intentionally requires a local real prospectus/runtime and intentionally refuses to write into `reports/frozen/`. The remote GitHub-only review cannot honestly reconstruct the local prospectus hash or `final_supervision_content_hash`. Those values must not be invented.

During A review, one additional provenance defect was found and fixed before freeze: the draft builder previously used a placeholder `date(2024, 1, 1)` for every real run. `scripts/build_v04_pr_g_manifest.py` now requires `--listing-date YYYY-MM-DD`, passes that authoritative date into `IPOAnalysisRequest`, and records the case identity in the draft. A PR-H/PR-G freeze run may not use a placeholder listing date because Market-X is point-in-time and listing date is a provenance boundary.

Accordingly:

```text
PR-G implementation / contract review     PASS
PR-G local freeze manifest materialization REQUIRED_LOCAL_ACTION
PR-H preparation                           UNBLOCKED
PR-H formal execution                      starts after the frozen PR-G manifest is committed
```

## 2. Protected-interface ruling

A accepts the PR-G protected-interface changes introduced by #104.

### Accepted

- `MarketContextProvider.context(profile, market)` receives the already-loaded snapshot. This removes the provenance risk of fetching a second independent market snapshot inside one analysis.
- `MarketContextView.observations` uses structured `MarketObservation` objects rather than strings.
- `ModelPredictionView.drivers` uses structured `ModelDriver` objects rather than strings.
- `FinalSupervisionResult.conflicts` is retained explicitly.

The two structured-element changes are technically breaking relative to the unused preparation contract introduced earlier, but A accepts them because the prior string contracts had not been wired into a production workflow, while the structured form is required to preserve missing reasons, SHAP sign and validation semantics. Future changes to these types require normal compatibility review.

### Not changed

- `RiskAgent.analyze()` contract;
- frozen PR-A–PR-F builders/policies;
- v0.3 report contract;
- 2025 Blind policy;
- probability/calibration semantics.

## 3. Finding 1 ruling — governed Market-X must not be flattened into the legacy snapshot

PR-G correctly identified that the modeling path uses `PreListingMarketFeatureSnapshot`, while the old runtime path uses the v0.2 `MarketSnapshot`.

A decision:

> **Do not make the legacy `MarketSnapshot` the new source of truth and do not stamp PR-B lineage onto a value that did not come from the governed Market-X pipeline.**

PR-H should add a governed runtime path that consumes a `PreListingMarketFeatureSnapshot` (or a lossless product-facing projection of it) directly. The legacy `MarketSnapshot` remains for v0.3 compatibility only.

Required invariants:

1. case identity, listing date and split must match the governed catalog;
2. observation date must remain strictly before listing date;
3. raw feature order and schema/policy versions must validate;
4. each available observation carries its own provenance;
5. missing industry benchmark / turnover remain explicit missing states, never neutral zero;
6. the current governed CSMAR HSI integration may be surfaced only through its actual provenance;
7. mock values remain permanently non-production.

This is now a **PR-H preflight implementation task**, not a reason to reopen PR-B.

## 4. Finding 2 ruling — PR-F per-case outputs remain runtime artifacts

A does **not** authorize committing the complete PR-F runtime directory or model bulk to Git merely to make the UI convenient.

PR-H should consume a checksummed local/runtime handoff bound to the frozen PR-F result. The existing `pr_f_run_dir` / Tier-2 validation design is retained.

The handoff must contain only what the product needs, for example:

```text
run_manifest / model-result identity
case_predictions needed by the selected demo cohort
single-IPO SHAP/top-driver records needed by the selected demo cohort
SHA256SUMS.txt
README with source/freeze hashes and exclusions
```

It must exclude:

```text
2025 Blind y
post-listing target labels used only for evaluation
raw licensed data
secrets
absolute local paths
unrelated model artifacts
```

Before any per-case score is shown, PR-G/PR-H must verify the handoff against the frozen PR-F `model_result_hash`; mismatch fails closed.

This is a **runtime handoff requirement for PR-H**, not a reason to reopen PR-F.

## 5. Remaining PR-H preflight items

Before PR-H can claim a full 3–5 case E2E demo, it must close these items:

1. materialize and commit the final PR-G freeze manifest from a real local run using the **authoritative listing date**;
2. wire governed `PreListingMarketFeatureSnapshot` into the runtime Market Context channel;
3. provide the frozen PR-F per-case score/driver runtime handoff for the chosen demo cases;
4. remove stale UI stage wording that still says PR-B/PR-F are blocking gates;
5. keep `ReportSection.section_id` deterministic in the v0.4 generator; do not modify the frozen v0.3 contract merely for cosmetic uniformity;
6. run the full CI suite and the 3–5 real-case E2E demo matrix;
7. update README / ROADMAP / five-person plan to formal PR-H only after the PR-G frozen manifest exists.

Canonical local draft command after this review:

```bash
PYTHONPATH=src python scripts/build_v04_pr_g_manifest.py \
  --prospectus <REAL_PROSPECTUS_PDF> \
  --company <AUTHORITATIVE_COMPANY_NAME> \
  --stock-code <AUTHORITATIVE_STOCK_CODE> \
  --listing-date <YYYY-MM-DD> \
  --data-dir <GOVERNED_LOCAL_DATA_DIR> \
  --output-dir reports/v04_pr_g
```

The resulting `reports/v04_pr_g/v04_pr_g_manifest_draft.json` must be inspected and independently validated before any A freeze action. Do not copy it mechanically if `analysis_status != completed`, traceability fails, identity/date is wrong, or any blind/probability/fake-market invariant fails.

The missing system `libomp` behavior is an environment/CI policy issue, not a PR-G gate blocker. CI must continue proving the LightGBM extra is actually installed rather than silently skipping model tests.

## 6. Gate boundary

This review does **not** authorize:

- 2024 post-hoc model tuning or score inversion;
- 2025 Blind y access;
- rebuilding PR-A–PR-F to make results look better;
- fake market proxies;
- large-scale Retriever/LLM/Agent rewrites before CH-2 benchmark evidence;
- calling uncalibrated score a probability.

Once the local PR-G freeze manifest is committed and validated, the formal current Gate moves to **PR-H — Streamlit Full E2E + 3–5 real IPO demo**.
