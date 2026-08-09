---
plan_id: GATE-A-07-08
title: Legal Candidate Contract Approval and v0.3 Severity Policy Formalization
status: APPROVED
revision: 1
base_commit: 41b4528b820fff1738449703d745aed8d2c4b2f9
branch: fix/v03-legal-contract-severity-freeze
owner: lead-1-tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md
---

# Legal Candidate Contract Approval and v0.3 Severity Policy Formalization

## Goal

Formalize the already-existing Legal candidate schema and the current
`medium / 50` provisional Legal severity behavior as the authoritative v0.3
internal contract, without changing production runtime behavior.

This Plan closes only:

- `GATE-A-07`: Legal candidate additive contract approval;
- `GATE-A-08`: Legal severity policy freeze.

It does not start V3-8 and does not authorize shared integration.

## Background

At `main@41b4528b820fff1738449703d745aed8d2c4b2f9`, Financial, Legal, and
Business standalone Agents are merged. Gate A remains blocked by governance,
retrieval, runtime prompt, and human Golden-review work.

The current Legal implementation already contains additive internal candidate
fields and emits provisional `medium / 50` candidates. The repository still
describes those fields as awaiting Member-1 approval, while draft Legal Golden
Cases A and E contain pre-policy `expected_level=high` suggestions. This Plan
formalizes the current compatible behavior; it does not redesign the models or
edit Golden CSV values.

## Project Rules

The Executor must read and follow:

- `AGENTS.md`
- `docs/PROJECT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_SCHEMA.md`
- `docs/V03_DEVELOPMENT_CONTRACT.md`
- `docs/V03_RISK_RULES.md`
- `docs/V03_LEGAL_CONTRACT_DELTA.md`
- `docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md`
- `docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `docs/execution/README.md`

The global public contract remains:

```text
v03_contract_v1
```

This is an additive internal candidate-contract formalization. No public
`RiskAgent`, Schema, Provider, Retriever, Workflow, or Service contract change
is approved.

## Planner Decision — Legal Candidate Contract

Member-1 and the Planner approve the fields already present in
`src/ipo_risk/agents/legal_models.py` as the frozen v0.3 internal Legal
candidate contract.

### ShareholderRightCandidate

Approved fields:

```text
right_type
holder
trigger_or_termination
survives_listing
is_effective
termination_event
termination_timing
restoration_clause
restoration_condition
impact_on_public_shareholders
uncertainty_reason
evidence_ids
```

### LitigationComplianceCandidate

Approved fields:

```text
matter_type
subject
counterparty_or_authority
current_status
event_date
amount
currency
amount_unit
is_pending
is_resolved
is_remediated
management_materiality
potential_impact
license_impact
materiality_stated
uncertainty_reason
evidence_ids
```

Approval does not make every field mandatory. Preserve the existing field
requirement classes:

```text
MUST_HAVE_FOR_DECISION
REVIEW_SIGNAL
OPTIONAL_SUPPORTING_FACT
```

Do not rename candidate-layer `counterparty_or_authority`. The normalized
internal observation layer may continue using `counterparty_or_regulator`.

## Planner Decision — v0.3 Legal Severity

Freeze v0.3 candidate severity as:

```text
redemption_rights:
  level = medium
  score = 50

material_litigation_compliance:
  level = medium
  score = 50
```

Every generated Legal candidate must record:

```text
level_is_provisional = true
score_is_rule_based = true
score_is_probability = false
```

The Agent must not auto-upgrade Legal risks to `high` or `critical`. The
specialized Legal Verifier changes verification status only and does not
escalate level or score. A verified v0.3 Legal risk may intentionally remain:

```text
verified
medium
50
provisional severity
```

A Legal `high` or `critical` mapping requires a future explicitly versioned
severity policy and is outside this Plan.

Legal draft Golden Cases A and E currently contain `expected_level=high`.
Those values are pre-policy suggestions, not authoritative v0.3 severity.
This Plan must not modify their CSV rows. Human review guidance must require
reviewers to resolve them against the frozen `medium / 50` policy.

## Inputs

The Executor must inspect these files as factual inputs without modifying
production Python or Golden data:

- `src/ipo_risk/agents/legal_models.py`
- the Legal builders and policy implementation that currently emit candidates;
- `tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv`
- `docs/V03_LEGAL_CONTRACT_DELTA.md`
- `docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md`
- `docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md`
- `configs/v03_risk_rules.yaml`
- existing Legal contract tests.

## Allowed Files

- `docs/V03_DEVELOPMENT_CONTRACT.md`
- `docs/V03_LEGAL_CONTRACT_DELTA.md`
- `docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md`
- `docs/V03_RISK_RULES.md`
- `docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `configs/v03_risk_rules.yaml`
- `tests/contract/test_redemption_rights_risk_contract.py`
- `tests/contract/test_material_litigation_compliance_risk_contract.py`
- `tests/contract/test_legal_candidate_contract_v03.py`
- `docs/execution/reports/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md`

## Forbidden Files

- `docs/execution/plans/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_PLAN.md`
- `src/ipo_risk/agents/`
- `src/ipo_risk/extraction/`
- `src/ipo_risk/domain/`
- `src/ipo_risk/providers/`
- `src/ipo_risk/retrieval/`
- `src/ipo_risk/core/`
- `src/ipo_risk/workflows/`
- `src/ipo_risk/services/`
- `src/ipo_risk/schemas/`
- `tests/fixtures/`
- all Golden CSV files;
- every `configs/` file except `configs/v03_risk_rules.yaml`;
- `pyproject.toml`
- `app/`
- `data/`
- every other Approved Execution Plan.

No production Python change, Golden annotation change, dependency change, or
public interface change is authorized.

## Tasks

### 1. Verify the approved internal candidate contract

- [ ] Inspect `legal_models.py` without modifying it.
- [ ] Confirm both candidate models contain exactly the Planner-approved fields.
- [ ] Confirm current defaults and optional semantics preserve old minimal
  payload validation.
- [ ] Confirm `counterparty_or_authority` remains the candidate-layer name and
  `counterparty_or_regulator` remains an observation-layer normalization only.
- [ ] Stop if fields or defaults differ from the approved decision.

### 2. Formalize the development contract

- [ ] Document the exact approved Legal candidate fields.
- [ ] Document their additive, backward-compatible internal status.
- [ ] Preserve `MUST_HAVE_FOR_DECISION`, `REVIEW_SIGNAL`, and
  `OPTIONAL_SUPPORTING_FACT` semantics.
- [ ] State explicitly that `v03_contract_v1` remains the public contract.

### 3. Resolve the Contract Delta

- [ ] Mark `V03_LEGAL_CONTRACT_DELTA.md` as `RESOLVED / APPROVED`.
- [ ] Preserve the historical rationale for each additive field.
- [ ] Remove language implying Member-1 approval remains outstanding.
- [ ] Do not claim that every approved field is required on every decision path.

### 4. Freeze the Legal severity policy

- [ ] Document `medium / 50` for both Legal risk codes.
- [ ] Freeze provisional, deterministic, non-probability metadata semantics.
- [ ] State that Agent and specialized Verifier do not escalate to `high` or
  `critical` in v0.3.
- [ ] State that a future escalation mapping requires a separately versioned
  policy.

### 5. Add backward-compatible configuration

- [ ] Add the same severity semantics to `configs/v03_risk_rules.yaml`.
- [ ] Keep the change additive and backward-compatible.
- [ ] Do not rename existing keys or change unrelated Financial/Business rules.

### 6. Strengthen Legal contract tests

- [ ] Prove the exact approved candidate fields remain available.
- [ ] Prove old minimal payloads remain valid.
- [ ] Prove additive defaults remain backward-compatible.
- [ ] Prove Legal builders remain `medium / 50`.
- [ ] Prove Legal builders never auto-upgrade to `high` or `critical`.
- [ ] Prove `level_is_provisional=true`.
- [ ] Prove `score_is_rule_based=true`.
- [ ] Prove `score_is_probability=false`.
- [ ] Do not weaken, skip, or xfail existing tests.

### 7. Update Golden human-review guidance

- [ ] State that Case A and Case E draft `high` values are pre-policy
  suggestions and not authoritative.
- [ ] Instruct human reviewers to resolve those draft values against the frozen
  `medium / 50` v0.3 policy.
- [ ] Do not modify any Golden CSV row.
- [ ] Do not fabricate a second reviewer or change review status.

### 8. Close Gate A decision items

Only after all required validation passes:

- [ ] Change `GATE-A-07` to `PASS`.
- [ ] Change `GATE-A-08` to `PASS`.
- [ ] Keep `V3-8_START_STATUS = BLOCKED` because GATE-A-03, GATE-A-04,
  GATE-A-05, GATE-A-06, GATE-A-09, and GATE-A-10 remain unresolved.

### 9. Write the Execution Report

- [ ] Create the report at the frozen `report_path`.
- [ ] Record Plan compliance, field verification, policy behavior, files,
  validation, Golden non-modification, remaining Gate A blockers, and the exact
  next action.

## Acceptance Criteria

### Contract

- Both Legal candidate field sets exactly match the Planner-approved lists.
- Existing default and optional semantics remain backward-compatible.
- Old minimal candidate payloads still validate.
- `counterparty_or_authority` is not renamed.
- Observation-layer `counterparty_or_regulator` remains clearly distinct.
- Public `v03_contract_v1` and all public interfaces remain unchanged.

### Severity

- Both Legal risk codes use provisional `medium / 50` candidates.
- Metadata states rule-based, non-probability, provisional severity.
- Neither builder nor Verifier auto-escalates Legal risk level or score.
- Configuration documents the same behavior additively.

### Golden governance

- Cases A and E are documented as pre-policy draft suggestions.
- No Golden CSV or annotation value changes.
- No second reviewer or review status is fabricated.

### Gate status

- `GATE-A-07 = PASS` only after contract validation succeeds.
- `GATE-A-08 = PASS` only after severity validation succeeds.
- `V3-8_START_STATUS = BLOCKED` remains unchanged.

### Scope

- No production Python diff.
- No Golden CSV or fixture diff.
- No Retriever, LLMProvider, Schema, Workflow, Service, or dependency diff.
- No 2025 blind-set access or tuning.
- No secret, token, raw credential, local absolute path, cache, or binary file.

## Required Validation

Run the three targeted Legal contract test files:

```text
pytest -q tests/contract/test_redemption_rights_risk_contract.py
pytest -q tests/contract/test_material_litigation_compliance_risk_contract.py
pytest -q tests/contract/test_legal_candidate_contract_v03.py
```

Run the complete project validation:

```text
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python -m compileall -q app src scripts
python scripts/check_execution_scope.py docs/execution/plans/GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_PLAN.md
git diff --check
```

The Scope Guard is required once this Approved Plan is tracked and execution
actually begins.

Confirm explicitly:

- no production Python diff;
- no Golden CSV or fixture diff;
- no 2025 blind access;
- no secrets or absolute paths;
- all changes remain inside Allowed Files.

## Manual Validation

- Compare `model_fields` for both Legal candidate models with the approved
  lists without modifying production models.
- Validate old minimal payloads and current additive payloads through tests.
- Inspect representative Legal builder outputs for both risk codes and confirm
  `medium / 50` with provisional, rule-based, non-probability metadata.
- Confirm Cases A and E remain unchanged in the Legal Golden CSV.
- Confirm the final diff contains no production Python or Golden data.

Real external LLM access is not required. No 2025 blind case may be opened or
used.

## Stop Conditions

Stop with `PLAN_CHANGE_REQUIRED` if any of the following occurs:

- any production Python change is required;
- `legal_models.py` must change;
- a public Schema or public interface must change;
- current runtime behavior does not match `medium / 50`;
- existing candidate fields or defaults differ from the approved lists;
- a Golden CSV or fixture must change;
- Retriever or LLMProvider changes become necessary;
- configuration cannot express the policy additively;
- validation requires weakening, skipping, or xfail of an existing test;
- any file outside Allowed Files must change.

Stop with `BLOCKED` if required tests or repository prerequisites cannot be
accessed and the issue cannot be resolved within Allowed Files.

Stop immediately without committing if a credential, local absolute path,
binary artifact, cache, generated result, or 2025 blind-set content is about to
enter the diff.

## Expected Deliverables

- authoritative internal Legal candidate contract documentation;
- `V03_LEGAL_CONTRACT_DELTA.md` marked `RESOLVED / APPROVED`;
- candidate/observation naming distinction documented;
- frozen v0.3 Legal `medium / 50` provisional severity policy;
- additive severity configuration;
- strengthened Legal candidate and builder contract tests;
- updated Case A/E human-review guidance without CSV edits;
- `GATE-A-07` and `GATE-A-08` marked PASS only after validation;
- `V3-8_START_STATUS = BLOCKED` retained;
- `GATE-A-07-08_LEGAL_CONTRACT_SEVERITY_EXECUTION_REPORT.md`.

## Notes

- This Plan formalizes existing runtime behavior; it does not authorize a new
  Legal implementation.
- Approval of a candidate field does not make it mandatory on every decision
  path.
- A verified Legal risk remaining provisional `medium / 50` is intentional in
  v0.3.
- Gate A remains blocked after this Plan because GATE-A-03/04/05/06/09/10 are
  still unresolved.
- This Plan does not authorize commit, push, PR creation, merge, tag, release,
  V3-8 execution, or shared integration.
