---
plan_id: V3-3
plan_revision: 1
execution_status: COMPLETED
base_commit: 6847f67df0e275576e6689c62a50b0269d4cfd84
start_head: 6a64f53de0864626ad4a9462c59e39aeb154a0e0
end_head: 6a64f53de0864626ad4a9462c59e39aeb154a0e0
branch: feat/v03-retriever-query-families
executor: codex
---

# Summary

Generalized `KeywordDocumentRetriever` with eight deterministic v0.3 query
families spanning Financial, Legal, and Business retrieval. Query-family
definitions centralize Simplified Chinese, Traditional Chinese, and English
aliases with positive, negative, preferred-section, and discouraged-section
signals. Existing cash and operating-cash-flow scoring remains on its original
path. No public interface, dependency, configuration, Agent, Workflow, Service,
Provider, Schema, or golden-case data was changed.

# Plan Compliance

COMPLIANT

All implementation and test changes are inside `Allowed Files`. No forbidden
path was changed, no 2025 blind-test case was inspected, and no dependency,
network service, LLM, embedding model, or vector database was introduced.

# Files Created

- `src/ipo_risk/retrieval/query_families.py`
- `tests/contract/test_v03_retriever_query_families.py`
- `docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md`

# Files Modified

- `src/ipo_risk/retrieval/keyword.py`

# Files Deleted

None.

# Tasks Completed

- [x] Inspect the current KeywordDocumentRetriever and preserve all existing cash, ending-cash and operating-cash-flow behavior.
- [x] Introduce a maintainable deterministic query-family definition for the eight v0.3 retrieval families: revenue, continuous_loss, customer_concentration, supplier_concentration, redemption_rights, material_litigation_compliance, commercialization_status, core_product_pipeline.
- [x] Provide meaningful Simplified Chinese, Traditional Chinese and English aliases for every new query family.
- [x] Add domain-aware positive and negative context / section weighting so that relevant Financial, Legal and Business sections rank above boilerplate, generic regulation text, summaries or unrelated keyword occurrences.
- [x] Keep ranking deterministic. Do not add embeddings, external search, LLM calls, vector databases or nondeterministic model scoring.
- [x] Preserve stable Evidence IDs for identical document/query inputs.
- [x] Preserve the current no-fallback rule: no real match must return an empty list rather than unrelated Evidence.
- [x] Preserve Evidence traceability: returned Evidence text must originate from the source DocumentChunk and retain document_id, chunk_id and physical page.
- [x] Add dedicated v0.3 Retriever contract tests covering all new query families without changing the public Retriever protocol.
- [x] Add decoy-section tests demonstrating that contextual ranking prefers relevant sections over misleading keyword occurrences.
- [x] Run the complete repository regression suite and create the required Execution Report.

# Validation Results

## 1

- Command: `pytest -q tests/contract/test_keyword_retriever.py`
- Result: PASS
- Details: 28 passed in 0.35s; existing v0.2 cash, ending-cash, operating-cash-flow, traceability, stable-ID, configuration, and Mock regressions passed.

## 2

- Command: `pytest -q tests/contract/test_v03_retriever_query_families.py`
- Result: PASS
- Details: 35 passed in 0.35s; covered eight families in three languages, eight decoy rankings, stable IDs, traceability, no fallback, catalog membership, and method signature.

## 3

- Command: `pytest -q`
- Result: PASS
- Details: 386 passed in 11.74s.

## 4

- Command: `python scripts/validate_project.py`
- Result: PASS
- Details: `status=completed verified=3 pending=1`.

## 5

- Command: `python scripts/validate_competition_data.py`
- Result: PASS
- Details: `competition_data_validation=passed`.

## 6

- Command: `python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity`
- Result: PASS
- Details: `valid v0.3 golden manifest` for the committed synthetic manifest.

## 7

- Command: `python -m compileall -q app src scripts`
- Result: PASS
- Details: exited 0 with no compilation errors.

## 8

- Command: `python scripts/check_execution_scope.py docs/execution/plans/V3-3_RETRIEVER_PLAN.md`
- Result: PASS
- Details: `execution_scope=valid`.

## 9

- Command: `git diff --check`
- Result: PASS
- Details: exited 0; only the existing Windows LF-to-CRLF working-copy warning was emitted.

# Acceptance Criteria

- PASS — DocumentRetriever.retrieve() signature and return type remain unchanged.
- PASS — No public Schema, registry, container, workflow, provider, Agent or Service interface is changed.
- PASS — Existing cash, ending-cash and operating-cash-flow Retriever contract tests continue to pass unchanged in behavior.
- PASS — All eight new query families support deterministic matching using Simplified Chinese, Traditional Chinese and English terminology.
- PASS — Every new query family has tests showing that relevant domain context ranks ahead of at least one plausible boilerplate or wrong-section decoy.
- PASS — Identical input produces stable ranking and stable Evidence IDs.
- PASS — `limit <= 0`, blank queries and no-match queries continue to return an empty list.
- PASS — Evidence remains traceable to its original DocumentChunk and physical page.
- PASS — No company name, stock code, case ID or physical prospectus page number is hard-coded into retrieval rules.
- PASS — No LLM, embedding model, vector database, network dependency or new third-party package is introduced.
- PASS — No 2025 blind-test case is used for query-family design or tuning.
- PASS — Existing Mock and v0.2 Retriever behavior remains compatible.
- PASS — Complete repository tests and validation commands pass.

# Manual Validation

- PASS — Local 2410.HK fixture was available. `python scripts/check_real_v02_e2e.py` completed with 706 parsed chunks, 0 parser errors, Evidence pages 563 and 562, cash runway 2.76 months, `verified`, and prediction `90.0/critical`.
- PASS — Financial `revenue`: relevant financial page 20 ranked above industry-overview decoy page 3, scores 0.78 and 0.34.
- PASS — Legal `redemption_rights`: relevant history/reorganisation page 20 ranked above statutory decoy page 3, scores 0.78 and 0.22.
- PASS — Business `core_product_pipeline`: relevant business page 20 ranked above definitions decoy page 3, scores 0.88 and 0.32.
- A first PowerShell-piped synthetic inspection attempt corrupted Chinese stdin and ended with `IndexError` after the real E2E had already passed. It did not change files. The inspection was rerun successfully by importing the UTF-8 contract fixture data directly.
- No 2025 blind-test document or result was inspected.

# Deviations

None.

# Known Limitations

- The committed v0.3 golden manifest still contains synthetic fixtures only, so real multi-case retrieval metrics are not a completion gate for this Plan.
- Ranking remains deterministic lexical/contextual scoring; it does not attempt semantic retrieval for wording absent from the maintained aliases.
- Query-family context is evaluated on each matching `DocumentChunk`; existing formal-statement page-neighborhood inheritance remains specific to the established cash-flow behavior.

# Suggested Follow-ups

- After reviewed V3-1 cases are merged, run real multi-case Recall@1/3/5 evaluation without tuning on the 2025 blind-test cohort.
- Consider generic document-section neighborhood propagation in a separately approved Plan if real reviewed cases demonstrate cross-page title loss outside cash-flow statements.

# Plan Change Requests

None.

# Git Diff Summary

```text
src/ipo_risk/retrieval/keyword.py | 88 ++++++++++++++++++++++++++++++---------
1 file changed, 69 insertions(+), 19 deletions(-)
```

The three newly created untracked files are listed under `Files Created`; Git
does not include untracked files in plain `git diff --stat` output.

# Final Git Status

```text
 M src/ipo_risk/retrieval/keyword.py
?? docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md
?? src/ipo_risk/retrieval/query_families.py
?? tests/contract/test_v03_retriever_query_families.py
```

# Next Action

READY_FOR_REVIEW
