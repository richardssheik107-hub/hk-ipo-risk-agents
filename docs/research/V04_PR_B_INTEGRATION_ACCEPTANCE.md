# V04 PR-B Integration & Acceptance Contract

> Status: **IMPLEMENTED IN REPO / LOCAL MATERIALIZATION + GATE EVIDENCE STILL REQUIRED**  
> Date: **2026-08-21**  
> Formal milestone: **PR-B — Market-X Core + Governed EOD Store**  
> Owners: **C = Market/PIT domain owner; A = Pipeline/Integration/Gate**

## 1. Objective

PR-B turns the already available IPO market foundation into a **real, governed, resumable and auditable Market-X Core** for the official 2020–2024 cohort.

The authoritative master plan distinguishes two layers:

```text
Market-X Core
  = inputs already governed today
  = official IPO metadata
  + governed target/prior-IPO EOD
  + prior-IPO offer/context facts known before the target listing

Market-X Extended
  = HSI / industry benchmark / total-market turnover families
  = remains explicitly missing until authoritative sources are supplied
```

Missing Extended sources are **not a PR-B Core failure**. They also may not be replaced with proxies.

PR-B is therefore allowed to pass its Core Gate while HSI / industry benchmark / turnover remain explicitly unavailable, provided the Core is fully audited and the Extended gaps remain visible.

## 2. Frozen implementation boundary

### 2.1 PR-B Core

Core implementation reuses:

```text
src/ipo_risk/providers/competition_market.py
src/ipo_risk/market/labels.py
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

Core feature contract:

```text
schema:  v04_ipo_market_context_features_v1
policy:  ipo_market_context_policy_v1
raw:     15 positions
missing: 15 adjacent __missing positions
total:   30 positions
```

The Core feature families are:

```text
ipo_count_30d
ipo_count_60d
log_prior_ipo_funds_raised_30d
log_prior_ipo_funds_raised_60d
prior_ipo_funds_raised_30d_sample_count
prior_ipo_funds_raised_60d_sample_count
recent_ipo_break_rate
recent_ipo_return_5d
recent_ipo_1d_sample_count
recent_ipo_5d_sample_count
same_industry_ipo_count_180d
same_industry_recent_break_rate
same_industry_recent_return_5d
same_industry_recent_1d_sample_count
same_industry_recent_5d_sample_count
```

Every raw value has an adjacent explicit `__missing` indicator. Missing outcome samples are not converted to zero.

### 2.2 Market-X Extended

The existing frozen Extended contract remains unchanged:

```text
src/ipo_risk/schemas/market_features.py
src/ipo_risk/market/features.py
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw + 10 missing indicators = 20 positions
```

It includes HSI, industry benchmark, recent IPO, turnover and volatility families. PR-B Core does **not** modify this schema or invent benchmark rows merely to force materialization.

Until governed sources are supplied, these Extended source families remain explicit gaps:

```text
hsi
industry_mapping
industry_index
market_turnover
```

## 3. Governed EOD store

Canonical builder:

```text
scripts/build_v04_ipo_eod_store.py
```

The current filter schema is:

```text
v04_ipo_eod_filter_v2
```

### 3.1 Cohort rule

The target cohort must be selected by:

```text
official_match_status == matched
AND official_listed_date.year in {2020, 2021, 2022, 2023, 2024}
```

`source_year` is a prospectus/document attribute and is **not** a safe modeling-cohort selector. The builder therefore uses `official_listed_date`, and a regression test covers a source-year/listing-year mismatch.

A full run expects exactly:

```text
438 official cases
```

Unexpected cohort drift fails closed.

### 3.2 EOD provenance

The filtered store preserves:

```text
OBJECT_ID
S_INFO_WINDCODE
TRADE_DT
OHLCV
S_DQ_AMOUNT
S_DQ_PRECLOSE
S_DQ_ADJCLOSE
```

`OBJECT_ID` is retained as the source record identifier.

`S_DQ_AMOUNT` is retained only as the original **per-security** source column. It is never reinterpreted as HKEX total-market turnover.

The EOD manifest records at least:

```text
filter_schema_version
selection_policy
official_listing_years
expected_official_case_count
target_case_count
target_case_ids_sha256
raw_eod_sha256
bridge_sha256
row_count
distinct_target_securities
target_security_count
min_trading_date
max_trading_date
source_record_id_column
S_DQ_AMOUNT semantics
```

Cache reuse is allowed only when the raw EOD hash, bridge hash, filter schema and cohort-selection policy are compatible.

## 4. Core point-in-time policy

For target IPO listing date `T`, Core features may use only information known strictly before `T`.

### 4.1 Prior IPO identity / offer facts

A prior IPO can enter a target context only if:

```text
prior_listing_date < T
```

Static prior IPO facts such as authoritative funds raised and official industry description may be used only for such prior IPOs.

### 4.2 Prior IPO outcomes used as X

1D / 5D outcomes are legitimate historical context features only after their target session has actually occurred.

The Core policy therefore requires:

```text
prior_1d_target_trading_date < T
prior_5d_target_trading_date < T
```

If a prior 5D target session occurs on the target IPO listing date itself, that outcome is **not** known strictly before listing and is excluded.

### 4.3 Target IPO leakage prohibition

The target IPO's own listing-day or post-listing price history never enters its Market-X Core.

2025 blind outcomes are not read by PR-B.

## 5. Canonical orchestration entry point

Implemented CLI:

```text
scripts/run_v04_pr_b.py
```

Default full run:

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b
```

Pilot / diagnostics:

```text
--case-ids <comma-separated>
--limit <n>
--resume
--verify-determinism
```

The CLI has no option to include 2025 blind outcomes.

## 6. Execution-context freeze

Before Core artifacts are accepted, execution context records:

```text
pr_b_version
git_revision
Python / package versions
Core schema version
Core policy version
Core manifest hash
Core manifest body
EOD filter schema
EOD manifest
Official bridge hash
Source-manifest hash
Extended source availability
Selected case count / IDs / IDs hash
blind_outcomes_included = false
post_listing_target_data_used_as_target_x = false
```

A full run requires a clean Git working tree so the materialized output can be tied to a committed revision.

Existing output is reused only with `--resume` and identical content/provenance. Different content fails closed and requires a new reviewed output root.

## 7. Per-case artifact

For every selected official case, PR-B Core writes one deterministic feature artifact containing:

```text
case_id
stock_code
cohort_year
dataset_split
listing_date
cutoff_semantics
core_feature_schema_version
core_feature_policy_version
core_feature_manifest_hash
feature_names
feature_values
raw_values
official bridge hash
IPO EOD hash
content_hash
```

Core formulas are not duplicated in the CLI.

## 8. Coverage contract

A full run must emit exactly one coverage row per official 2020–2024 case.

Fields include:

```text
case_id
stock_code
cohort_year
dataset_split
listing_date
core_market_x_status
core_market_x_available
available_raw_feature_count
missing_raw_feature_count
core_feature_hash
core_feature_manifest_hash
core_feature_policy_version
pit_status
one_day_outcome_history_available
five_day_outcome_history_available
hsi_extended_source_status
industry_mapping_extended_source_status
industry_index_extended_source_status
market_turnover_extended_source_status
failure_stage
failure_reason
```

The semantic coverage row intentionally does not encode transient lifecycle state such as `created` versus `reused`; therefore the coverage hash can remain stable across a legitimate resume rerun.

Required aggregate summary:

```text
selected_case_count
core_market_x_materialized_count
failed_count
failure_count_by_stage
core_feature_manifest_hash
coverage_content_hash
governed EOD coverage / hashes
Extended source status
blind_outcomes_included = false
```

## 9. Failure policy

One case failure must not silently remove that case or stop unrelated cases.

Current Core orchestration reports failures as structured:

```text
case_id
stage
reason
```

Artifact/provenance conflicts are different from a normal missing-data case. They fail closed rather than silently overwrite an existing output.

## 10. Determinism

`--verify-determinism` rebuilds each selected Core artifact from the same governed inputs and compares the complete deterministic payload.

Required evidence:

```text
checked_case_count
mismatch_count
mismatch_case_ids
passed
coverage_content_hash
```

For a valid rerun:

```text
mismatch_count = 0
coverage semantic hash unchanged
```

## 11. Tests required before Gate acceptance

Repository tests now cover the implementation-level guards for:

- official listing-year selection rather than document `source_year`;
- official cohort drift rejection;
- governed EOD streaming filter;
- source `OBJECT_ID` retention;
- no reinterpretation of `S_DQ_AMOUNT` as total-market turnover;
- strict future-IPO exclusion;
- not-yet-known prior outcome exclusion;
- adjacent missing indicators and stable Core manifest hash;
- 2025 blind rejection;
- resume reuse versus conflict;
- Extended missing sources remaining explicit instead of becoming fake Core data;
- one-case failure remaining visible in coverage;
- deterministic rebuild behavior.

The actual repository test suite still must be run in a real checkout before PR-B can be marked PASS:

```bash
python -m pip install -e '.[dev,retrieval-research]'
pytest -q
```

No document may claim green tests merely because test code exists.

## 12. Local run sequence still required

### B-Pilot

Run a deterministic Development pilot:

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b_pilot \
  --limit 5
```

Inspect:

- governed EOD manifest;
- Core feature artifacts;
- coverage rows;
- missing semantics;
- Extended-source statuses;
- failure report.

### B-Full

Then run the full 438-case cohort:

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b
```

### B-Audit

Rerun from unchanged inputs:

```bash
python scripts/run_v04_pr_b.py \
  --catalog-dir data/catalog \
  --data-root <LOCAL_MARKET_ROOT> \
  --output-dir reports/v04_pr_b \
  --resume \
  --verify-determinism
```

Only measured local results may update actual PR-B coverage counts.

## 13. PR-B Core PASS Gate

PR-B Core can be accepted only when all are true:

```text
[ ] full official cohort resolves to 438 cases
[ ] governed EOD store builds from official listing-year selection
[ ] every 438 case appears exactly once in coverage
[ ] every successful Core row has stable feature hash
[ ] every failure has stage + reason
[ ] Core manifest hash is frozen and recorded
[ ] PIT tests pass
[ ] no target post-listing data enters target X
[ ] no 2025 blind outcome is read
[ ] resume is conflict-safe
[ ] deterministic rerun reports 0 mismatches
[ ] full pytest is green
[ ] local run summary is frozen in a completion report / small manifest
```

The following are **not** Core PASS requirements, but must remain visible limitations until resolved:

```text
HSI source
industry benchmark mapping
industry-index history
HKEX total-market turnover
```

## 14. Explicitly prohibited

PR-B must not:

- use `source_year` as the modeling cohort selector;
- use Hang Seng Bank as HSI;
- guess an industry benchmark from company name or LLM output;
- treat an industry description as an authoritative index mapping;
- use per-security `S_DQ_AMOUNT` as total-market turnover;
- fill missing source families with zero;
- fabricate a benchmark row merely to create an `observation_date`;
- alter the frozen Extended `v04_market_features_v1` contract without a versioned decision;
- access 2025 blind y;
- start PR-C formally before PR-B Gate acceptance.

## 15. Current repository status after preparation

The repository now contains the unblocked PR-B Core implementation and tests:

```text
scripts/build_v04_ipo_eod_store.py        cohort/governed-store hardening
scripts/run_v04_pr_b.py                   canonical Core orchestration
src/ipo_risk/market/ipo_market_context_features.py
                                         deterministic Core feature/vector path
tests/unit/test_v04_ipo_eod_store.py      EOD governance tests
tests/unit/test_v04_pr_b_orchestration.py orchestration / leakage / resume tests
tests/unit/test_ipo_market_context_features.py
                                         PIT / manifest / missingness tests
```

What remains is execution evidence from a machine that actually has the governed market CSV plus the full test environment. Until that evidence exists, status is **implemented, not yet Gate-passed**.
