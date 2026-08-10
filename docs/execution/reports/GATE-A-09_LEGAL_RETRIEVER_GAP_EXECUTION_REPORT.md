---
plan_id: GATE-A-09
plan_revision: 1
execution_status: COMPLETED
base_commit: 6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc
start_head: 3853dcab9f36609804927fc4871580e8a4d034ff
end_head: 3853dcab9f36609804927fc4871580e8a4d034ff
branch: fix/v03-legal-retriever-gap
executor: codex
---

# Summary

Closed GATE-A-09 by expanding only the two existing Legal query-family data
definitions. The public Retriever signature, deterministic ranking
implementation, Evidence identity algorithm and eight-family catalog remain
unchanged.

All eight 2020—2023 Legal A—H development draft targets are now present in
Top-5 at fixed `limit=5`: Top-1 1/8, Top-3 6/8 and Top-5 8/8. These results are
development acceptance, not formal reviewed Golden Recall.

```text
GATE_A_09 = PASS
development_validation_only = true
formal_reviewed_golden_metric = false
release_recall_at_3_target_proven = false
```

A—H remain development draft/preselection cases. Their Top-5 8/8 result at a
fixed retrieval limit of 5 satisfies this Approved Plan's GATE-A-09 acceptance.
The Top-3 result is 6/8 (75%) and does not prove the final project
`Recall@3 >= 90%` release target. Formal reviewed-Golden Retriever evaluation
remains future work after human primary and second review.

Planner final review found no ranking-engine blocker. Literal Plan coverage was
synchronized for standalone `VAM`, bare Simplified/Traditional Chinese
anti-dilution variants, and Chinese listing-application rejection variants.

# Plan Compliance

COMPLIANT

# Files Created

- `tests/fixtures/v03_retriever/legal_recall_cases.json`
- `scripts/check_v03_legal_retriever_recall.py`
- `docs/execution/reports/GATE-A-09_LEGAL_RETRIEVER_GAP_EXECUTION_REPORT.md`

# Files Modified

- `src/ipo_risk/retrieval/query_families.py`
- `tests/contract/test_v03_retriever_query_families.py`
- `docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md`
- `docs/V03_GATE_A_CLOSEOUT.md`

# Files Deleted

None.

# Tasks Completed

1. **Record the current Legal Retriever baseline — COMPLETED.** The catalog
   remains the exact eight existing query families and the public signature is
   `retrieve(self, chunks, query, limit=3)`. Pre-change contracts passed 52 and
   28 tests. A—H baseline Top-5 was 4/8: B rank 5, D rank 1, G rank 1 and H
   rank 3; A, C, E and F missed.
2. **Expand `redemption_rights` aliases — COMPLETED.** Added generic Simplified
   Chinese, Traditional Chinese and English terms for special rights,
   liquidation preference, anti-dilution, pre-emption, repurchase/buyback,
   veto, director nomination and valuation-adjustment/VAM arrangements.
3. **Expand rights lifecycle context — COMPLETED.** Added termination, lapse,
   expiry, waiver, restoration, revival, reinstatement and listing-application
   failure variants. These are positive ranking context and are not filters.
4. **Expand `material_litigation_compliance` aliases and status context —
   COMPLETED.** Added litigation, arbitration, regulatory investigation,
   licence/permit, tax, environmental penalty and data-privacy aliases, plus
   pending, resolved, remediation, renewal and suspension status context.
5. **Preserve negative/status Evidence and control boilerplate — COMPLETED.**
   Added generic no-material-litigation, future-exposure, ordinary shareholder
   rights, statutory redemption and similar negative ranking signals. Tests
   prove negative Evidence remains retrievable and direct facts outrank
   boilerplate.
6. **Add multilingual synthetic Legal Retriever fixtures — COMPLETED.** Added
   16 synthetic cases covering active, terminated, waived and restorable
   rights; listing failure; VAM; pending/resolved/no litigation; remediation;
   licence suspension/renewal; future-risk decoy; environmental, privacy and
   tax matters across Simplified Chinese, Traditional Chinese and English.
7. **Strengthen query-family contract tests — COMPLETED.** Added lifecycle,
   status, negative Evidence, decoy ranking, stable ID, traceability and Top-5
   limit assertions. Existing normalization is exercised for case, line break,
   whitespace and hyphen variants.
8. **Add a safe real-development validation script — COMPLETED.** The script
   accepts repeated `CASE=PATH` arguments or JSON environment configuration,
   performs no network access and prints no paths or prospectus text. Missing
   input returns `BLOCKED`.
9. **Run A—H development acceptance with `limit=5` — COMPLETED.** Results:

   | Case | Stock | Family | Expected | Ranked pages | Rank | Result |
   |---|---|---|---:|---|---:|---|
   | A | 9898.HK | redemption_rights | 300 | 169, 468, 546, 300, 125 | 4 | HIT |
   | B | 9863.HK | redemption_rights | 207 | 555, 217, 488, 207, 516 | 4 | HIT |
   | C | 2517.HK | redemption_rights | 152 | 80, 152, 142, 429, 81 | 2 | HIT |
   | D | 1961.HK | redemption_rights | 78 | 338, 532, 78, 533, 549 | 3 | HIT |
   | E | 6698.HK | material_litigation_compliance | 26 | 300, 26, 27, 308, 723 | 2 | HIT |
   | F | 2451.HK | material_litigation_compliance | 298 | 293, 298, 18, 679, 303 | 2 | HIT |
   | G | 9600.HK | material_litigation_compliance | 222 | 21, 222, 116, 119, 58 | 2 | HIT |
   | H | 1942.HK | material_litigation_compliance | 44 | 44, 49, 131, 165, 171 | 1 | HIT |

   Stable Evidence IDs were emitted for every ranked page and manually
   inspected. They are retained in the safe script output rather than copied
   into production rules.
10. **Run regression and scope validation — COMPLETED.** All mandatory commands
    and available v0.2 real checks passed. No 2025 file was opened or used.
11. **Close GATE-A-09 only after all checks pass — COMPLETED.** The Gap Report
    is resolved and only GATE-A-09 changed from FAIL to PASS. GATE-A-03/04/05/
    06/10 remain FAIL and V3-8 remains BLOCKED.
12. **Write the Execution Report — COMPLETED.** This report records actual
    baseline, final results, scope and validation outcomes.

# Validation Results

## Legal query-family contracts

- **Command:** `pytest -q tests/contract/test_v03_retriever_query_families.py`
- **Result:** PASS
- **Details:** 71 passed in 0.75s after the final contract changes. Baseline was
  52 passed.

## Existing Keyword Retriever contracts

- **Command:** `pytest -q tests/contract/test_keyword_retriever.py`
- **Result:** PASS
- **Details:** 28 passed in 0.45s.

## Complete suite

- **Command:** `pytest -q`
- **Result:** PASS
- **Details:** 849 passed in 13.60s.

## Project validation

- **Command:** `python scripts/validate_project.py`
- **Result:** PASS
- **Details:** `status=completed`, `verified=3`, `pending=1`.

## Competition-data validation

- **Command:** `python scripts/validate_competition_data.py`
- **Result:** PASS
- **Details:** `competition_data_validation=passed`. The desktop bundled Python
  dependency path supplied `openpyxl`; no dependency was installed or changed.

## Byte compilation

- **Command:** `python -m compileall -q app src scripts`
- **Result:** PASS
- **Details:** Completed with no compile error.

## Scope Guard

- **Command:** `python scripts/check_execution_scope.py docs/execution/plans/GATE-A-09_LEGAL_RETRIEVER_GAP_PLAN.md`
- **Result:** PASS
- **Details:** `execution_scope=valid` after each material stage and at final
  validation.

## Whitespace validation

- **Command:** `git diff --check`
- **Result:** PASS
- **Details:** No whitespace error. Git emitted only the existing Windows
  LF-to-CRLF checkout warning.

## Changed-path inspection

- **Command:** `git diff --name-only`
- **Result:** PASS
- **Details:** Tracked changes are Plan-allowed. Final `git status --short`
  additionally lists the three Plan-allowed created files.

## v0.2 real Retriever regression

- **Command:** `python scripts/check_real_keyword_retriever.py`
- **Result:** PASS
- **Details:** Cash page 563 ranked first; operating cash-flow page 562 ranked
  first; legal/constitution decoys 665 and 683 were not matched.

## v0.2 real Service E2E regression

- **Command:** `python scripts/check_real_v02_e2e.py`
- **Result:** PASS
- **Details:** 706 parsed pages, zero parser errors, Evidence pages 563/562,
  cash runway 2.76 months, `verified`, prediction `90.0/critical`.

# Acceptance Criteria

- **PASS — Vocabulary and ranking context.** Both Legal families cover the
  approved multilingual alias and lifecycle/status classes. Existing
  normalization handles the required variants. Negative/status Evidence is
  retrievable and direct facts outrank generic boilerplate.
- **PASS — Contract and traceability.** The catalog remains exactly eight
  names; Retriever and Schema interfaces are unchanged; Evidence IDs and
  physical-page traceability are stable; `limit` behavior is unchanged.
- **PASS — Development acceptance.** All eight expected physical pages appear
  in Top-5 at `limit=5`; counts and ranks are recorded as development draft
  acceptance, not formal Golden Recall.
- **PASS — Safety and scope.** No case-specific production rule, 2025 blind
  input, forbidden file, Golden CSV, dependency or public-interface change.
- **PASS — Gate status.** Only GATE-A-09 changed to PASS. Other mandatory FAIL
  items remain unchanged and V3-8 remains BLOCKED.

# Manual Validation

- Confirmed all eight required PDFs were available before editing.
- Inspected A—H target pages and returned Top-5 pages using physical PDF page
  numbers.
- Repeated the safe validator and confirmed stable Evidence IDs and identical
  A—H ranking.
- Inspected production additions for stock codes, company names, document IDs,
  page numbers, Evidence IDs, credentials and local paths; none are present.
- Confirmed `keyword.py`, public interfaces, Golden fixtures and the Approved
  Plan have no diff.
- Confirmed only 2020—2023 development prospectuses were accessed; the 2025
  blind set was not opened, parsed, retrieved or tuned.
- Remaining human Golden primary/second review is outside GATE-A-09 and remains
  open under GATE-A-05/06.

# Deviations

None.

# Known Limitations

- A—H are draft preselection cases and do not establish formal Golden Recall.
- The acceptance target is Top-5; only one selected target ranks Top-1.
- Legal Agent Golden review and real-provider prompt routing remain separate
  Gate A blockers.

# Suggested Follow-ups

- Execute a separately approved GATE-A-10 Plan for Legal real-provider prompt
  routing.
- Complete Legal A—H human primary/second review and Case C adjudication before
  merging reviewed Legal rows into the canonical Golden manifest.

# Plan Change Requests

None.

# Git Diff Summary

```text
docs/V03_GATE_A_CLOSEOUT.md                        | 14 ++--
docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md             | 34 ++++++++
src/ipo_risk/retrieval/query_families.py           | 50 +++++++++++
tests/contract/test_v03_retriever_query_families.py | 97 ++++++++++++++++++++++
4 files changed, 188 insertions(+), 7 deletions(-)
```

The three created files and two modified documentation files are shown in the
final status; untracked files are not included by plain `git diff --stat`.

# Final Git Status

```text
 M docs/V03_GATE_A_CLOSEOUT.md
 M docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md
 M src/ipo_risk/retrieval/query_families.py
 M tests/contract/test_v03_retriever_query_families.py
?? docs/execution/reports/GATE-A-09_LEGAL_RETRIEVER_GAP_EXECUTION_REPORT.md
?? scripts/check_v03_legal_retriever_recall.py
?? tests/fixtures/v03_retriever/legal_recall_cases.json
```

# Next Action

READY_FOR_REVIEW
