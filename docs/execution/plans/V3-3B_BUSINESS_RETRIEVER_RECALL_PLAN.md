---
plan_id: V3-3B
title: Remediate Business Retriever recall for commercialization and core-product evidence
status: APPROVED
revision: 1
base_commit: da317612768828a27e37da679e2205625164a1f4
branch: fix/v03-business-retriever-recall
owner: tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md
---

# V3-3B Business Retriever Recall Remediation

## Goal

Improve the existing deterministic KeywordDocumentRetriever so that the
`commercialization_status` and `core_product_pipeline` query families retrieve
small, meaningful, traceable Top 5 Evidence sets for both pre-commercial and
commercial Business facts in real 2020-2023 prospectuses, without case-specific
rules and without changing any public interface.

## Background

V3-7 Business Agent execution correctly stopped with `PLAN_CHANGE_REQUIRED`.
Manual validation showed that the existing Business query families do not
generalize to all real prospectus wording:

- 1167.HK: `commercialization_status` returned no Evidence, while
  `core_product_pipeline` Top 5 missed the manually verified principal pages.
- 9633.HK: both Business query families returned no Evidence even though the
  prospectus contains commercial product and product-sales facts.

The current V3-7 partial implementation is preserved in its separate dirty
worktree. This Plan must be executed in a clean, independent worktree and must
not edit, reset, clean, delete, commit, push, or overwrite that partial work.

This remediation is a Retriever task. It must generalize factual Business
language rather than special-case company codes, company names, document IDs,
known page numbers, or known gold Evidence IDs. It must also preserve all
existing Retriever behavior, including the v0.2 cash and operating-cash-flow
regression.

## Project Rules

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/execution/README.md

## Inputs

- src/ipo_risk/retrieval/base.py
- src/ipo_risk/retrieval/query_families.py
- src/ipo_risk/retrieval/keyword.py
- tests/contract/test_keyword_retriever.py
- tests/contract/test_v03_retriever_query_families.py
- tests/fixtures/v03_retriever/
- scripts/check_real_keyword_retriever.py
- scripts/check_real_v02_e2e.py
- docs/execution/plans/V3-3_RETRIEVER_PLAN.md
- docs/execution/plans/V3-7_BUSINESS_AGENT_PLAN.md
- 2020-2023 development-set prospectuses for 1167.HK and 9633.HK, supplied only through local paths or environment variables

## Allowed Files

- src/ipo_risk/retrieval/query_families.py
- src/ipo_risk/retrieval/keyword.py
- tests/contract/test_keyword_retriever.py
- tests/contract/test_v03_retriever_query_families.py
- tests/fixtures/v03_retriever/
- scripts/check_v03_business_retriever_recall.py
- docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md

## Forbidden Files

- docs/execution/plans/V3-3B_BUSINESS_RETRIEVER_RECALL_PLAN.md
- src/ipo_risk/agents/
- src/ipo_risk/providers/
- src/ipo_risk/schemas/
- src/ipo_risk/core/
- src/ipo_risk/domain/
- src/ipo_risk/parsers/
- src/ipo_risk/predictors/
- src/ipo_risk/workflows/
- src/ipo_risk/services/
- src/ipo_risk/repositories/
- src/ipo_risk/reporting/
- configs/
- prompts/
- app/
- pyproject.toml
- tests/fixtures/v03_golden_cases/
- docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md

## Tasks

- [ ] Reproduce and document the current Business Retriever failures for 1167.HK and 9633.HK using only 2020-2023 development-set PDFs and physical PDF page numbers.
- [ ] Inspect the manually validated pages and extract only generic Simplified Chinese, Traditional Chinese, and English factual language patterns that can generalize across issuers.
- [ ] Expand `commercialization_status` from a pre-commercial risk-keyword query into a factual status query that retrieves both non-commercial and commercial evidence.
- [ ] Cover factual wording such as no products approved for commercial sale, no product-sales revenue, products not yet launched, products manufactured and sold, commercial product sales, commercial launch, and marketing approval with or without commenced sales.
- [ ] Expand `core_product_pipeline` to retrieve principal/core product identity, pipeline, development, approval, launch, manufacture, and sale facts without relying on issuer-specific names.
- [ ] Adjust deterministic context and ranking features only as needed to place primary Business facts in a meaningful Top 5 while retaining stable Evidence identity and full traceability.
- [ ] Keep query-family scoring deterministic and network-free; do not add embeddings, vector databases, LLM calls, or third-party dependencies.
- [ ] Add multilingual synthetic contract fixtures for pre-commercial facts, mature commercial facts, approval-before-sales facts, principal products, and realistic decoys.
- [ ] Add regressions proving that both positive and negative commercialization facts are retrievable and that generic risk-factor or unrelated language does not outrank primary factual evidence.
- [ ] Preserve the eight existing v0.3 query families, existing Retriever contracts, stable Evidence IDs, requested limits, and v0.2 cash/operating-cash-flow retrieval behavior.
- [ ] Add a safe local smoke script that accepts the two real PDF paths through command-line arguments or environment variables and reports only stock code, query family, ranked physical pages, Evidence IDs, and hit status.
- [ ] Generate the V3-3B Execution Report with exact scope, test results, manual validation pages, known limitations, and the required next action.

## Acceptance Criteria

### Public contract and scope

- `DocumentRetriever` and `KeywordDocumentRetriever.retrieve(...)` public signatures remain unchanged.
- `DocumentChunk`, `Evidence`, public Schema, Parser, Agent, Provider, Container, Workflow, Service, risk registry, and golden manifest remain unchanged.
- No new dependency, network call, embedding model, vector database, or LLM call is introduced.
- Only Allowed Files are changed, and the Approved Plan itself remains unchanged.

### Generic retrieval behavior

- `commercialization_status` retrieves both pre-commercial facts and mature commercial/product-sales facts; it is not limited to text containing explicit risk wording.
- `core_product_pipeline` retrieves principal/core product identity and pipeline/development/approval/launch/manufacture/sale facts.
- Simplified Chinese, Traditional Chinese, and English variants are covered by deterministic tests.
- At minimum, these semantic classes are covered by tests:
  - no products approved for commercial sale and no product-sales revenue;
  - products manufactured and sold with revenue generated from product sales;
  - marketing approval received but commercial sales not commenced;
  - principal/core product and product-pipeline descriptions.
- No implementation condition references 1167, 9633, an issuer name, a known document ID, page 13, page 17, page 107, or any other gold page/Evidence ID.
- Existing requested `limit` semantics remain intact; the implementation must not claim success by expanding retrieval to an arbitrary large result set.

### Real 2020-2023 validation

- For 1167.HK, `commercialization_status` changes from an empty result to valid traceable Evidence, with the manually verified commercialization/product-revenue page included in Top 5.
- For 1167.HK, `core_product_pipeline` Top 5 includes the manually verified principal/core-product page.
- For 9633.HK, `commercialization_status` Top 5 includes the manually verified mature commercial product/product-sales page.
- For 9633.HK, `core_product_pipeline` returns valid traceable product Evidence when a manually verified principal-product page is available.
- The report records exact physical pages used for acceptance. Known development-set pages may appear in tests or the smoke script's expected manual-validation data, but never in production ranking logic.
- No 2025 blind-set prospectus is opened, parsed, queried, annotated, or used for tuning.

### Regression and evidence quality

- All existing Retriever and query-family tests pass without weakened assertions, skip, xfail, or deleted coverage.
- Revenue, continuous loss, customer concentration, supplier concentration, redemption/special rights, material litigation/compliance, commercialization status, and core product/pipeline query families continue to work.
- The 2410.HK v0.2 regression remains stable: cash Evidence page 563 and operating-cash-flow Evidence page 562 remain retrievable under the existing real-case check.
- Evidence IDs remain stable for identical document/chunk/query inputs.
- Returned Evidence retains `document_id`, `chunk_id`, physical `page`, and source text traceability.
- Top 5 remains a small meaningful Evidence set; generic summaries, definitions, risk-factor boilerplate, and unrelated pages must not systematically outrank primary factual Business pages.

### Safe smoke behavior

- The smoke script has no hard-coded user absolute path and accepts local PDFs through environment variables or command-line arguments.
- Suggested environment variables are `IPO_RISK_V33B_1167_PDF` and `IPO_RISK_V33B_9633_PDF`.
- The script does not print full source text, credentials, Authorization headers, local absolute paths, or raw external responses.
- Missing local PDFs produce an explicit safe `NOT_TESTED`/configuration outcome rather than a false PASS.

## Required Validation

```text
pytest -q tests/contract/test_keyword_retriever.py
pytest -q tests/contract/test_v03_retriever_query_families.py
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/V3-3B_BUSINESS_RETRIEVER_RECALL_PLAN.md
git diff --check
```

When the local v0.2 real fixture is available, also run:

```text
python scripts/check_real_keyword_retriever.py
python scripts/check_real_v02_e2e.py
```

Tests must not require network access or large real prospectuses in CI. Passing
validation by deleting tests, weakening assertions, changing correct expected
results to match a defect, adding skip/xfail, or increasing retrieval limits is
forbidden.

## Manual Validation

### A. 1167.HK development-set case

- Parse the locally supplied 2020-2023 prospectus with the existing PyMuPDF Parser.
- Run `commercialization_status` with `limit=5` and verify that Top 5 includes the manually validated no-commercial-sale/no-product-sales Evidence page.
- Run `core_product_pipeline` with `limit=5` and verify that Top 5 includes the manually validated principal/core-product Evidence page.
- Record physical pages, Evidence IDs, rankings, and PASS/FAIL in the Execution Report.

### B. 9633.HK development-set case

- Parse the locally supplied 2020-2023 prospectus with the existing PyMuPDF Parser.
- Run `commercialization_status` with `limit=5` and verify that Top 5 includes the manually validated manufactured/sold product or product-sales Evidence page.
- Run `core_product_pipeline` with `limit=5` and verify a principal-product Evidence page when one has been manually established.
- Record physical pages, Evidence IDs, rankings, and PASS/FAIL in the Execution Report.

### C. Existing v0.2 regression

- If the 2410.HK local fixture is available, confirm the existing physical pages 563 and 562 and run the full cash-runway E2E regression.
- Expected full regression remains 706 parsed non-empty pages, zero parser errors, 2.76 months cash runway, verified status, and 90/critical prediction.
- If a local fixture is unavailable, record `NOT_TESTED`; do not claim PASS.

### D. Blind-set protection

- Confirm in the Execution Report that no 2025 blind-set PDF or derived gold label was accessed or used.

## Stop Conditions

- A public Retriever interface, Schema, Parser, Agent, Provider, Container, Workflow, Service, risk registry, frozen configuration, or golden manifest must change.
- Completing the real cases requires issuer-specific, stock-code-specific, document-ID-specific, product-name-specific, page-specific, or Evidence-ID-specific production logic.
- Meeting Top 5 acceptance requires increasing the requested limit beyond 5 or returning an unfiltered large candidate pool.
- Passing tests requires deleting or weakening assertions, changing correct expected values to hide a defect, adding skip/xfail, or reducing existing coverage.
- A new third-party dependency, embedding model, vector database, LLM call, remote API, or network-required test is needed.
- Any Allowed Files expansion is required.
- The existing eight query families or v0.2 cash/operating-cash-flow behavior regress and cannot be corrected inside Allowed Files.
- A 2025 blind-set document or derived blind label would need to be read or used.
- A required real 2020-2023 PDF is unavailable and manual acceptance cannot be honestly completed.
- The current V3-7 partial worktree would need to be reset, cleaned, overwritten, committed, pushed, or otherwise altered.
- Any API key, token, password, Authorization header, user absolute path, original large PDF, archive, cache, binary, or generated result is about to enter the diff.
- The work expands into V3-7 Agent implementation, V3-8 Verifier, V3-9 Supervisor/enhanced_v2, shared integration, UI, or release work.

On a scope or contract violation, stop with `PLAN_CHANGE_REQUIRED`. On missing
data or an external prerequisite that prevents honest validation, stop with
`BLOCKED`. Do not silently broaden the Plan.

## Expected Deliverables

- Generalized `commercialization_status` factual Evidence retrieval.
- Generalized `core_product_pipeline` factual Evidence retrieval.
- Deterministic multilingual aliases/context/ranking changes limited to the existing Retriever implementation.
- Network-free synthetic Retriever contract fixtures and regressions.
- Preserved stable Evidence identity, traceability, Top 5 discipline, eight-query-family behavior, and v0.2 regression.
- Safe local 1167.HK/9633.HK Business Retriever smoke script.
- Real 2020-2023 manual-validation results for 1167.HK and 9633.HK.
- `docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md`.

This Plan explicitly does **not** authorize:

- modifying this Approved Plan;
- continuing or committing the preserved V3-7 partial implementation;
- changing Business Agent code or tests;
- changing the golden manifest;
- changing public interfaces or shared architecture;
- using the 2025 blind set;
- commit, push, Pull Request creation, merge, tag, or release during Plan execution.

## Notes

- V3-7 remains `PLAN_CHANGE_REQUIRED` until V3-3B is independently executed, reviewed, merged, and synchronized back into the preserved Business worktree.
- This Plan repairs a shared Retriever boundary and is therefore owned by the technical lead, not folded into the member-5 Business Agent scope.
- Known development-set physical pages are acceptance or regression data only. They must never appear in production matching or ranking logic.
- After V3-3B merges, resume V3-7 without discarding its existing partial code; rebase or merge only after a deliberate review of that dirty worktree.
- The executor must return `READY_FOR_REVIEW`, `PLAN_CHANGE_REQUIRED`, or `BLOCKED` and must not commit, push, open a Pull Request, merge, tag, or release automatically.
