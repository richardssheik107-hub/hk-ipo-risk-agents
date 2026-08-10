---
plan_id: GATE-A-09
title: Close v0.3 Legal Retriever Alias and Lifecycle/Status Gaps
status: APPROVED
revision: 1
base_commit: 6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc
branch: fix/v03-legal-retriever-gap
owner: lead-1-tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/GATE-A-09_LEGAL_RETRIEVER_GAP_EXECUTION_REPORT.md
---

# Close v0.3 Legal Retriever Alias and Lifecycle/Status Gaps

## Goal

Close GATE-A-09 by expanding the existing deterministic Legal `QueryFamily`
vocabulary and contextual ranking signals so that `redemption_rights` and
`material_litigation_compliance` retrieve small, traceable and meaningful
Evidence sets for positive, negative and lifecycle/status Legal facts in real
2020—2023 development prospectuses.

This is a Retriever vocabulary/context remediation. It is not a Legal Agent
rewrite, Legal Verifier task, Prompt runtime integration, shared Container
integration, or V3-8 work.

## Background

At `main@6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc`, GATE-A-07 and
GATE-A-08 are merged and complete. Gate A remains blocked by Golden review,
Legal Retriever closure and Legal Prompt runtime integration.

The existing query-family catalog already provides deterministic aliases,
positive/negative context, section weights, stable Evidence identity and the
public `KeywordDocumentRetriever.retrieve(...)` contract. The Legal vocabulary
is narrower than the domain requirements recorded in
`V03_LEGAL_RETRIEVAL_GAP_REPORT.md`. This Plan extends only the existing Legal
query-family data and its tests. It does not authorize changes to ranking
implementation or public contracts.

Legal A—H are 2020—2023 development `preselection / draft` cases. They may be
used for development acceptance but must not be described as reviewed Golden
Recall metrics.

## Project Rules

- `AGENTS.md`
- `docs/PROJECT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_SCHEMA.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `docs/execution/README.md`

## Inputs

- `docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md`
- `docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md`
- `src/ipo_risk/retrieval/query_families.py`
- `src/ipo_risk/retrieval/keyword.py`
- `tests/contract/test_v03_retriever_query_families.py`
- `tests/contract/test_keyword_retriever.py`
- `tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv`
- `docs/execution/plans/V3-3_RETRIEVER_PLAN.md`
- `docs/execution/plans/V3-3B_BUSINESS_RETRIEVER_RECALL_PLAN.md`
- Existing local 2020—2023 development prospectuses for Legal A—H.
- Existing local v0.2 real-case fixture when available.

The Executor must read all Project Rules and Inputs before editing. Inputs are
read-only unless also listed under Allowed Files.

## Allowed Files

- `src/ipo_risk/retrieval/query_families.py`
- `tests/contract/test_v03_retriever_query_families.py`
- `tests/fixtures/v03_retriever/legal_recall_cases.json`
- `scripts/check_v03_legal_retriever_recall.py`
- `docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `docs/execution/reports/GATE-A-09_LEGAL_RETRIEVER_GAP_EXECUTION_REPORT.md`

## Forbidden Files

- `docs/execution/plans/GATE-A-09_LEGAL_RETRIEVER_GAP_PLAN.md`
- `src/ipo_risk/retrieval/keyword.py`
- `src/ipo_risk/retrieval/base.py`
- `src/ipo_risk/agents/`
- `src/ipo_risk/domain/`
- `src/ipo_risk/providers/`
- `src/ipo_risk/schemas/`
- `src/ipo_risk/core/`
- `src/ipo_risk/workflows/`
- `src/ipo_risk/services/`
- `src/ipo_risk/parsers/`
- `src/ipo_risk/predictors/`
- `configs/`
- `prompts/`
- `app/`
- `tests/fixtures/v03_golden_cases/`
- `pyproject.toml`

No Golden CSV, public interface, Schema, dependency, Agent, Verifier, Provider,
Prompt, Container, Workflow, Service, Parser or Predictor change is authorized.
If aliases/context alone are insufficient and a forbidden implementation file
must change, stop with `PLAN_CHANGE_REQUIRED`; do not broaden this Plan.

## Tasks

### 1. Record the current Legal Retriever baseline

- [ ] Read both existing Legal `QueryFamily` definitions and current ranking
  metadata without modifying `keyword.py`.
- [ ] Record the exact eight-family catalog and current public `retrieve()`
  signature.
- [ ] Run the existing Legal query-family contracts before changes.
- [ ] Record baseline A—H Top-5 pages when all required development PDFs are
  available; otherwise stop with `BLOCKED` before claiming Gate closure.

### 2. Expand `redemption_rights` aliases

- [ ] Add issuer-independent Simplified Chinese, Traditional Chinese and
  English aliases for liquidation preference.
- [ ] Add aliases for anti-dilution rights.
- [ ] Add aliases for pre-emptive/pre-emption rights.
- [ ] Add aliases for repurchase/buyback rights.
- [ ] Add aliases for veto rights.
- [ ] Add aliases for director nomination rights.
- [ ] Add aliases for valuation adjustment mechanism/VAM/对赌安排/對賭安排.
- [ ] Do not add issuer names, stock codes, document IDs, known pages,
  Evidence IDs, investor names or other case-specific production rules.

### 3. Expand rights lifecycle context

- [ ] Add terminate/terminated/termination, cease, lapse, expire and
  简繁“终止/終止/失效” as positive lifecycle context.
- [ ] Add waive/waived/waiver and 豁免 as positive lifecycle context.
- [ ] Add restore/restored/restorable, revive, reinstate, resume and
  恢复/恢復/重新生效.
- [ ] Add listing-application failure/restoration trigger context, including
  withdrawn/rejected applications and an IPO not completed.
- [ ] Keep terminated, waived and restored text retrievable as decision
  Evidence rather than exclusion-filtering it.

### 4. Expand `material_litigation_compliance` aliases and status context

- [ ] Add litigation/诉讼/訴訟 and arbitration/仲裁.
- [ ] Add regulatory investigation/监管调查/監管調查.
- [ ] Add licence/license/permit and 牌照/许可/許可.
- [ ] Add tax/税务/稅務.
- [ ] Add environmental penalty/环境处罚/環境處罰.
- [ ] Add data privacy/数据隐私/數據隱私.
- [ ] Add pending/ongoing/unresolved and corresponding Simplified/Traditional
  current-status context.
- [ ] Add resolved/settled/closed and 已结案/已結案/已和解.
- [ ] Add remediated/rectified and 已整改/整改完成.
- [ ] Add renewed/not renewed, suspended operations, licence/permit suspension
  and corresponding Simplified/Traditional licence-impact context.

### 5. Preserve negative/status Evidence and control boilerplate

- [ ] Ensure terminated rights, waived rights, settled/closed litigation,
  remediated regulatory matters, renewed licences and explicit
  no-material-litigation statements remain retrievable.
- [ ] Use `negative_context` and `discouraged_sections` only as ranking signals;
  do not turn them into exclusion filters.
- [ ] Add only generic, issuer-independent decoy signals for ordinary-course
  future disputes, general regulatory exposure, general shareholder rights,
  ordinary share buyback, statutory redemption and generic templates.
- [ ] Prove direct issuer-specific facts outrank generic boilerplate when both
  are present.

### 6. Add multilingual synthetic Legal Retriever fixtures

- [ ] Create `tests/fixtures/v03_retriever/legal_recall_cases.json`.
- [ ] Cover at least: active special right; terminated special right; waived
  right; conditional restoration; listing-application failure restoration;
  actual pending litigation; resolved litigation; explicit no-material-
  litigation; remediated regulatory matter; licence suspended/not renewed;
  licence renewed/impact removed; generic future-litigation decoy.
- [ ] Include Simplified Chinese, Traditional Chinese and English, plus case,
  line-break, PDF-whitespace and hyphen variants.
- [ ] Keep fixtures synthetic and free of issuer/page/document-specific
  production logic.

### 7. Strengthen query-family contract tests

- [ ] Prove direct factual Evidence is retrievable.
- [ ] Prove lifecycle/status terms contribute ranking context.
- [ ] Prove negative Evidence remains retrievable.
- [ ] Prove primary facts outrank boilerplate decoys.
- [ ] Prove stable Evidence IDs and document/chunk/page/source traceability.
- [ ] Prove `limit=5` is respected and existing limit semantics remain unchanged.
- [ ] Prove the exact existing eight query-family names and public Retriever
  signature remain unchanged.
- [ ] Reuse existing normalization; do not add normalization code in this Plan.
- [ ] Do not weaken, skip or xfail any existing test.

### 8. Add a safe real-development validation script

- [ ] Create `scripts/check_v03_legal_retriever_recall.py`.
- [ ] Accept repeated CLI PDF inputs or environment configuration without
  embedding a user absolute path.
- [ ] Perform no network access.
- [ ] Never print credentials, full local paths or full prospectus text.
- [ ] Output only case ID, stock code, query family, expected physical page,
  ranked physical pages, Evidence IDs, hit status and summary counts.
- [ ] Return `NOT_TESTED / BLOCKED`, never fake PASS, for missing PDFs.

### 9. Run A—H development acceptance with `limit=5`

- [ ] A: 9898.HK, `redemption_rights`, physical page 300.
- [ ] B: 9863.HK, `redemption_rights`, physical page 207.
- [ ] C: 2517.HK, `redemption_rights`, physical page 152.
- [ ] D: 1961.HK, `redemption_rights`, physical page 78.
- [ ] E: 6698.HK, `material_litigation_compliance`, physical page 26.
- [ ] F: 2451.HK, `material_litigation_compliance`, physical page 298.
- [ ] G: 9600.HK, `material_litigation_compliance`, physical page 222.
- [ ] H: 1942.HK, `material_litigation_compliance`, physical page 44.
- [ ] Parse each existing local development prospectus and record returned
  pages, Evidence IDs, expected-page rank and HIT/MISS.
- [ ] Require all eight selected development pages in Top-5 and report Top-1,
  Top-3 and Top-5 hit counts.
- [ ] Treat known stock codes/pages only as acceptance data; do not place them
  in production query/ranking logic.
- [ ] Do not call these formal Golden Recall metrics.

### 10. Run regression and scope validation

- [ ] Re-run all existing Retriever query-family contracts.
- [ ] Re-run the complete test suite and project validators.
- [ ] Run v0.2 real Retriever and E2E checks when their local fixture is
  available; record `NOT_RUN` honestly otherwise.
- [ ] Confirm no public interface, query-family name/count or Evidence identity
  regression.
- [ ] Confirm no 2025 blind-set file was opened, parsed, retrieved or tuned.
- [ ] Run Scope Guard after each material task and at the end.

### 11. Close GATE-A-09 only after all acceptance checks pass

- [ ] Mark `V03_LEGAL_RETRIEVAL_GAP_REPORT.md` as resolved only after all eight
  development pages pass Top-5 and all required validation passes.
- [ ] Change only GATE-A-09 to PASS in `V03_GATE_A_CLOSEOUT.md`.
- [ ] Update `snapshot_main` to the execution base where appropriate.
- [ ] Keep GATE-A-03/04/05/06/10 as FAIL.
- [ ] Keep `V3-8_START_STATUS = BLOCKED`.

### 12. Write the Execution Report

- [ ] Create the report at the frozen `report_path`.
- [ ] Record baseline and final Top-1/Top-3/Top-5 A—H counts, per-case pages,
  Evidence IDs and HIT/MISS without full paths or full source text.
- [ ] Record exact aliases/context added, normalization behavior, regression
  results, scope, blind guard, deviations, limitations and next action.
- [ ] Explicitly state that A—H are development draft acceptance cases rather
  than formal reviewed Golden metrics.

## Acceptance Criteria

### Vocabulary and ranking context

- Both Legal query families cover the approved Simplified Chinese,
  Traditional Chinese and English alias/status/lifecycle classes.
- Existing normalization handles case, line break, PDF whitespace and hyphen
  variants without modifying normalization code.
- Negative/status Evidence remains retrievable; no lifecycle or negative term
  becomes an exclusion filter.
- Direct factual Evidence outranks generic boilerplate in synthetic and real
  development contexts.

### Contract and traceability

- The query-family catalog remains exactly the existing eight names.
- `DocumentRetriever`, `KeywordDocumentRetriever.retrieve(...)`,
  `DocumentChunk` and `Evidence` remain unchanged.
- Evidence IDs are stable and document ID, chunk ID, physical page and source
  snippet remain traceable.
- Requested `limit` semantics remain unchanged; Gate success uses `limit=5`.

### Development acceptance

- All eight A—H expected physical pages appear within their query family's
  Top-5 result using existing local 2020—2023 development PDFs.
- Top-1, Top-3 and Top-5 counts and per-case ranks are recorded honestly.
- No pass is obtained by increasing `limit` beyond 5.
- Results are labeled development acceptance, not formal Golden Recall.
- Missing any required A—H PDF yields `BLOCKED`, not GATE-A-09 PASS.

### Safety and scope

- No issuer, stock code, document ID, known page, Evidence ID, investor name or
  other case-specific rule enters production query-family data.
- No 2025 blind-set prospectus or derived label is accessed.
- No forbidden file, Golden CSV, dependency or public interface changes.
- All existing Retriever, v0.2 and full-suite regressions remain stable.

### Gate status

- GATE-A-09 changes to PASS only after every mandatory check passes.
- GATE-A-03/04/05/06/10 remain FAIL.
- `V3-8_START_STATUS = BLOCKED` remains unchanged.

## Required Validation

Run exactly:

```text
pytest -q tests/contract/test_v03_retriever_query_families.py
pytest -q tests/contract/test_keyword_retriever.py
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/GATE-A-09_LEGAL_RETRIEVER_GAP_PLAN.md
git diff --check
git diff --name-only
```

If the local v0.2 real fixture is available, also run:

```text
python scripts/check_real_keyword_retriever.py
python scripts/check_real_v02_e2e.py
```

Do not claim PASS for an unexecuted command. Confirm all changed paths are
Plan-allowed, `git diff -- src/ipo_risk/retrieval/keyword.py` is empty,
`git diff -- tests/fixtures/v03_golden_cases` is empty, and no forbidden or
unsafe artifact enters the diff.

## Manual Validation

- Inspect all A—H Top-5 results using the safe validation output.
- Confirm expected physical pages and stable Evidence IDs for each case.
- Confirm direct facts outrank boilerplate without issuer/page-specific logic.
- Inspect production additions for issuer names, stock codes, document IDs,
  page numbers, Evidence IDs, credentials and local absolute paths.
- Confirm A—H are labeled development draft acceptance rather than formal
  Golden metrics.
- Confirm no 2025 blind-set file was accessed.

## Stop Conditions

Stop with `PLAN_CHANGE_REQUIRED` if:

- `src/ipo_risk/retrieval/keyword.py` or Retriever ranking implementation must
  change;
- a public Retriever interface, Schema, Parser, Agent, Verifier, Provider,
  Prompt runtime, shared integration or dependency must change;
- a ninth query family is required;
- issuer/page/document/Evidence-specific production logic is required;
- `limit > 5` is required to claim success;
- tests must be weakened or a skip/xfail added;
- a Golden CSV must change;
- existing normalization cannot support the approved generic variants;
- 2025 blind data would need to be accessed.

Stop with `BLOCKED` if any required A—H development PDF is unavailable or the
real A—H acceptance cannot be run honestly. In either stop state, do not mark
the Gap Report resolved or GATE-A-09 PASS.

Stop immediately if a secret, credential, local absolute path, cache, binary,
raw prospectus, generated result or unsafe artifact would enter the diff.

## Expected Deliverables

- Expanded issuer-independent Legal aliases and lifecycle/status context in
  the two existing Legal query families.
- A synthetic multilingual Legal recall fixture covering positive, negative,
  lifecycle, remediation and licence cases.
- Strengthened deterministic Retriever contract tests.
- A safe local A—H development recall script with Top-1/Top-3/Top-5 reporting.
- Honest A—H Top-5 development acceptance using all eight required PDFs.
- Stable query-family catalog, Retriever signature and Evidence traceability.
- Updated Gap Report and Gate A status only after every acceptance check passes.
- `GATE-A-09_LEGAL_RETRIEVER_GAP_EXECUTION_REPORT.md`.

## Notes

- Negative/status Evidence is decision Evidence and must remain retrievable.
- `negative_context` and `discouraged_sections` are ranking signals only.
- Known A—H identifiers and pages are acceptance data only and must never enter
  production ranking logic.
- This Plan does not authorize GATE-A-10, shared integration or V3-8.
- On successful reviewed execution, the next technical Gate is GATE-A-10, but
  it must use a separate future Approved Plan.
