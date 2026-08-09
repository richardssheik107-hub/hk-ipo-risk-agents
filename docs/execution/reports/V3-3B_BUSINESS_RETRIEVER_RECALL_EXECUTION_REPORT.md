---
plan_id: V3-3B
plan_revision: 1
execution_status: COMPLETED
base_commit: da317612768828a27e37da679e2205625164a1f4
start_head: dd44b203bd9318644a104dd368c444022fd79ce0
end_head: dd44b203bd9318644a104dd368c444022fd79ce0
branch: fix/v03-business-retriever-recall
executor: codex
---

# V3-3B Business Retriever Recall Execution Report

## Summary

Generalized the existing deterministic Business query-family vocabulary so
`commercialization_status` retrieves both pre-commercial and mature commercial
facts, while `core_product_pipeline` retrieves both clinical pipelines and
principal commercial products. Added multilingual network-free fixtures,
ranking/traceability regressions, and a safe two-case local smoke script.

Real 2020 development-set validation passed for 1167.HK and 9633.HK. The 1167
commercialization and core-product pages ranked first. The 9633 commercial
product page ranked first for commercialization and third for core-product
retrieval. The existing 2410.HK cash-runway regression also passed unchanged.

No Retriever public interface, Schema, Parser, Agent, Provider, Container,
Workflow, Service, configuration, dependency, or golden-manifest change was
made. `src/ipo_risk/retrieval/keyword.py` did not require modification.

## Plan Compliance

COMPLIANT

All changes are within the Approved Plan's Allowed Files. The Approved Plan and
the preserved V3-7 Business Agent worktree were not modified. Production logic
contains no issuer, stock-code, product-name, document-ID, page, or Evidence-ID
special case. No 2025 blind-set file or derived label was accessed.

## Files Created

- `tests/fixtures/v03_retriever/business_recall_cases.json`
- `scripts/check_v03_business_retriever_recall.py`
- `docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md`

## Files Modified

- `src/ipo_risk/retrieval/query_families.py`
- `tests/contract/test_v03_retriever_query_families.py`

## Files Deleted

None.

## Tasks Completed

- [x] Reproduced and documented the existing 1167.HK and 9633.HK failures with 2020 development-set PDFs and physical pages.
- [x] Inspected manually validated pages and extracted only generic Simplified Chinese, Traditional Chinese, and English factual patterns.
- [x] Expanded `commercialization_status` into a factual status query covering both pre-commercial and commercial evidence.
- [x] Covered no approval/no product revenue, manufacture-and-sell, product-sales revenue, commercial launch, and approval-before-sales wording.
- [x] Expanded `core_product_pipeline` to include principal products, product categories/portfolios, development state, approval, launch, manufacture, and sale facts.
- [x] Improved deterministic ranking through query-family aliases and contextual signals while preserving stable Evidence identity and traceability.
- [x] Kept retrieval deterministic and network-free with no new dependency, embedding, vector database, or LLM call.
- [x] Added multilingual synthetic fixtures for pre-commercial, mature commercial, approval-before-sales, principal-product, pipeline, and decoy cases.
- [x] Added regressions proving positive and negative commercialization facts are retrievable and generic industry language cannot outrank primary facts.
- [x] Preserved all eight v0.3 query families, existing Retriever contracts, requested limits, stable IDs, and v0.2 cash behavior.
- [x] Added a safe smoke script using command-line arguments or environment variables without printing paths or source text.
- [x] Generated this Execution Report with exact validation and manual results.

## Validation Results

### Approved Plan validation

- Command: `python scripts/validate_execution_plan.py docs/execution/plans/V3-3B_BUSINESS_RETRIEVER_RECALL_PLAN.md --approved`
- Result: PASS
- Details: `plan_validation=valid`.

### Keyword Retriever contracts

- Command: `pytest -q tests/contract/test_keyword_retriever.py`
- Result: PASS
- Details: `28 passed`.

### v0.3 query-family contracts

- Command: `pytest -q tests/contract/test_v03_retriever_query_families.py`
- Result: PASS
- Details: `52 passed`, including 12 new Business factual-recall/ranking/limit checks.

### Full test suite

- Command: `pytest -q`
- Result: PASS
- Details: `637 passed in 12.82s`.

### Project validation

- Command: `python scripts/validate_project.py`
- Result: PASS
- Details: `status=completed verified=3 pending=1`.

### Competition-data validation

- Command: `python scripts/validate_competition_data.py`
- Result: PASS
- Details: The first invocation in the system Python environment failed before validation because the existing optional `openpyxl` runtime package was unavailable. No dependency or repository file was changed. The command was rerun with the existing workspace-provided `openpyxl 3.1.5` package on `PYTHONPATH` and returned `competition_data_validation=passed`.

### Golden-manifest integrity

- Command: `python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity`
- Result: PASS
- Details: `valid v0.3 golden manifest`; the manifest was not modified.

### Byte compilation

- Command: `python -m compileall -q app src scripts`
- Result: PASS
- Details: Completed with no byte-compilation error; generated caches remained ignored.

### Scope Guard

- Command: `python scripts/check_execution_scope.py docs/execution/plans/V3-3B_BUSINESS_RETRIEVER_RECALL_PLAN.md`
- Result: PASS
- Details: `execution_scope=valid` after each material stage and at final validation.

### Diff whitespace check

- Command: `git diff --check`
- Result: PASS
- Details: No whitespace error. Git emitted only the repository's normal LF-to-CRLF working-copy warning.

### Real Keyword Retriever regression

- Command: `python scripts/check_real_keyword_retriever.py`
- Result: PASS
- Details: 2410.HK cash page 563 remained rank 1; operating-cash-flow page 562 remained rank 1; legal pages 665 and 683 were not matched.

### Real v0.2 E2E regression

- Command: `python scripts/check_real_v02_e2e.py`
- Result: PASS
- Details: 706 chunks, zero parser errors, Evidence pages 563/562, 2.76 months, verified, prediction 90/critical.

### V3-3B real smoke

- Command: `python scripts/check_v03_business_retriever_recall.py`
- Result: PASS
- Details: Both configured 2020 development cases passed all four Top 5 checks. With no configured paths the script safely returned `NOT_TESTED reason=pdf_not_configured` for each case and printed no path.

## Acceptance Criteria

### Public contract and scope

- PASS — `DocumentRetriever` and `KeywordDocumentRetriever.retrieve(...)` signatures are unchanged.
- PASS — `DocumentChunk`, `Evidence`, Schema, Parser, Agent, Provider, Container, Workflow, Service, risk registry, and golden manifest are unchanged.
- PASS — No dependency, network call, embedding model, vector database, or LLM call was added.
- PASS — Only Allowed Files changed; the Approved Plan is unchanged.

### Generic retrieval behavior

- PASS — `commercialization_status` retrieves pre-commercial and mature commercial/product-sales facts.
- PASS — `core_product_pipeline` retrieves core/principal product identity and pipeline/development/approval/launch/manufacture/sale facts.
- PASS — Simplified Chinese, Traditional Chinese, and English variants have deterministic fixture coverage.
- PASS — No-products-approved/no-product-revenue, commercial manufacture-and-sale, approval-before-sales, and principal/core product semantic classes are covered.
- PASS — Production logic contains no 1167, 9633, issuer name, document ID, product name, physical page, or gold Evidence ID.
- PASS — Requested `limit` behavior is unchanged; a dedicated test confirms exactly five stable results from seven valid candidates.

### Real 2020-2023 validation

- PASS — 1167.HK `commercialization_status`: page 17 ranked 1/5.
- PASS — 1167.HK `core_product_pipeline`: page 13 ranked 1/5.
- PASS — 9633.HK `commercialization_status`: page 107 ranked 1/5.
- PASS — 9633.HK `core_product_pipeline`: page 107 ranked 3/5.
- PASS — Physical pages, ranks, and Evidence IDs were recorded; expected pages exist only in the smoke acceptance layer, not production ranking logic.
- PASS — No 2025 blind-set prospectus or derived label was accessed.

### Regression and evidence quality

- PASS — Existing tests passed without deleted/weak assertions, skip, or xfail.
- PASS — All eight existing v0.3 query families remain present and covered.
- PASS — 2410.HK cash page 563 and operating-cash-flow page 562 remain rank 1.
- PASS — Evidence IDs remain stable for identical inputs.
- PASS — Evidence retains document ID, chunk ID, physical page, and source-text traceability.
- PASS — Primary Business facts outrank or exclude generic industry-overview decoys within Top 5.

### Safe smoke behavior

- PASS — Paths are accepted by arguments or `IPO_RISK_V33B_1167_PDF` / `IPO_RISK_V33B_9633_PDF`.
- PASS — No local path, full source text, credential, Authorization header, or raw response is printed.
- PASS — Missing paths return explicit `NOT_TESTED`, not a false PASS.

## Manual Validation

### 1167.HK

- PASS — Parser produced 519 non-empty chunks with zero page errors.
- PASS — `commercialization_status` Top 5 pages: `17, 297, 278, 279, 294`; page 17 ranked first.
- PASS — Page 17 Evidence ID: `3be414d8-209e-5e70-9f3d-fd731402e41b`.
- PASS — `core_product_pipeline` Top 5 pages: `13, 213, 224, 297, 57`; page 13 ranked first.
- PASS — Page 13 Evidence ID: `8f6e9b7b-51e2-529e-8e77-1196905cbb4e`.

### 9633.HK

- PASS — Parser produced 547 non-empty chunks with zero page errors.
- PASS — `commercialization_status` Top 5 pages: `107, 62, 63, 221, 328`; page 107 ranked first.
- PASS — Page 107 commercialization Evidence ID: `3a2aea19-cd9c-5622-8c88-ec9e024896a9`.
- PASS — `core_product_pipeline` Top 5 pages: `11, 154, 107, 9, 24`; page 107 ranked third.
- PASS — Page 107 core-product Evidence ID: `3c2a042b-28eb-5b18-878b-10ab542a1a09`.

### 2410.HK v0.2 regression

- PASS — 706 parsed chunks, zero parser errors, Evidence pages 563/562, cash runway 2.76 months, verified, prediction 90/critical.

### Blind-set protection

- PASS — Only the explicitly selected 2020 development archive entries and the existing 2410.HK v0.2 fixture were used. No 2025 archive was opened or inspected.

## Deviations

None. The temporary competition-data validator environment retry did not alter
the Plan scope, repository, dependencies, or validation logic.

## Known Limitations

- Retrieval remains deterministic phrase/context matching rather than semantic embedding retrieval.
- Real Business validation covers two 2020 development-set issuers; additional cross-industry shadow cases would improve confidence without changing this Plan's acceptance result.
- The 9633.HK core-product primary page is rank 3 rather than rank 1, but remains inside the frozen Top 5 acceptance threshold.
- Physical page expectations in the smoke script are development-set acceptance data and require deliberate maintenance if the source PDFs change.

## Suggested Follow-ups

- Perform an independent human review of the four recorded Business Evidence rankings.
- Review and merge V3-3B before resuming V3-7.
- After merge, deliberately synchronize the preserved V3-7 worktree and rerun its Business Agent acceptance without discarding its partial implementation.
- Consider a separate future shadow-test Plan for broader non-biotech Business terminology; do not add it to V3-3B.

## Plan Change Requests

None.

## Git Diff Summary

```text
src/ipo_risk/retrieval/query_families.py          | 28 ++++++--
tests/contract/test_v03_retriever_query_families.py | 94 ++++++++++++++++++++++
2 tracked files changed, 120 insertions(+), 2 deletions(-)

Untracked allowed deliverables:
docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md
scripts/check_v03_business_retriever_recall.py
tests/fixtures/v03_retriever/business_recall_cases.json
```

## Final Git Status

```text
 M src/ipo_risk/retrieval/query_families.py
 M tests/contract/test_v03_retriever_query_families.py
?? docs/execution/reports/V3-3B_BUSINESS_RETRIEVER_RECALL_EXECUTION_REPORT.md
?? scripts/check_v03_business_retriever_recall.py
?? tests/fixtures/v03_retriever/
```

## Next Action

READY_FOR_REVIEW
