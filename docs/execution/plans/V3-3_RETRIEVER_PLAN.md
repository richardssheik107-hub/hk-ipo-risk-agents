---
plan_id: V3-3
title: Generalize v0.3 Retriever Query Families
status: APPROVED
revision: 1
base_commit: 6847f67df0e275576e6689c62a50b0269d4cfd84
branch: feat/v03-retriever-query-families
owner: tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md
---

# V3-3 Retriever Query Families

## Goal

Extend the existing deterministic KeywordDocumentRetriever from the v0.2 cash / operating-cash-flow retrieval slice into the v0.3 multi-domain query-family retriever required by Financial, Legal, and Business Agents.

The implementation must add query families for:

- revenue
- continuous_loss
- customer_concentration
- supplier_concentration
- redemption_rights
- material_litigation_compliance
- commercialization_status
- core_product_pipeline

The existing DocumentRetriever public interface must remain unchanged.

## Background

The current KeywordDocumentRetriever already provides deterministic prospectus Evidence retrieval for cash, ending cash balance and operating cash flow.

It already supports:

- Simplified Chinese, Traditional Chinese and English aliases
- normalized matching
- deterministic ranking
- financial statement context weighting
- negative-context suppression
- stable Evidence IDs
- traceable Evidence snippets
- limit handling
- empty result on no match
- no fallback evidence

v0.3 requires this mechanism to support Financial, Legal and Business query families without introducing embeddings, vector databases, LLMs or project-specific hard-coded prospectus rules.

The current v0.3 golden manifest on main contains only synthetic fixtures. Therefore this Plan validates the retriever with deterministic contract tests and existing regressions. Real golden-case retrieval metrics are a follow-up after reviewed V3-1 cases are merged.

## Project Rules

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/PROJECT_MASTER_CHECKLIST.md
- docs/execution/README.md

## Inputs

- src/ipo_risk/retrieval/base.py
- src/ipo_risk/retrieval/keyword.py
- tests/contract/test_keyword_retriever.py
- tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
- existing DocumentChunk and Evidence public schemas
- existing v0.2 cash and operating-cash-flow regression behavior

Do not use the 2025 blind-test cohort for rule selection, alias tuning, section-weight tuning or acceptance decisions.

## Allowed Files

- src/ipo_risk/retrieval/keyword.py
- src/ipo_risk/retrieval/query_families.py
- tests/contract/test_keyword_retriever.py
- tests/contract/test_v03_retriever_query_families.py
- tests/fixtures/v03_retriever/
- docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md

## Forbidden Files

- docs/execution/plans/V3-3_RETRIEVER_PLAN.md
- src/ipo_risk/retrieval/base.py
- src/ipo_risk/schemas/
- src/ipo_risk/core/container.py
- src/ipo_risk/domain/risk_codes.py
- src/ipo_risk/agents/
- src/ipo_risk/providers/
- src/ipo_risk/workflows/
- src/ipo_risk/services/
- configs/
- data/
- tests/fixtures/v03_golden_cases/
- .github/workflows/

## Tasks

- [ ] Inspect the current KeywordDocumentRetriever and preserve all existing cash, ending-cash and operating-cash-flow behavior.
- [ ] Introduce a maintainable deterministic query-family definition for the eight v0.3 retrieval families: revenue, continuous_loss, customer_concentration, supplier_concentration, redemption_rights, material_litigation_compliance, commercialization_status, core_product_pipeline.
- [ ] Provide meaningful Simplified Chinese, Traditional Chinese and English aliases for every new query family.
- [ ] Add domain-aware positive and negative context / section weighting so that relevant Financial, Legal and Business sections rank above boilerplate, generic regulation text, summaries or unrelated keyword occurrences.
- [ ] Keep ranking deterministic. Do not add embeddings, external search, LLM calls, vector databases or nondeterministic model scoring.
- [ ] Preserve stable Evidence IDs for identical document/query inputs.
- [ ] Preserve the current no-fallback rule: no real match must return an empty list rather than unrelated Evidence.
- [ ] Preserve Evidence traceability: returned Evidence text must originate from the source DocumentChunk and retain document_id, chunk_id and physical page.
- [ ] Add dedicated v0.3 Retriever contract tests covering all new query families without changing the public Retriever protocol.
- [ ] Add decoy-section tests demonstrating that contextual ranking prefers relevant sections over misleading keyword occurrences.
- [ ] Run the complete repository regression suite and create the required Execution Report.

## Acceptance Criteria

- DocumentRetriever.retrieve() signature and return type remain unchanged.
- No public Schema, registry, container, workflow, provider, Agent or Service interface is changed.
- Existing cash, ending-cash and operating-cash-flow Retriever contract tests continue to pass unchanged in behavior.
- All eight new query families support deterministic matching using Simplified Chinese, Traditional Chinese and English terminology.
- Every new query family has tests showing that relevant domain context ranks ahead of at least one plausible boilerplate or wrong-section decoy.
- Identical input produces stable ranking and stable Evidence IDs.
- limit <= 0, blank queries and no-match queries continue to return an empty list.
- Evidence remains traceable to its original DocumentChunk and physical page.
- No company name, stock code, case ID or physical prospectus page number is hard-coded into retrieval rules.
- No LLM, embedding model, vector database, network dependency or new third-party package is introduced.
- No 2025 blind-test case is used for query-family design or tuning.
- Existing Mock and v0.2 Retriever behavior remains compatible.
- Complete repository tests and validation commands pass.

## Required Validation

```text
pytest -q tests/contract/test_keyword_retriever.py
pytest -q tests/contract/test_v03_retriever_query_families.py
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/V3-3_RETRIEVER_PLAN.md
git diff --check
```

## Manual Validation

If the local 2410.HK real PDF fixture is available, run:

```text
python scripts/check_real_v02_e2e.py
```

Confirm that the existing cash-runway regression remains:

- cash runway: 2.76 months
- verification: verified
- prediction: 90 / critical

If the fixture is unavailable, record this check as NOT_TESTED rather than fabricating a result.

Manually inspect representative synthetic retrieval results for at least:

- one Financial query family
- one Legal query family
- one Business query family

Confirm that the highest-ranked Evidence belongs to the intended document context.

Do not inspect or tune against 2025 blind-test cases.

## Stop Conditions

- A change to src/ipo_risk/retrieval/base.py is required.
- A public Schema, ComponentRegistry, Workflow, Service, Provider or Agent interface must change.
- A new runtime dependency is required.
- The implementation requires embeddings, an LLM, vector search or external network access.
- A company name, stock code, case ID or prospectus page number would need to be hard-coded.
- Existing cash or operating-cash-flow regression can only be restored by changing files outside Allowed Files.
- Passing validation requires deleting tests, adding skips/xfails, weakening assertions or modifying expected results to hide a regression.
- Implementation requires modifying the v0.3 golden manifest or using 2025 blind-test cases for tuning.
- The current worktree contains unrelated uncommitted changes.
- The required fix materially expands beyond Retriever query-family generalization.

If any stop condition is reached, stop with PLAN_CHANGE_REQUIRED or BLOCKED as appropriate. Do not silently broaden this Plan.

## Expected Deliverables

- Generalized deterministic v0.3 query-family Retriever implementation.
- Simplified Chinese, Traditional Chinese and English aliases for the eight required query families.
- Domain-aware deterministic context ranking for Financial, Legal and Business retrieval.
- Regression coverage preserving the existing v0.2 Retriever behavior.
- Dedicated v0.3 query-family contract tests.
- docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md
- No business Agent implementation, LLMProvider implementation, Verifier implementation or workflow expansion.

## Notes

V3-1 real reviewed golden cases are not yet complete on main. Real multi-case Retriever metrics are therefore not a completion gate for this execution Plan and must be evaluated after reviewed golden cases are merged.

This Plan does not authorize commit, push, Pull Request creation, merge, tag or release.
