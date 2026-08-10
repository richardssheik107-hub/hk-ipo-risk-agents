# V03 Legal A–H Formal Double-Review Audit

Audit date: 2026-08-10

Promotion status: `FORMAL_LEGAL_GOLDEN_PROMOTED_TO_CANONICAL_FIXTURE`

This document records only the formal human-review outcome required to govern
the v0.3 Legal Golden rows. It intentionally excludes reviewer working copies,
Q&A transcripts, local review outputs, backup locations, rendered pages and
other review-process artifacts.

## Review provenance

- Primary reviewer: `Ap`
- Primary review date: `2026-08-10`
- Independent second reviewer: `Pan***`
- Second review date: `2026-08-10`
- Independence status: `USER_CONFIRMED`
- Human adjudicator: `An`
- Adjudication date: `2026-08-10`
- Codex preselection used for formal decisions: `NO`
- 2025 blind data used: `NO`

The user confirmed that the second reviewer independently checked the A–H
source PDFs before seeing the Primary reviewer's final labels and reasoning.
The formal decision source is limited to the two human reviews and the human
adjudications recorded below.

## Final A–H outcomes

| Case | Case ID | Risk code | Final decision | Review status | Physical page |
| --- | --- | --- | --- | --- | --- |
| A | `ipo_2021_09898` | `redemption_rights` | `false / rejected / not_applicable` | `adjudicated` | 300 |
| B | `ipo_2022_09863` | `redemption_rights` | `false / rejected / not_applicable` | `double_reviewed` | 207 |
| C | `ipo_2023_02517` | `redemption_rights` | `true / verified / medium` | `adjudicated` | 152 |
| D | `ipo_2020_01961` | `redemption_rights` | `true / verified / medium` | `adjudicated` | 150 |
| E | `ipo_2022_06698` | `material_litigation_compliance` | `true / verified / medium` | `double_reviewed` | 26 |
| F | `ipo_2023_02451` | `material_litigation_compliance` | `false / rejected / not_applicable` | `adjudicated` | 300 |
| G | `ipo_2020_09600` | `material_litigation_compliance` | `false / rejected / not_applicable` | `double_reviewed` | 222 |
| H | `ipo_2020_01942` | `material_litigation_compliance` | `false / rejected / not_applicable` | `double_reviewed` | 44 |

Fully agreed cases: `B, E, G, H`

Human-adjudicated cases: `A, C, D, F`

All label disagreements resolved: `YES`

Mandatory Case C adjudication completed: `YES`

## Adjudication record

### Case A

The disputed rights are board representation, transfer-control and securities
registration rights, not redemption, repurchase or investor put rights. The
final finding is therefore `false / rejected / not_applicable`. Physical page
300 contains the target sentence; page 299 is supporting context.

### Case C

Formal arbitration record: `C-2517-RED-20260810-001`.

The right's nature, holders, controlling-shareholder obligors, pre-application
termination and automatic listing-failure restoration conditions are explicit,
so the status is `verified`. The final human governance decision retains
`medium`: the automatic restoration mechanism is a substantive conditional
exit right, and the absence of price, IRR and payment-term disclosure does not
support reducing the frozen Legal severity to `low`. The earlier proposed
`low` outcome was expressly revised; no severity-policy conflict remains.

### Case D

Document-level evidence resolves the target-page incompleteness. Physical page
150 states the issuer redemption obligation, triggers, principal-based amount
and fifth-business-day mechanics; physical page 78 remains the original anchor.
The final finding is `true / verified / medium`.

### Case F

The pending patent litigation is real, but the prospectus evidence on physical
pages 299–300 supports a non-material current exposure and no material adverse
impact. Physical page 300 is the primary materiality evidence; pages 294–301
remain context. The final finding is `false / rejected / not_applicable`.

## Promotion controls

- Canonical fixture: `tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`
- Legal fixture: `tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv`
- Canonical rows: 8
- `double_reviewed`: 4
- `adjudicated`: 4
- Reviewer fields: `Ap / Pan***`
- Unresolved human disagreement: `NO`
- Unresolved policy conflict: `NO`
- Canonical merge performed by this branch: `YES`
- GitHub merge performed: `NO`

## Validation

Validation results are recorded from the final promotion branch before commit:

- Golden schema and integrity: `PASS`
- Legal annotation contract: `PASS`
- Physical page / exact-text check: `PASS (8/8)`
- 2025 blind guard: `PASS`
- Repository hygiene and scope audit: `PASS (promotion scope only; no workbench history or review-process artifacts)`
- Project validation: `PASS (status=completed, verified=3, pending=1)`
- Full test suite: `PASS (861 passed)`
