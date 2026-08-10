---
plan_id: GATE-A-07-08
plan_revision: 1
execution_status: COMPLETED
base_commit: 41b4528b820fff1738449703d745aed8d2c4b2f9
start_head: 64b84f54c4caf3f8a7eb0274bacd7dafd620df9a
end_head: 64b84f54c4caf3f8a7eb0274bacd7dafd620df9a
branch: fix/v03-legal-contract-severity-freeze
executor: codex
---

# GATE-A-07-08 Legal Contract and Severity Execution Report

## Summary

Formalized the existing Legal candidate fields as the approved, additive and
backward-compatible v0.3 internal candidate contract. Frozen both Legal risk
codes at provisional, deterministic `medium / 50`, added matching
machine-readable configuration, strengthened contract tests, and updated
human-review guidance without changing production Python or Golden data.

```text
runtime_production_behavior_changed = false
public_contract=v03_contract_v1
GATE-A-07=PASS
GATE-A-08=PASS
V3-8_START_STATUS=BLOCKED
```

### Contract Decision Formalized

The approved `ShareholderRightCandidate` and `LitigationComplianceCandidate`
field sets exactly match the models present at the execution baseline. Their
existing defaults preserve old minimal payload validation. Approval does not
make all additive fields mandatory: `MUST_HAVE_FOR_DECISION`, `REVIEW_SIGNAL`,
and `OPTIONAL_SUPPORTING_FACT` remain distinct.

The candidate-layer name remains `counterparty_or_authority`. The normalized
observation layer may use `counterparty_or_regulator`; no production rename or
public interface change occurred.

### Severity Policy Formalized

Both `redemption_rights` and `material_litigation_compliance` remain
provisional `medium / 50`. Builders emit `level_is_provisional=true`,
`score_is_rule_based=true`, and `score_is_probability=false`. Contract tests
also show that the specialized Legal Verifiers preserve level and score while
changing only verification state. Any future `high` or `critical` mapping
requires a separately versioned policy.

### Golden Review Guidance

Cases A and E retain their unchanged draft `expected_level=high` CSV values.
The checklist now identifies those values as pre-policy suggestions and directs
human reviewers to resolve them against frozen `medium / 50`. No reviewer,
review status, annotation value, or fixture was changed.

### Post-execution Planner Review Synchronization

After the runtime execution completed, Planner review corrected three
documentation/governance records: Legal professional review ownership was
assigned to Member-4 while Member-2 retained data-governance and technical
rerun support; the Gate A snapshot was aligned to `main@41b4528b`; and stale
Case A/E wording was aligned to the frozen provisional `medium / 50` policy.
These follow-ups did not change production runtime behavior, public contracts,
Golden data, Gate results, or the execution conclusions recorded above.

### Candidate Compatibility Result

PASS. Exact `model_fields` assertions and old-minimal-payload tests confirm
that approved additive defaults remain backward-compatible. No candidate model
or runtime implementation was changed.

### Files Changed

Nine existing Allowed Files were modified and two Allowed Files were created.
The authoritative path lists appear under Files Created and Files Modified.

### Remaining Gate A Blockers

GATE-A-03, GATE-A-04, GATE-A-05, GATE-A-06, GATE-A-09, and GATE-A-10 remain
FAIL. Consequently `V3-8_START_STATUS = BLOCKED`.

## Plan Compliance

COMPLIANT. All changes are within Allowed Files. The Approved Plan, production
Python, public interfaces, Golden fixtures, Retriever, Provider, Workflow,
Service, dependency files, and 2025 blind data were not modified or accessed.

## Files Created

- `tests/contract/test_legal_candidate_contract_v03.py`
- `docs/execution/reports/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md`

## Files Modified

- `configs/v03_risk_rules.yaml`
- `docs/V03_DEVELOPMENT_CONTRACT.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `docs/V03_LEGAL_CONTRACT_DELTA.md`
- `docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md`
- `docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md`
- `docs/V03_RISK_RULES.md`
- `tests/contract/test_material_litigation_compliance_risk_contract.py`
- `tests/contract/test_redemption_rights_risk_contract.py`

## Files Deleted

None.

## Tasks Completed

### 1. Verify the approved internal candidate contract

- [x] Inspected `legal_models.py` without modifying it.
- [x] Confirmed both candidate models exactly match the approved field sets.
- [x] Confirmed defaults and optional semantics preserve minimal payloads.
- [x] Confirmed candidate/observation naming remains distinct.
- [x] No field or default mismatch was found.

### 2. Formalize the development contract

- [x] Documented both exact Legal candidate field sets.
- [x] Documented additive, backward-compatible internal status.
- [x] Preserved all three field-requirement classes.
- [x] Kept the public contract at `v03_contract_v1`.

### 3. Resolve the Contract Delta

- [x] Marked the delta `RESOLVED / APPROVED`.
- [x] Preserved each field's historical rationale.
- [x] Removed outstanding Member-1 approval language.
- [x] Did not claim that every approved field is universally required.

### 4. Freeze the Legal severity policy

- [x] Documented `medium / 50` for both Legal risk codes.
- [x] Froze provisional, deterministic, non-probability metadata.
- [x] Documented that Agent and specialized Verifier do not escalate severity.
- [x] Required a separate versioned policy for future escalation.

### 5. Add backward-compatible configuration

- [x] Added matching `candidate_severity` blocks to both Legal risks.
- [x] Kept the configuration additive.
- [x] Did not rename keys or change Financial/Business rules.

### 6. Strengthen Legal contract tests

- [x] Asserted exact candidate field sets.
- [x] Asserted old minimal payload compatibility and additive defaults.
- [x] Asserted both builders remain `medium / 50`.
- [x] Asserted neither builder emits `high` or `critical`.
- [x] Asserted all three severity metadata flags.
- [x] Asserted both specialized Verifiers preserve level and score.
- [x] Added configuration-to-policy equality assertions.
- [x] No test was weakened, skipped, or xfailed.

### 7. Update Golden human-review guidance

- [x] Marked A/E draft `high` as non-authoritative pre-policy suggestions.
- [x] Directed reviewers to frozen `medium / 50`.
- [x] Did not modify any Golden CSV row.
- [x] Did not fabricate review status or a second reviewer.

### 8. Close Gate A decision items

- [x] Changed GATE-A-07 to PASS after contract validation passed.
- [x] Changed GATE-A-08 to PASS after severity validation passed.
- [x] Kept GATE-A-03/04/05/06/09/10 unresolved.
- [x] Kept `V3-8_START_STATUS = BLOCKED`.

### 9. Write the Execution Report

- [x] Created this report at the frozen report path.
- [x] Recorded compliance, decisions, validation, non-modification guarantees,
  remaining blockers, and next action.

## Validation Results

### Targeted Legal contract tests

- Command: `pytest -q tests/contract/test_redemption_rights_risk_contract.py`
- Result: PASS
- Details: 2 passed; builder and Verifier preserve provisional `medium / 50`.

- Command: `pytest -q tests/contract/test_material_litigation_compliance_risk_contract.py`
- Result: PASS
- Details: 3 passed; builder and Verifier preserve provisional `medium / 50`.

- Command: `pytest -q tests/contract/test_legal_candidate_contract_v03.py`
- Result: PASS
- Details: 5 passed; exact fields, defaults, minimal payloads, naming and YAML policy validated.

### Complete project validation

- Command: `pytest -q`
- Result: PASS
- Details: 830 passed in 13.81 seconds.

- Command: `python scripts/validate_project.py`
- Result: PASS
- Details: `status=completed verified=3 pending=1`.

- Command: `python scripts/validate_competition_data.py`
- Result: PASS
- Details: `competition_data_validation=passed` using the existing workspace runtime; no installation performed.

- Command: `python -m compileall -q app src scripts`
- Result: PASS
- Details: completed with no errors.

- Command: `python scripts/check_execution_scope.py docs/execution/plans/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_PLAN.md`
- Result: PASS
- Details: `execution_scope=valid` before and after material changes.

- Command: `git diff --check`
- Result: PASS
- Details: no whitespace errors; Git emitted only local line-ending notices.

### Scope Guard

- Production diff: empty (`git diff -- src`).
- Golden/fixture diff: empty (`git diff -- tests/fixtures`).
- Approved Plan diff: empty.
- Legal Golden manifest hash remained `5a9e1e50c1254c399003d9ab2d4225994c87d480`.
- Added-line scan found no secret, credential, token assignment, authorization
  header, or local absolute path.
- No cache, binary, PDF, ZIP, generated result, or dependency artifact entered the diff.
- No 2025 blind-set file was opened, read, tuned against, or modified.

## Acceptance Criteria

### Contract

- PASS — Both candidate field sets exactly match the approved lists.
- PASS — Defaults and optional semantics remain backward-compatible.
- PASS — Old minimal candidate payloads validate.
- PASS — `counterparty_or_authority` remains unchanged.
- PASS — Observation `counterparty_or_regulator` remains distinct.
- PASS — Public `v03_contract_v1` and public interfaces are unchanged.

### Severity

- PASS — Both Legal codes use provisional `medium / 50`.
- PASS — Metadata is provisional, rule-based, and non-probability.
- PASS — Builders and Verifiers do not auto-escalate level or score.
- PASS — Configuration expresses the same policy additively.

### Golden governance

- PASS — A/E are documented as pre-policy draft suggestions.
- PASS — Golden CSV and annotation values are unchanged.
- PASS — No second reviewer or review status was fabricated.

### Gate status

- PASS — GATE-A-07 changed only after successful contract validation.
- PASS — GATE-A-08 changed only after successful severity validation.
- PASS — `V3-8_START_STATUS = BLOCKED` remains unchanged.

### Scope

- PASS — No production Python diff.
- PASS — No Golden CSV or fixture diff.
- PASS — No Retriever, Provider, Schema, Workflow, Service, or dependency diff.
- PASS — No 2025 blind access or tuning.
- PASS — No secret, local absolute path, cache, or binary artifact.

## Manual Validation

- Completed: compared both `model_fields` collections with the approved lists.
- Completed: instantiated old minimal payloads through contract tests.
- Completed: inspected representative Builder outputs and Verifier copies for both codes.
- Completed: compared the Legal Golden manifest hash before and after execution.
- Completed: inspected final scope for production and Golden-data changes.
- Remaining human checks: A—H primary/second review and Case C adjudication remain Gate A work.

## Deviations

None.

## Known Limitations

- The severity policy is intentionally provisional and not a calibrated probability.
- Cases A and E still contain pre-policy draft values pending human review.
- GATE-A-03/04/05/06/09/10 remain unresolved.
- This task does not integrate Legal into shared runtime or start V3-8.

## Suggested Follow-ups

- Close the Legal Retriever gaps under a separate Approved Plan.
- Integrate the Legal domain prompt into real-provider runtime routing separately.
- Complete independent Financial, Business and Legal Golden reviews.
- Run a final Gate A audit before drafting V3-8.

## Plan Change Requests

None.

## Git Diff Summary

```text
configs/v03_risk_rules.yaml                        |  12 +
docs/V03_DEVELOPMENT_CONTRACT.md                   |  64 +++
docs/V03_GATE_A_CLOSEOUT.md                        |  20 +-
docs/V03_LEGAL_CONTRACT_DELTA.md                   |  53 +--
docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md         |   6 +
docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md          |  23 +-
docs/V03_RISK_RULES.md                             |   8 +
.../GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_PLAN.md   | 429 +++++++++++++++++++++
...-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md | 341 ++++++++++++++++
.../contract/test_legal_candidate_contract_v03.py  | 105 +++++
...material_litigation_compliance_risk_contract.py |  11 +
.../test_redemption_rights_risk_contract.py        |  11 +
12 files changed, 1044 insertions(+), 39 deletions(-)
```

This final summary compares `main@41b4528b` with the complete reviewed branch,
including the Approved Plan, execution result, and post-execution Planner
documentation synchronization.

## Final Git Status

```text
 M configs/v03_risk_rules.yaml
 M docs/V03_DEVELOPMENT_CONTRACT.md
 M docs/V03_GATE_A_CLOSEOUT.md
 M docs/V03_LEGAL_CONTRACT_DELTA.md
 M docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md
 M docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md
 M docs/V03_RISK_RULES.md
 M tests/contract/test_material_litigation_compliance_risk_contract.py
 M tests/contract/test_redemption_rights_risk_contract.py
?? docs/execution/reports/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md
?? tests/contract/test_legal_candidate_contract_v03.py
```

## Next Action

READY_FOR_REVIEW
