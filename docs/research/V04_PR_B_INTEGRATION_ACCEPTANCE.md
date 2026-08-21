# V04 PR-B Integration & Acceptance Contract

> Status: **IMPLEMENTATION-READY CONTRACT / PR-B NOT YET PASSED**  
> Date: **2026-08-21**  
> Formal milestone: **PR-B — Market-X Core + Governed EOD Store**  
> Owners: **C = Market/PIT domain owner; A = Pipeline/Integration/Gate**

## 1. Objective

PR-B must turn the already-frozen pre-listing Market-X semantics into a **real, governed, resumable and auditable 438-case materialization path**.

The task is integration/materialization, not feature redesign.

Reuse these existing contracts and engines:

```text
src/ipo_risk/schemas/market.py
src/ipo_risk/schemas/market_features.py
src/ipo_risk/market/features.py
src/ipo_risk/providers/competition_market.py
src/ipo_risk/providers/market_reference.py
src/ipo_risk/modeling/market_dataset.py
scripts/build_v04_ipo_eod_store.py
```

Frozen feature policy/schema:

```text
feature policy: v04_prelisting_market_features_v1
feature schema: v04_market_features_v1
10 raw positions + 10 missing indicators = 20 positions
```

No PR-B implementation may silently change those names, order, formulas, windows or missing semantics.

## 2. Required real-source families

Current real source readiness is:

| Family | Current state | PR-B requirement |
|---|---|---|
| Official IPO identity / listing date | available | reuse authoritative catalog |
| Target/prior IPO OHLCV | 432 / 438 | reuse governed provider/store; explicit unavailable for six cases |
| HSI daily close | missing | add governed source + stable index ID + version/checksum |
| Industry mapping | missing | add authoritative industry→benchmark mapping, preferably effective-dated |
| Industry-index history | missing | add governed benchmark series + stable IDs + provenance |
| HK total-market turnover | missing | add governed total-market turnover series + unit/scope/source/version |

Hard prohibitions:

- Hang Seng Bank is not an HSI proxy;
- workbook industry name alone is not authoritative benchmark mapping;
- single-security `S_DQ_AMOUNT` is not total-market turnover;
- missing source must remain missing; it cannot be filled with zero or a convenient substitute.

## 3. Source contract

Every real source integrated in PR-B must have an auditable record containing at minimum:

```text
logical_source_id
source_name
source_version
portable path or stable upstream identifier
sha256/checksum when file-backed
coverage range
record count or mapped entity count where meaningful
unit / market scope where applicable
availability status
provenance notes
```

If raw files live outside Git, the repository may commit only the portable manifest/metadata needed to validate them. Do not commit large raw market files.

A changed checksum/version is a provenance change. Resume must not silently reuse artifacts produced from a different source state.

## 4. Canonical orchestration entry point

Implement a thin CLI:

```text
scripts/run_v04_pr_b.py
```

Suggested interface:

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b \
  --resume
```

Useful diagnostic options:

```text
--case-ids <comma-separated>
--limit <n>
--verify-determinism
```

The CLI should **orchestrate existing domain logic**, not duplicate feature formulas from `PreListingMarketFeatureEngine`.

Full default scope is the governed official 2020–2024 listing-year universe: **438 cases**. A full run must fail closed if the official target universe unexpectedly drifts.

PR-B is X-side work. Do not add an option that reads 2025 blind outcomes.

## 5. Execution context / provenance freeze

Before materialization, write an execution context that records at least:

```text
pr_b_version
git_revision
market_feature_schema_version
market_feature_manifest_hash
market_feature_policy_version
official universe / bridge hash
source manifest hash
selected case count
selected case IDs hash
Python / relevant package versions
blind_outcomes_included = false
```

Requirements:

- portable paths only in committed/reusable metadata;
- no API key/token;
- identical provenance may be resumed/reused;
- incompatible existing provenance must fail closed and require a new output root or explicit reviewed rebuild path.

## 6. Per-case build flow

Canonical flow:

```text
Official IPO metadata
      ↓
PIT target context
      ↓
Governed HSI / industry / turnover / prior-IPO inputs
      ↓
PreListingMarketFeatureEngine
      ↓
PreListingMarketFeatureSnapshot
      ↓
MARKET_FEATURE_MANIFEST_V1 vectorization
      ↓
Market feature artifact + hashes
      ↓
Coverage / PIT / failure audit
```

For every target case, either produce a valid snapshot/feature artifact or an explicit structured status explaining why it is unavailable/partial/failed.

One case failure must not silently remove it from coverage or contaminate other cases.

## 7. Point-in-time invariants

For target listing date `T`, all feature inputs must satisfy their real information-availability boundary.

At minimum:

```text
observation_date < T
market/reference trading_date <= observation_date
```

The implementation must preserve the existing engine behavior that excludes listing-day and future rows before feature computation.

For prior IPO outcomes used as **historical context X**:

```text
prior_label.target_trading_date <= target_observation_date
```

Therefore a prior IPO may be known as an IPO but its 5D result is not usable until that 5D target session had actually occurred by the target IPO observation date.

Required PIT tests should prove that:

1. adding/changing target IPO listing-day or post-listing data cannot change valid pre-listing X;
2. future benchmark rows are ignored/rejected;
3. future prior-IPO outcomes are excluded;
4. `observation_date >= listing_date` is rejected;
5. a mismatched identity/reference series is rejected;
6. missing source becomes explicit missingness, not zero.

## 8. Coverage contract

Generate both machine-readable detailed coverage and aggregate summary.

Recommended per-case fields:

```text
case_id
stock_code
cohort_year
dataset_split
listing_date
market_snapshot_status
market_document_available / market_x_available
observation_date
benchmark_reference_id
industry_reference_id
available_raw_feature_count
missing_raw_feature_count
hsi_family_available
industry_family_available
recent_ipo_family_available
turnover_family_available
failure_stage
failure_reason
market_snapshot_hash
market_feature_hash
market_feature_manifest_hash
market_feature_policy_version
source_manifest_hash
pit_status
```

A full PR-B coverage table must contain **exactly one explicit row per governed target case**. No silent drops.

Aggregate summary should include at minimum:

```text
selected_case_count
market_x_materialized_count
full_feature_family_count
partial_market_x_count
failed_count
failure_count_by_stage
missing_reason_counts
feature-family availability counts
pit_pass_count / pit_fail_count
market_feature_manifest_hash
coverage content hash
```

Do not define `partial` as failure simply because a legitimately unavailable family is represented by the frozen missingness contract. Distinguish domain-level missing input from pipeline failure.

## 9. Failure taxonomy

Use structured stage + reason. Suggested stages:

```text
preflight
metadata
source_resolution
benchmark
industry_mapping
industry_series
turnover
prior_ipo_context
feature_build
vectorization
artifact_write
pit_validation
determinism
```

Examples of valid reasons:

```text
missing_benchmark_source
missing_industry_mapping
missing_industry_series
missing_turnover_source
insufficient_history
no_recent_ipo_sample
source_checksum_conflict
identity_mismatch
duplicate_source_record
post_listing_leakage
artifact_provenance_conflict
```

Do not catch a broad exception and convert every failure into an indistinguishable generic success/skip state.

## 10. Artifact layout

Recommended runtime layout:

```text
reports/v04_pr_b/
  execution_context.json
  source_inventory.json
  market_status.json
  market_snapshots/
    <case_id>.json
  market_features/
    <case_id>.json
  coverage.csv
  coverage_summary.json
  failure_report.csv
  pit_audit.json
  determinism_report.json
```

These are runtime/research artifacts. Large full-run outputs should remain ignored/local unless a small sanitized freeze manifest or completion report is explicitly selected for Git.

## 11. Resume and determinism

PR-B should inherit the spirit of PR-A's conflict-safe behavior:

- same source/config/code provenance + same artifact content → reuse allowed;
- existing artifact with incompatible provenance/content → fail closed;
- `--resume` is not permission to overwrite changed provenance;
- deterministic artifacts must use canonical ordering / serialization where hashing matters.

A verification run should check at least:

```text
selected cases checked
snapshot hash mismatches
feature hash mismatches
manifest hash mismatches
coverage semantic hash
PIT violations
passed
```

Normal resume lifecycle fields may change from `created` to `reused`; semantic hashes must not drift.

## 12. Existing EOD filtered store audit

`scripts/build_v04_ipo_eod_store.py` already provides a useful streaming target-IPO EOD filter with raw/bridge hashes.

Before treating it as a frozen PR-B component, Codex/C should audit and, if needed, correct its cohort selection logic so it follows the **authoritative official listing-year / official-universe membership**, not document `source_year`. The repository has known cases where source year differs from official listing year.

Any correction must preserve explicit provenance and add regression tests proving the official 438-case universe is selected correctly.

## 13. Tests required before PR-B PASS

At minimum add/retain coverage for:

- frozen Market manifest/order/hash stability;
- strict pre-listing cutoff;
- listing-day/future mutation does not alter X;
- prior-IPO label availability cutoff;
- explicit missing source/missing reason;
- HSI/industry/turnover source provenance;
- no single-stock turnover proxy;
- duplicate reference/activity rejection;
- official-universe cohort selection;
- 2025 blind-y absence / fail-closed guard;
- full coverage row count and no silent drop;
- resume identical provenance;
- resume conflicting provenance fails closed;
- one-case failure isolation;
- deterministic rerun hashes;
- existing Document/Market dataset and v0.3 regressions remain green.

Full repository validation before claiming PASS:

```bash
python -m pip install -e '.[dev,retrieval-research]'
pytest -q
```

Do not claim tests passed unless they were actually run.

## 14. Pilot then full-run protocol

Recommended sequence:

### Pilot

Run a deterministic small Development subset that covers:

- complete reference input;
- industry mapping present/missing;
- recent IPO context present/empty;
- at least one explicit source-missing path.

Verify artifacts, hashes, PIT and resume behavior.

### Full 438

Run the governed 2020–2024 universe. One case failure must not stop the batch.

Then run `--resume --verify-determinism` and compare semantic hashes.

Only after a real full run may readiness documents be updated with new Market-X coverage numbers.

## 15. PR-B PASS Gate

PR-B is PASS only when all of the following are true:

```text
[ ] official 438 target cases all appear exactly once in coverage
[ ] real Market source inventory is versioned and auditable
[ ] HSI source integrated or explicitly governed as unavailable under the agreed PR-B scope
[ ] industry mapping / series integrated or explicitly governed as unavailable under the agreed PR-B scope
[ ] total-market turnover integrated or explicitly governed as unavailable under the agreed PR-B scope
[ ] no prohibited proxy substitution
[ ] all Market X obey strict point-in-time cutoff
[ ] no 2025 blind outcome accessed
[ ] frozen 20-position Market manifest unchanged
[ ] all failures/missingness are explicit
[ ] snapshot/feature/source hashes are recorded
[ ] deterministic rerun passes
[ ] targeted tests pass
[ ] full repository test suite passes
[ ] completion/readiness docs reflect real run evidence
```

If the team's intended definition of “Market-X Core” deliberately allows some extended source families to remain missing, that scope decision must be explicit in the PR-B completion report and must not be misreported as full 20-position real-source coverage. Missing indicators are valid model inputs; fabricated proxies are not.

## 16. Stop condition

After PR-B PASS/freeze:

```text
STOP
→ review Gate
→ then formally start PR-C
```

Do not use this preparation contract as authorization to merge PR-C target-policy work into main before PR-B is formally accepted.
