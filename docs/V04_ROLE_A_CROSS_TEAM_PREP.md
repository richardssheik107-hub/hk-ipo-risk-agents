# v0.4 Role A Cross-Team Preparation Map

> Status: **HISTORICAL PREPARATION RECORD — PR-B SUBSEQUENTLY COMPLETE / FROZEN**
> Current result: [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
> Date: **2026-08-21**  
> Formal milestone: **PR-B — Market-X Core + Governed EOD Store**  
> Governance: formal Gate / mainline merge order remains PR-A → PR-B → PR-C → ...

## 1. Purpose

PR-A is complete and frozen. Role A acts as **Tech Lead / Pipeline / Integration / Governance**. This preparation package has now completed the repository-side work that can be done without the user's local governed market files and executable environment.

A owns the engineering boundary around:

```text
contract
→ orchestration
→ provenance
→ coverage
→ leakage guard
→ reproducibility
→ integration test
→ Gate review
```

A does not reopen frozen Document Intelligence, choose ungoverned market proxies, freeze D's target threshold, inspect 2025 blind y, or bind E's product layer to unfinished model logic.

## 2. Current repository audit: do not duplicate existing work

### Document / B foundations — frozen

Already available:

- `V03DocumentRiskSnapshot` and `v04_document_features_v1`;
- 100-position Production Document feature manifest/vectorizer;
- 438 / 438 frozen Production Document-X;
- 60-case Oracle Document-X evaluation-only path;
- document modeling dataset joins and blind protection.

B's next useful work is downstream traceability / QA when model-driver and final-explanation layers arrive, not another Retriever or Agent redesign.

### Market / C foundations — Core and Extended are separate

#### PR-B Market-X Core

Implemented on the current branch:

```text
schema: v04_ipo_market_context_features_v1
policy: ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Implementation:

```text
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

Core uses currently governed information only:

- authoritative official IPO identity / listing date;
- prior-IPO offer/context facts;
- governed IPO EOD;
- prior IPO 1D / 5D outcomes only after their target trading session has occurred strictly before the target IPO listing date.

#### Market-X Extended

Existing frozen Extended contract remains unchanged:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw + 10 missing indicators = 20 positions
```

Extended still lacks governed:

```text
HSI history
industry → benchmark authoritative mapping
industry-index history
HKEX total-market turnover
```

These are visible future source gaps, not a reason to fabricate data and not a PR-B Core blocker.

### Quant / D foundations

Already available:

- `MarketOutcomeLabel` 1D / 5D / 20D / 60D infrastructure;
- official listing-price return base;
- observed-session horizon semantics;
- Development / Validation / Blind guards;
- `V04ModelingDatasetBuilder`;
- `V04MarketAugmentedDatasetBuilder` for the existing Extended contract;
- Oracle Logistic baseline harness.

Do not formally freeze the final 5D classification threshold until PR-C. Do not alter PR-D dataset contracts prematurely merely to consume the new Core artifact; that is a versioned downstream decision after PR-B Gate acceptance.

### Product / E foundations

Already available:

- Oracle separation is explicit and evaluation-only;
- `IPOAnalysisService` remains the product-facing service boundary;
- current Document report / Streamlit path remains the stable v0.3 compatibility layer.

Product work must wait for frozen model-output contracts before claiming PR-G/PR-H completion.

## 3. What Role A has completed for PR-B

The web-side preparation has completed the following unblocked work:

### A1 — Correct governed EOD cohort selection

`scripts/build_v04_ipo_eod_store.py` now selects the official cohort by:

```text
official_match_status == matched
AND official_listed_date.year in 2020–2024
```

It no longer treats document `source_year` as modeling cohort year.

The EOD filtered store also:

- expects 438 official cases on a full run;
- preserves `OBJECT_ID` source-record provenance;
- hashes raw EOD + official bridge;
- records target case IDs hash and date coverage;
- explicitly states `S_DQ_AMOUNT` is per-security only;
- fails closed on incompatible cache provenance.

### A2 — Harden deterministic Core feature path

`src/ipo_risk/market/ipo_market_context_features.py` now has:

- stable raw feature order;
- deterministic manifest hash;
- adjacent `__missing` indicators;
- strict future-IPO exclusion;
- strict not-yet-known-outcome exclusion;
- deterministic vectorization;
- explicit rejection of manifest-key drift.

### A3 — Implement canonical PR-B orchestration

`scripts/run_v04_pr_b.py` now orchestrates:

```text
Official 2020–2024 metadata
→ governed EOD store
→ prior-IPO historical label/context preparation
→ per-case Core feature artifact
→ explicit coverage
→ failure report
→ provenance freeze
→ conflict-safe resume
→ deterministic rebuild verification
```

It supports:

```text
--case-ids
--limit
--resume
--verify-determinism
```

It contains no option to read 2025 blind outcomes.

### A4 — Add integration / leakage tests

Added or expanded:

```text
tests/unit/test_v04_ipo_eod_store.py
tests/unit/test_v04_pr_b_orchestration.py
tests/unit/test_ipo_market_context_features.py
```

Coverage includes:

- official listing-year selection;
- official cohort drift;
- streaming filtered-store behavior;
- source-record provenance retention;
- no total-market-turnover proxy misuse;
- future IPO exclusion;
- future/not-yet-known prior-outcome exclusion;
- missingness/manifest stability;
- 2025 blind rejection;
- same-provenance resume;
- changed-content conflict fail-closed;
- one-case failure remains visible in coverage;
- deterministic rebuild semantics.

### A5 — Freeze acceptance / handoff documentation

Current implementation and Gate rules are frozen in:

```text
docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md
docs/V04_ROLE_A_CODEX_HANDOFF.md
AGENTS.md
```

## 4. A → B: remaining Document / Agent responsibility

B should preserve this traceability chain for later PR-E/F/G/H integration:

```text
prospectus page
→ Evidence
→ RiskItem
→ V03DocumentRiskSnapshot risk position
→ Production Document feature
→ model driver
→ final explanation
```

Do not:

- tune Retriever in v0.4 mainline;
- change the eight canonical risks merely to improve market metrics;
- weaken Evidence / Calculation requirements;
- collapse `pending`, `needs_review`, `rejected`, `not_emitted`, `unavailable` into safe zero;
- reorder the frozen 100 Document feature positions.

No additional B implementation is required to unblock the current PR-B Gate.

## 5. A → C: remaining Market / PIT responsibility

C's immediate responsibility is **domain QA of the existing PR-B Core implementation and real local source execution**, not rebuilding the feature formulas.

On a machine with the governed competition market data:

```text
1. run targeted tests
2. run full pytest
3. run a 5-case Development pilot
4. inspect Core artifacts / coverage / failure semantics
5. run the full 438-case Core materialization
6. run --resume --verify-determinism
7. report actual coverage and failures
```

If authoritative Extended sources later become available, C may integrate them under the existing Extended versioned contract. Missing HSI/industry/turnover data must remain explicit until then.

## 6. A → D: remaining Quant / ML responsibility

After PR-B Gate acceptance, D owns the formal downstream sequence.

### PR-C

Freeze 5D weak-performance target policy using **2020–2023 Development only**. 2024 cannot choose the threshold; 2025 y remains closed.

### PR-D

Build a canonical model-ready dataset with exact identity joins and explicit feature/version provenance. Because the repository now distinguishes Core from the older Extended 20-position snapshot, PR-D must make a deliberate versioned dataset-contract decision rather than silently changing an old feature order.

### PR-E / PR-F

Run fair M/P/O/PM/OM baselines first, then LightGBM + explainability only after baseline diagnostics.

Required experiment provenance should carry at least:

```text
dataset/content hash
Document manifest hash
Market Core/Extended manifest hash as applicable
outcome policy version
train/validation split
model family
hyperparameters
random seed
code revision
result artifact hash/version
```

Oracle remains a diagnostic ceiling, never Production input.

## 7. A → E: remaining Oracle / Product responsibility

Maintain the hard separation:

```text
Production runtime ─X→ expert_results / Oracle Gold
```

Future Final Supervisor integration should consume governed outputs:

```text
Document assessment
+ Market assessment
+ frozen model output
+ explainability drivers
+ evidence / provenance
+ missingness / conflicts
→ Final Supervisor
```

Market Agent / Final Supervisor may explain frozen model outputs but may not alter model scores or invent evidence.

Streamlit remains behind `IPOAnalysisService` / a controlled upper service. UI may not directly read raw market CSVs, model internals or Agent internals.

## 8. Cross-team integration rules owned by A

For every downstream PR, A reviews:

- public/protected interface impact stated explicitly;
- new cross-module data versioned/Pydantic where appropriate;
- source + version + provenance recorded;
- failures structured and auditable;
- no local absolute path or secret committed;
- no large runtime data committed;
- 2025 blind governance preserved;
- deterministic tests exist for new boundaries;
- full tests actually run before claiming green;
- readiness numbers updated only from real execution evidence.

## 9. What is truly left before PR-B Gate

Repository-side implementation preparation is done. The remaining work requires the executable local checkout and governed market CSV:

```text
1. install/verify dependencies
2. run PR-B targeted tests
3. run full pytest
4. run 5-case pilot
5. run 438-case PR-B Core materialization
6. run --resume --verify-determinism
7. fix only real runtime/test defects if any
8. if Gate passes, freeze measured PR-B completion evidence
```

The exact commands are in [`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md).

Do not create another branch for this handoff unless the user explicitly asks. Do not formally enter PR-C until the PR-B Gate is accepted.
