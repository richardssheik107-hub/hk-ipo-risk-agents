# v0.4 Role A → Codex Handoff

> Status: **READY FOR IMPLEMENTATION**  
> Date: **2026-08-21**  
> State: **PR-A COMPLETE / FROZEN; PR-B NEXT**

## 1. Read first

Before coding, read:

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
4. `docs/V04_ROLE_A_CROSS_TEAM_PREP.md`
5. `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`
6. `docs/research/V04_PRELISTING_MARKET_FEATURES.md`
7. `docs/research/V04_DATA_READINESS.md`

Inspect existing implementations/tests before editing. The Market schema, feature engine, dataset builders and blind guards already exist and should not be duplicated.

## 2. Hard boundaries

Do not reopen v0.3 Document Intelligence, change the frozen 20-position Market vector without an explicit versioned decision, use target post-listing data as X, access 2025 blind outcomes, use single-stock `S_DQ_AMOUNT` as total-market turnover, infer industry benchmarks from company names, or jump to PR-C before PR-B passes.

## 3. Immediate PR-B implementation queue

### B1 — Audit real source availability

Inspect the local data roots and `data/catalog/v04_source_manifest.json` for:

- HSI daily close;
- industry-to-index mapping;
- industry-index history;
- HK total-market turnover;
- IPO EOD / prior-IPO history.

For each available source record identity, path/upstream ID, format, coverage, version/checksum, unit/scope and PIT suitability. If a required source is absent, report it as a blocker instead of fabricating a substitute.

### B2 — Audit/harden `scripts/build_v04_ipo_eod_store.py`

The current script filters using document `source_year`. Confirm that target selection matches the authoritative official listing-year / official-universe cohort. If not, correct it and add regression tests for known source-year/listing-year mismatches. Preserve streaming behavior and source hashes.

### B3 — Add real governed reference-market adapters

`InMemoryMarketReferenceDataProvider` is test-only. For approved sources that really exist, implement deterministic adapters returning the existing `MarketReferenceBar` / `MarketActivityObservation` contracts.

Adapters must validate rows, reject duplicate reference/date records, preserve source/version provenance, enforce exclusive pre-listing access and have contract tests.

`src/ipo_risk/providers/` is protected: state compatibility impact and add tests before changing it.

### B4 — Implement `scripts/run_v04_pr_b.py`

Create a thin orchestration CLI. Reuse `PreListingMarketFeatureEngine`; do not copy its formulas.

Required responsibilities:

```text
load official 2020–2024 cohort
freeze execution/source provenance
resolve governed market sources
build one Market snapshot per case
vectorize with frozen manifest
write per-case status
build coverage and failure reports
run PIT audit
support conflict-safe resume
support deterministic verification
```

Detailed behavior and artifact fields are frozen in `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`.

### B5 — Add PR-B integration tests

Cover at least:

- official cohort preflight;
- strict `observation_date < listing_date`;
- future target/reference rows cannot change X;
- future prior-IPO labels excluded;
- source provenance/checksum recorded;
- missing source remains explicit;
- no prohibited turnover proxy;
- one case failure does not remove other coverage rows;
- same-provenance resume reuses;
- changed provenance fails closed;
- deterministic snapshot/feature/coverage hashes;
- 2025 blind outcomes are not accessed.

Reuse existing Market math tests rather than duplicating them.

### B6 — Pilot, full run, determinism

Run a small Development pilot first. Check artifact layout, PIT, missingness, hashes and resume behavior.

Then run the full governed 438-case 2020–2024 cohort, followed by resume + determinism verification. One case failure must not stop the batch.

Only real run results may update readiness counts.

### B7 — Full validation and PR-B completion evidence

Run:

```bash
python -m pip install -e '.[dev,retrieval-research]'
pytest -q
```

If PR-B actually passes, update `docs/research/V04_DATA_READINESS.md`, `docs/ROADMAP.md` and `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md` from measured results, and add a concise PR-B completion report/freeze manifest. Do not claim green tests or coverage without running them.

## 4. Stop at the PR-B Gate

After the acceptance checklist passes, stop and report:

- files changed;
- protected/public interface impact;
- actual source/Market-X coverage;
- targeted/full test results;
- remaining source limitations;
- whether PR-B is ready to accept.

Do not formally advance to PR-C until PR-B is accepted.

## 5. Work remaining after PR-B

### PR-C — D lead

Freeze the 5D weak-performance target and classification threshold using 2020–2023 Development only. Keep 2024 out of threshold selection and 2025 y closed. Produce outcome policy manifest and leakage tests.

### PR-D — D lead + A integration

Reuse existing dataset builders to materialize canonical Document X + Market X + frozen Y assets. Audit identity joins, duplicates/orphans, missingness, M/P/O/PM/OM cohorts, provenance and feature-only blind export.

### PR-E — D lead

Run fair M/P/O/PM/OM baselines with the same cohort, target, split, preprocessing and model family. Use Oracle only as an evaluation ceiling/error-attribution path.

### PR-F — D lead

After baseline diagnostics, implement LightGBM, time-aware Development CV, frozen 2024 validation, SHAP, calibration/error analysis and reproducible experiment manifests.

### PR-G — E lead

Implement Market Agent + Final Supervisor on frozen model outputs. Agents may explain, not alter model scores or invent evidence.

### PR-H — E lead + A integration

Complete Streamlit Full E2E for 3–5 real IPOs through the controlled service boundary.

## 6. Remaining ownership

| Role | Remaining work |
|---|---|
| A | PR-B orchestration/integration/Gate review; later cross-module integration |
| B | frozen Document downstream QA / explanation traceability |
| C | authoritative source acquisition/approval, real PIT adapters and Market-X domain QA |
| D | PR-C target policy, PR-D dataset, PR-E/F modeling |
| E | Oracle isolation QA, PR-G supervisor, PR-H product integration |

## 7. Human/C decisions Codex must not guess

Stop and ask if these are not already governed:

- authoritative HSI source;
- authoritative industry benchmark taxonomy/mapping;
- authoritative industry-index histories;
- authoritative HK total-market turnover source/scope/unit;
- whether PR-B Core requires all extended source families real, or allows explicitly missing extended families under a narrower documented Core definition.

No scope decision permits proxy substitution.

## 8. Suggested Codex instruction

> Read `AGENTS.md`, `docs/V04_ROLE_A_CODEX_HANDOFF.md` and `docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`. Audit current PR-B foundations and real local source availability first. Do not duplicate the frozen Market feature engine/schema. Implement unblocked PR-B tasks in order, preserve PIT/no-leakage and 2025 blind-y boundaries, run tests, and stop at the PR-B Gate. Report missing authoritative sources as blockers rather than inventing them.
