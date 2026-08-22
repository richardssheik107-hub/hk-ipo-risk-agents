# v0.4 Role A — Integration Gate Handoff

> Status: **A PREPARATION COMPLETE — WAITING FORMAL PR-C GOVERNED MATERIALIZATION**  
> Owner: **A — Tech Lead / Pipeline**  
> Date: **2026-08-22**  
> Base main revision: **`1d441e6efb716f448b858e37e0d40954faf2a2da`**

This handoff records the Role-A tasks that can be completed before the governed
PR-C full run. It does **not** claim PR-C or PR-D formal Gate completion.

## 1. PR-C → PR-D contract is now frozen at the measured label semantics

PR-B EOD/session coverage and PR-C outcome coverage are different contracts.
PR-D must consume the PR-C outcome contract, not the PR-B EOD count.

```text
Official cohort                    438
PR-C 5D outcome available          424
PR-C 5D outcome unavailable         14
Development outcome available      354 / 368
Validation outcome available        70 / 70
missing_base_price                  12
no_eligible_session                  2
```

The PR-D orchestration must fail closed unless the upstream PR-C freeze manifest
contains `438 / 424 / 14`, zero build failures, zero determinism mismatches,
Validation isolation, and no 2025 Blind-y access. After reading all target
artifacts, PR-D independently re-checks the split counts and missing-reason
semantics rather than trusting only the manifest totals.

This prevents the historical `432 / 6` PR-B EOD coverage assumption from
re-entering the model-ready dataset contract.

## 2. Formal PR-D Gate checklist

PR-D may be declared COMPLETE / FROZEN only after formal PR-C freeze exists and
the real canonical materialization satisfies all of the following.

### Upstream binding

- PR-A freeze manifest is reviewed and hash-bound.
- PR-B freeze manifest is reviewed and hash-bound.
- PR-C freeze manifest is reviewed and hash-bound.
- PR-C policy hash is identical across all 438 target artifacts.
- PR-C threshold hash is identical across all 438 target artifacts.
- Validation did not fit or select the threshold.
- 2025 Blind outcome access is false.

### Cohort / target coverage

```text
Official coverage                 438
Model-ready                       424
Explicit target exclusions         14
Development model-ready           354
Validation model-ready              70
missing_base_price                  12
no_eligible_session                  2
```

No unavailable target is zero-imputed and no case is silently dropped.

### Identity / leakage

- `case_id`, stock code, cohort year, listing date and split agree across
  Production Document-X, Market-X Core and PR-C target.
- no duplicate case IDs;
- no orphan X or orphan y;
- identifiers, document IDs, Evidence IDs, Gold pages and target-derived values
  remain provenance only and never enter X;
- Oracle remains evaluation-only and cannot enter Production matrices.

### Feature contracts

- Market-X Core remains 30 positions;
- Production Document-X remains 100 positions;
- Market-X Extended remains optional and separately versioned;
- component-prefixed M/P/O/PM/OM feature order is deterministic;
- feature manifest drift fails closed.

### Reproducibility

- clean committed checkout;
- first materialization succeeds;
- `--resume` produces byte-equivalent canonical JSON/coverage content;
- source manifest hash, coverage hash, target policy hash and threshold hash are
  retained in the run manifest;
- full repository CI passes.

Only after the above checks pass may A issue the PR-D final Gate sign-off.

## 3. Oracle identity governance decision

Role E previously found Oracle artifacts whose `cohort_year` / `dataset_split`
can reflect annotation-packet metadata instead of the authoritative official IPO
identity. More 2024 expert annotations have since landed, so the old Oracle
coverage audit must be rerun before any formal PR-E interpretation.

### A decision

**Do not unfreeze or rewrite PR-A Production Document-X to repair Oracle-only
identity metadata.** Production remains frozen. **Do not silently rewrite frozen
Oracle artifacts in memory either.**

PR-D now separates the Production model-ready path from the evaluation-only
Oracle intersection:

- Production Document-X, Market-X Core and PR-C target identity mismatches remain
  hard failures;
- Oracle artifact integrity, schema, manifest and `evaluation_only` violations
  remain hard failures;
- if a valid frozen Oracle artifact differs only in `oracle.*` identity metadata,
  the Production row remains model-ready but that Oracle artifact is explicitly
  excluded from the Oracle intersection;
- coverage records `oracle_source_present`, `oracle_document_available` and the
  exact `oracle_exclusion_reason` so the exclusion cannot become a silent drop.

This is an isolation policy, not canonicalization. The old Oracle payload remains
immutable and its bad identity is never promoted into the canonical dataset.

The preferred long-term path is an **evaluation-only Oracle refresh /
canonicalization** using the authoritative official IPO identity. Any future
refreshed Oracle artifact should record at least:

```text
original artifact hash
original cohort_year / dataset_split
canonical cohort_year / dataset_split
authoritative identity source hash
normalization policy version
normalization reason
evaluation_only = true
```

This keeps the Production closed loop moving without weakening Oracle provenance
or invalidating PR-A Production hashes.

## 4. PR-G / Final Supervisor A-side contract review

The architectural direction of the Role-E preparation is acceptable with the
following non-negotiable integration boundaries:

1. `MarketContextProvider` must not be a `RiskAgent` and must not inject
   unverified market statements into `verified_risks`.
2. Final Supervisor may reference existing Evidence / Risk IDs only; referenced
   IDs must be a subset of its inputs.
3. Model output must remain a model score/prediction view and may not masquerade
   as Evidence, a legal/financial fact, or a calibrated probability unless a
   separate calibration Gate has passed.
4. Final Supervisor integrates and explains; it does not create new Document
   Evidence, new professional RiskItems, or unsupported market facts.
5. Missing market/model/document channels remain explicit state and must never
   be replaced by fabricated numeric placeholders.
6. Any changes to protected interfaces such as `agents/base.py` or
   `core/container.py` require focused contract tests and review after rebasing
   onto the then-current `main`.
7. The existing Role-E preparation must be rebased/reconciled before merge; its
   old milestone/UI status text must not be allowed to overwrite the current
   PR-C/PR-D state.

A therefore considers the **contract review complete**, but not PR-G itself.
PR-G remains a downstream formal milestone after PR-F.

## 5. Current authoritative execution state

```text
PR-A  COMPLETE / FROZEN
PR-B  COMPLETE / FROZEN
PR-C  implementation + A static audit + Gate correction complete
      FORMAL GOVERNED MATERIALIZATION PENDING
      NOT FROZEN
PR-D  engineering preparation merged; 424/14 integration contract prepared
      FORMAL MATERIALIZATION BLOCKED BY PR-C
PR-E/F engineering preparation exists but formal results are downstream
PR-G/H preparation exists but formal milestones are downstream
```

The immediate external blocker is the governed PR-C full run that produces the
numeric Development-only q25 threshold, 438 target artifacts, deterministic
rerun evidence and the small PR-C freeze manifest.

## 6. Role-A work completed in this branch

- corrected PR-D upstream acceptance from `432 / 6` to `424 / 14`;
- pinned `354 Development / 70 Validation` model-ready coverage;
- pinned `12 missing_base_price / 2 no_eligible_session` semantics;
- added downstream self-checks so manifest totals alone are insufficient;
- updated PR-D orchestration regression coverage;
- isolated Oracle-only identity drift from the Production dataset while keeping
  Oracle integrity/schema failures fail-closed and exclusions explicit;
- froze the PR-D formal Gate checklist;
- made the Oracle identity governance decision without unfreezing PR-A;
- completed the A-side PR-G/Final-Supervisor contract review;
- hardened the frozen Retriever ranking test so absence of the optional
  `lightgbm` research dependency skips only the LightGBM-specific check instead
  of crashing pytest collection;
- aligned `docs/README.md` and `docs/ROADMAP.md` with the active PR-C Gate and
  PR-D preparation state.

The only Role-A Gate work that cannot be completed from the public repository is
the final PR-C sign-off and the subsequent real PR-D materialization, because
both require governed runtime artifacts.
