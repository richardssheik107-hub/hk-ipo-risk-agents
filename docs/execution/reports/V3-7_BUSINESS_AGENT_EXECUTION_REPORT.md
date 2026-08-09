---
plan_id: V3-7
plan_revision: 1
execution_status: COMPLETED
base_commit: 47e3a0779054101d96250a881654a41d33f7bc32
start_head: da317612768828a27e37da679e2205625164a1f4
end_head: ffeef185fdd78f71f95a485c1882bce4b152eee8
branch: feat/v03-business-agent
executor: codex
---

# Summary

V3-7 is complete as a standalone Business Agent implementation for
`precommercial_product`. The resumed execution consumed the merged V3-3B
Business Retriever recall fix without modifying Retriever code. It implements
deterministic fact extraction, optional structured LLM candidate handling,
rule-based reconciliation, typed diagnostics, traceable Evidence, stable risk
identity, real development-case regressions, and a safe local smoke script.

The Agent is standalone-ready only. It is not registered in the shared
Container, Workflow, or Service, and it does not perform verification.

# Plan Compliance

COMPLIANT. All changes are within the Approved Plan's Allowed Files. The Plan,
frozen candidate models, public interfaces, Retriever, Provider, risk registry,
configuration, Container, Workflow, Service, Verifier, and UI remain unchanged.
No dependency was added and no 2025 blind case was accessed.

# Files Created

- `src/ipo_risk/agents/business_v03.py`
- `src/ipo_risk/agents/business_extraction.py`
- `src/ipo_risk/agents/business_policy.py`
- `tests/unit/test_business_extraction_v03.py`
- `tests/unit/test_business_agent_v03.py`
- `tests/contract/test_business_agent_v03_contract.py`
- `tests/regression/test_v03_business_golden_values.py`
- `scripts/check_v03_business_agent.py`
- `docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md`

# Files Modified

- `tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`
  - Added only three draft `precommercial_product` Business rows.

# Files Deleted

None.

# Tasks Completed

1. Added `V03BusinessAgent` with the frozen `RiskAgent.analyze()` contract,
   `name="business"`, list return type, and per-call diagnostic reset.
2. Used only the existing Retriever interface and merged V3-3B query families;
   each query family remains limited to five Evidence items.
3. Added deterministic Simplified Chinese, Traditional Chinese, and English
   commercialization, product-stage, approval, launch, and revenue extraction.
4. Distinguished direct product-sales revenue from licensing, milestone, R&D
   service, collaboration, and unattributed generic revenue.
5. Mapped extracted facts to the frozen `CommercializationCandidate` and
   `CoreProductCandidate` models with validated Evidence IDs.
6. Added optional structured LLM candidate consumption with deterministic and
   unavailable/no-key operation remaining network-free.
7. Added deterministic/LLM reconciliation, including out-of-scope Evidence ID
   rejection and material conflict handling.
8. Added the frozen `precommercial_product` rule producing only a medium/60,
   pending candidate with no Calculation.
9. Preserved prospectus Evidence identity and generated stable deterministic
   risk IDs.
10. Added typed diagnostics and isolated Retriever, extractor, and Provider
    failures without leaking raw exception payloads.
11. Added two real positive draft rows for 1167.HK and one real negative draft
    row for 9633.HK; second reviewer remains empty.
12. Added network-free extraction, Agent, contract, and real-text regression
    tests.
13. Added a safe local Business smoke script with environment/CLI PDF input and
    non-sensitive output.
14. Updated this execution report with final validation and manual results.

# Validation Results

- `pytest -q tests/unit/test_business_extraction_v03.py`: PASS, 20 passed.
- `pytest -q tests/unit/test_business_agent_v03.py`: PASS, 14 passed.
- `pytest -q tests/contract/test_business_agent_v03_contract.py`: PASS, 5 passed.
- `pytest -q tests/contract/test_v03_agent_contract.py`: PASS, 9 passed.
- `pytest -q tests/regression/test_v03_business_golden_values.py`: PASS, 3 passed.
- Combined focused compatibility run: PASS, 51 passed.
- `pytest -q`: PASS, 825 passed.
- `python scripts/validate_project.py`: PASS,
  `status=completed verified=3 pending=1`.
- `python scripts/validate_competition_data.py`: PASS. The existing bundled
  workspace `openpyxl` runtime was added to `PYTHONPATH`; no dependency was
  installed or changed.
- `python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv --integrity`:
  PASS.
- `python -m compileall -q app src scripts`: PASS.
- `python scripts/check_execution_scope.py docs/execution/plans/V3-7_BUSINESS_AGENT_PLAN.md`:
  PASS, `execution_scope=valid`.
- `git diff --check`: PASS.

# Acceptance Criteria

- Public contract and frozen models unchanged: PASS.
- Business ownership limited to `precommercial_product`: PASS.
- Evidence identity and traceability: PASS.
- Direct versus non-product revenue semantics: PASS.
- Approval, launch, and commercialization semantics: PASS.
- Positive, negative, ambiguous, conflict, and failure behavior: PASS.
- Pending-only risk behavior, deterministic medium/60 score, no Calculation,
  and stable risk ID: PASS.
- Mock, unavailable, and deterministic LLM paths remain network-free: PASS.
- Real positive and negative draft rows with no fabricated second review: PASS.
- Allowed-file scope and frozen-boundary restrictions: PASS.
- Full regression and v0.2 real-case regression: PASS.

# Manual Validation

## 1167.HK positive case

- Parsed chunks: 519; parser errors: 0.
- Agent result: one pending `precommercial_product` risk.
- Risk level/score: medium / 60; Calculation: none.
- Main Evidence pages 13 and 17 were retained; additional supporting Evidence
  remained traceable to physical pages.
- Deterministic facts identify the core product, an approved but not launched
  state, no direct product-sales revenue, and milestone revenue as non-product
  revenue.
- Diagnostic: `risk_generated`.

## 9633.HK negative case

- Parsed chunks: 547; parser errors: 0.
- Agent result: no risk.
- Diagnostic: `not_applicable`.
- The retrieved product disclosure supports an already commercialized product
  business rather than a pre-commercial candidate.

## LLM and no-key modes

- Deterministic no-key path: PASS.
- Mock structured LLM path: PASS in network-free tests.
- Unavailable/failing LLM degradation: PASS in network-free tests.
- Real external LLM: NOT_TESTED; it is optional and not required for CI.

## v0.2 regression

- 2410.HK parsed chunks/pages: 706.
- Parser errors: 0.
- Evidence pages: 563 / 562.
- Cash runway: 2.76 months.
- Verification: verified.
- Prediction: 90 / critical.

## Review status

- Manifest rows remain `draft`.
- Human second review is still pending; `second_reviewer` is empty.
- 2025 blind set: NOT_ACCESSED.

# Deviations

The first execution stopped correctly at `PLAN_CHANGE_REQUIRED` when the then
current Retriever could not recall the selected Business main evidence. V3-3B
was subsequently approved, implemented, reviewed, and merged independently.
This resumed execution used that merged baseline without changing the V3-7
Plan or expanding V3-7 scope.

The runtime signature compatibility fix is implemented inside the allowed
`business_v03.py`; the frozen `agents/base.py` Protocol remains unchanged.

# Known Limitations

- The implementation is standalone-ready but not wired into ComponentRegistry,
  Container, Workflow, Service, shared Verifier, or UI.
- Real external LLM endpoint behavior was not exercised in this task.
- The three real Business annotations are draft until an actual second reviewer
  completes independent review.
- Deterministic extraction is intentionally narrow and evidence-driven; novel
  layouts or unclear revenue attribution degrade to typed review diagnostics.
- V3-7 does not implement V3-8 specialized verification or V3-9 supervision.

# Suggested Follow-ups

- Perform independent human second review of the 1167.HK and 9633.HK draft
  annotations without altering their status prematurely.
- Review this implementation against the Approved Plan, Execution Report,
  actual diff, and validation results before authorizing commit or PR work.
- Handle shared registration/integration and specialized verification only in
  separately approved future plans.

# Plan Change Requests

None. The earlier Retriever blocker was resolved by the separately approved and
merged V3-3B work before V3-7 resumed.

# Git Diff Summary

The working tree contains ten V3-7 paths: nine created files and one modified
manifest. Git reports the tracked manifest as three inserted rows; untracked
created files are not included in `git diff --stat` until staging.

# Final Git Status

```text
 M tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
?? docs/execution/reports/V3-7_BUSINESS_AGENT_EXECUTION_REPORT.md
?? scripts/check_v03_business_agent.py
?? src/ipo_risk/agents/business_extraction.py
?? src/ipo_risk/agents/business_policy.py
?? src/ipo_risk/agents/business_v03.py
?? tests/contract/test_business_agent_v03_contract.py
?? tests/regression/test_v03_business_golden_values.py
?? tests/unit/test_business_agent_v03.py
?? tests/unit/test_business_extraction_v03.py
```

# Next Action

READY_FOR_REVIEW
