# v0.4 Role A Cross-Team Preparation Map

> Status: **PREPARATION PACKAGE — READY FOR CODEX / TEAM USE**  
> Date: **2026-08-21**  
> Formal milestone: **PR-B — Market-X Core + Governed EOD Store**  
> Governance: preparation may run in parallel; formal Gate / mainline merge order remains PR-A → PR-B → PR-C → ...

## 1. Purpose

PR-A is complete and frozen. Role A now acts as **Tech Lead / Pipeline / Integration / Governance**. The goal of this preparation package is not to take over B/C/D/E domain decisions, but to make their work easy to integrate, audit, test and hand off.

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

A does **not** reopen frozen Document Intelligence, choose ungoverned market proxies, freeze D's target threshold, or bind E's product layer to unfinished model logic.

## 2. Repository audit: do not duplicate what already exists

The following foundations are already implemented and should be reused rather than rebuilt:

### Document / B foundations

- `V03DocumentRiskSnapshot` and `v04_document_features_v1`;
- 100-position Production Document feature manifest/vectorizer;
- 438 / 438 frozen Production Document-X;
- 60-case Oracle Document-X evaluation-only path;
- document modeling dataset joins and blind protection.

### Market / C foundations

- `src/ipo_risk/schemas/market_features.py`;
- frozen `v04_prelisting_market_features_v1` policy;
- frozen `v04_market_features_v1` manifest;
- `PreListingMarketFeatureEngine`;
- `MarketFeatureValue` explicit missingness/provenance;
- 10 raw Market features + 10 `__missing` indicators = 20 positions;
- `InMemoryMarketReferenceDataProvider` for deterministic tests;
- governed target-IPO OHLCV foundation with 432 / 438 coverage;
- `scripts/build_v04_ipo_eod_store.py` as an existing filtered-store foundation;
- Market augmented dataset join and 2025 feature-only blind exporter.

### Quant / D foundations

- `MarketOutcomeLabel` 1D / 5D / 20D / 60D infrastructure;
- official listing-price return base;
- observed-session horizon semantics;
- Development / Validation / Blind guards;
- `V04ModelingDatasetBuilder`;
- `V04MarketAugmentedDatasetBuilder`;
- Oracle Logistic baseline harness.

### Product / E foundations

- Oracle separation is already explicit and evaluation-only;
- `IPOAnalysisService` remains the product-facing service boundary;
- current Document report / Streamlit path remains the stable v0.3 compatibility layer.

Therefore the next work is primarily **real-source integration, orchestration, audit and downstream contracts**, not a second implementation of the existing schemas or feature engines.

## 3. A → B: Document / Agent preparation

B owns Document Intelligence quality and downstream explanation. Since v0.3 and PR-A are frozen, A should help B mainly through regression and traceability boundaries.

### A can prepare / review now

1. Preserve the frozen Document feature manifest and its deterministic hash.
2. Preserve the semantic chain:

```text
prospectus page
→ Evidence
→ RiskItem
→ V03DocumentRiskSnapshot risk position
→ Production Document feature
→ future model driver
→ final explanation
```

3. Add downstream integration tests when model/supervisor layers arrive so a feature driver can still be traced to its risk code and, where available, Evidence / Calculation provenance.
4. Keep `pending`, `needs_review`, `rejected`, `not_emitted`, `unavailable` distinct; never collapse non-verified states into safe zero.
5. Reject changes that silently reorder the frozen 100 positions.

### A must not do on B's behalf

- Retriever tuning;
- prompt optimization;
- changing the eight canonical risks;
- weakening Evidence / Calculation requirements;
- changing frozen Document semantics merely to improve later model scores.

### B handoff condition

B's downstream work is integration-ready when existing Document-X can be consumed without changing its frozen schema and later explanations can reference canonical `risk_code` / provenance rather than raw Retriever candidates.

## 4. A → C: Market / PIT preparation — highest current priority

C is the PR-B domain owner. A owns the integration and Gate shell around C's real market sources.

### Already frozen and reusable

```text
PreListingMarketFeatureContext
PreListingMarketFeatureSnapshot
MarketFeatureManifest
MarketFeatureVector
PreListingMarketFeatureEngine
v04_market_features_v1
```

Do not create a second Market-X schema.

### A preparation responsibilities

1. Define one canonical PR-B orchestration entry point: `scripts/run_v04_pr_b.py`.
2. Require governed source records for HSI, industry mapping / industry series and total-market turnover.
3. Require exact point-in-time checks for every target IPO:

```text
source_market_date <= observation_date < listing_date
```

4. Require explicit missingness instead of neutral-zero substitution.
5. Produce one explicit coverage row for every official 2020–2024 target case.
6. Require structured failure stage + reason; no silent skip.
7. Record source path/identifier, dataset version and checksum/hash in execution provenance.
8. Make resume conflict-safe: identical provenance may reuse; differing provenance must fail closed or use a new output root.
9. Add deterministic rerun verification for snapshots/features/coverage semantic content.
10. Keep 2025 outcome inaccessible; PR-B is X-side work.

The detailed acceptance contract is in [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md).

## 5. A → D: Quant / ML preparation

D owns methodology and final empirical decisions. A should provide reproducible containers and leakage guards without freezing D's research choices early.

### Already available

- outcome label infrastructure;
- deterministic Document + label joins;
- deterministic Document + Market joins;
- blind feature-only exporters;
- Oracle baseline foundation.

### A can prepare / enforce

1. Keep split policy immutable:

```text
2020–2023 Development
2024      Validation
2025      Blind
```

2. Ensure 2025 y has no API path into development/training materialization.
3. Require one-row / one-identity canonical dataset assembly with exact `case_id`, stock, listing date and split checks.
4. Require future experiment records to carry at minimum:

```text
dataset/content hash
Document manifest hash
Market manifest hash
outcome policy version
train/validation split
model family
hyperparameters
random seed
code revision
result artifact hash/version
```

5. Keep M / P / O / PM / OM comparisons on the same cohort, y, split, preprocessing and model family.
6. Treat Oracle as a diagnostic ceiling, never as Production input.

### A must not do on D's behalf

- freeze the final weak-performance threshold before PR-C;
- tune on 2024 and still call it untouched validation;
- inspect/use 2025 blind y;
- jump directly to LightGBM before PR-E baseline diagnostic.

## 6. A → E: Oracle / Product preparation

E owns Oracle integration, Final Supervisor and final product path. A should keep the architecture clean while later components are still unfrozen.

### A can prepare / enforce

1. Maintain a hard dependency boundary: Production runtime must not depend on `expert_results/` or Oracle Gold features.
2. Define the future Final Supervisor integration shape around already-governed outputs rather than internal module files:

```text
Document assessment
+ Market assessment
+ frozen model output
+ explainability drivers
+ evidence / provenance
+ missingness / conflicts
→ Final Supervisor
```

3. Require the final product to preserve uncertainty and missing information rather than filling unsupported conclusions.
4. Keep Streamlit behind `IPOAnalysisService` / a controlled upper service; UI must not directly read raw Market CSV, model files or Agent internals.
5. Allow UI skeleton work only with mock/stable contracts; do not treat it as PR-H completion.

### A must not do on E's behalf

- implement a Final Supervisor that can override the frozen model score;
- let a Market Agent invent market evidence;
- bind UI to temporary PR-B / PR-C file layouts as if they were public APIs.

## 7. Cross-team integration rules owned by A

For every downstream PR, A should review the following before Gate PASS:

- public/protected interface impact is stated explicitly;
- new cross-module data is Pydantic/versioned where appropriate;
- source + version + provenance is recorded;
- failures are structured and auditable;
- no local absolute path / secret enters Git;
- no large runtime data is committed;
- 2025 blind governance is preserved;
- deterministic tests exist for the new boundary;
- full test suite is run before claiming green;
- generated readiness numbers are updated only after a real run.

## 8. Current priority for A

Role A should spend most effort on C / PR-B now:

```text
1. PR-B integration acceptance contract       READY IN DOCS
2. real governed source adapters              CODEX / C
3. canonical PR-B orchestration CLI           CODEX / A
4. coverage + PIT + failure + determinism      CODEX / A
5. real pilot and 438-case run                LOCAL / TEAM
6. PR-B Gate review                           A
```

B/D/E preparation remains useful, but should not pull engineering attention away from the current formal Gate.

## 9. Codex handoff

The exact implementation queue, stop conditions and ownership split are in:

[`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md)

Codex should read that file together with `AGENTS.md`, the master plan and the PR-B acceptance contract before editing production code.
