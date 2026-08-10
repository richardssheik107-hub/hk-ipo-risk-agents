---
plan_id: V03-COMPLETION-ONE-SHOT
title: Complete v0.3 Multi-Agent Risk Analysis
status: APPROVED
revision: 1
base_commit: cb7197558510bb92c454e5ab22c8413fa91147c0
branch: feat/v03-completion-one-shot
owner: lead-1-tech-lead
planner: web-chatgpt
executor: codex
report_path: docs/execution/reports/V03_COMPLETION_ONE_SHOT_EXECUTION_REPORT.md
---

# Complete v0.3 Multi-Agent Risk Analysis

## Goal

Execute the remaining v0.3 engineering sequence as one controlled program while
preserving every frozen repository contract, human-review requirement, v0.2
regression, Mock path and 2025 blind-set boundary.

The program must stop honestly after GATE-A-10 if genuine human evidence for
GATE-A-03/04/05/06 is absent. V3-8 and every dependent phase are conditional on
all mandatory Gate A criteria being genuinely PASS.

## Background

The authoritative implementation base is
`main@cb7197558510bb92c454e5ab22c8413fa91147c0`, Merge PR #31. GATE-A-01,
02, 07, 08, 09, 11 and 12 are PASS. GATE-A-03, 04, 05, 06 and 10 are FAIL.
Gate A and V3-8 are BLOCKED. The stable workflow is `mvp_v1`; `enhanced_v2`
is not complete.

The current OpenAI-compatible Provider carries `task_name`, `prompt_version`,
schema and selected Evidence, but does not resolve the frozen Legal domain
instructions into the actual request. Real Financial and Business canonical
rows remain draft without independent second review. Legal A--H remain
preselection/draft rows without genuine human primary or second review.

## Project Rules

- AGENTS.md
- docs/PROJECT_SPEC.md
- docs/ARCHITECTURE.md
- docs/DATA_SCHEMA.md
- docs/PROJECT_MASTER_CHECKLIST.md
- docs/V03_DEVELOPMENT_CONTRACT.md
- docs/V03_RISK_RULES.md
- docs/V03_ANNOTATION_GUIDE.md
- docs/V03_GATE_A_CLOSEOUT.md
- docs/V03_LLM_PROVIDER_SPEC.md
- docs/execution/README.md

## Inputs

- docs/V03_LEGAL_PROMPT_SPEC.md
- docs/V03_LEGAL_VERIFIER_RULES.md
- docs/V03_LEGAL_CONTRACT_DELTA.md
- docs/V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md
- docs/V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md
- docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md
- docs/execution/plans/
- docs/execution/reports/
- src/ipo_risk/
- configs/
- scripts/
- app/
- tests/
- tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
- tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv

All inputs must be inspected from repository state. Old Planner summaries are
not more authoritative than committed code, tests, manifests and review
artifacts.

## Allowed Files

- src/ipo_risk/
- configs/
- scripts/
- app/
- tests/
- docs/
- README.md
- ROADMAP.md
- CHANGELOG.md
- .env.example
- pyproject.toml

## Forbidden Files

- data/
- models/
- .env
- .github/
- start.bat
- start.sh

No raw prospectus, generated bulky result, model artifact, credential, user
absolute path or 2025 blind input may enter the diff. Allowed shared boundaries
may change only when the applicable conditional phase is reached and the
public-contract stop condition has not triggered.

## Tasks

### 0. Verify and freeze execution context

- [x] Verify `origin/main` equals the approved base.
- [x] Verify the starting worktree is clean.
- [x] Create `feat/v03-completion-one-shot` from the exact approved base.
- [x] Read the authoritative contracts, prior relevant Plans/reports, current
      implementation, tests and Golden artifacts before editing code.

### 1. Close GATE-A-10 Legal prompt runtime

- [ ] Add a deterministic, version-controlled internal prompt registry or
      resolver without changing `LLMProvider.generate_structured(...)`.
- [ ] Map `shareholder_rights_extract` plus
      `legal_shareholder_rights_v1` to the frozen shareholder-rights instruction.
- [ ] Map `litigation_compliance_extract` plus
      `legal_litigation_compliance_v1` to the frozen litigation/compliance
      instruction.
- [ ] Fail closed for an unknown Legal task/version pair or task/version
      mismatch; never silently use an unversioned generic Legal prompt.
- [ ] Preserve compatible generic non-Legal structured generation.
- [ ] Put the resolved domain instruction into the actual OpenAI-compatible
      request while retaining JSON schema and supplied Evidence.
- [ ] Ensure prompts do not request final score, level, verified status,
      probability, investment advice or facts outside supplied Evidence.
- [ ] Preserve deterministic Mock behavior and safe provider failures.
- [ ] Add network-free unit/contract tests for resolution, mismatch, request
      messages, schema, Evidence and generic compatibility.
- [ ] Update GATE-A-10 status only after all targeted and regression checks pass.

### 2. Audit the human Golden gates

- [ ] Inspect canonical and Legal manifests plus every related review and
      adjudication artifact.
- [ ] For A03, verify genuine independent second review for real Financial rows.
- [ ] For A04, verify genuine independent second review for all three real
      Business rows.
- [ ] For A05, verify genuine human primary review, independent second review
      and Case C adjudication for Legal A--H.
- [ ] For A06, merge only genuinely reviewed Legal rows while preserving
      provenance and review history.
- [ ] Never treat Codex, ChatGPT, AI, system, automation, placeholders or
      `codex_preselection` as a human reviewer.
- [ ] If evidence is missing, create
      `docs/review/V03_REMAINING_HUMAN_GOLDEN_REVIEW_PACKET.md`, keep the human
      gates FAIL, and stop before V3-8.

### 3. Conditional final Gate A audit

- [ ] Proceed only if A01--A12 are all supported by auditable evidence.
- [ ] If genuinely complete, set `GATE_A_OVERALL_STATUS = PASS` and
      `V3-8_START_STATUS = UNBLOCKED` with criterion-by-criterion evidence.
- [ ] Never infer a human-review PASS from tests or automated output.

### 4. Conditional V3-8 specialized verifier system

- [ ] Proceed only after Gate A is genuinely PASS.
- [ ] Route all eight v0.3 risk codes to deterministic specialized verification.
- [ ] Preserve `RiskAgent.analyze(...) -> list[RiskItem]`; Agents never
      self-verify.
- [ ] Enforce Evidence, Calculation, Evidence-ID traceability, finite numeric
      values, period/unit/currency consistency and conflict handling for numeric
      risks.
- [ ] Preserve Legal provisional `medium / 50` and its non-probability metadata.
- [ ] Verify Legal lifecycle, actual/negative/status/remediation/licence rules.
- [ ] Preserve the Business direct-product-sales rule and ambiguity handling.
- [ ] Add complete verifier-state tests without rewriting working Financial
      verification unnecessarily.

### 5. Conditional shared component integration

- [ ] Register and assemble Catalog IPO data, Keyword Retriever, real v0.3
      Financial/Legal/Business Agents, specialized Verifier, Supervisor and
      LLMProvider through ComponentRegistry/DependencyContainer.
- [ ] Keep Market disabled and outside v0.3.
- [ ] Preserve `mock`, `cash_runway`, `disabled`, `mvp_v1` and existing
      interfaces.
- [ ] Add a credential-free real-v0.3 configuration with environment-only
      secret injection.

### 6. Conditional V3-9 Supervisor and enhanced_v2

- [ ] Add a configuration-selectable `enhanced_v2` while preserving `mvp_v1`.
- [ ] Parse once, load profile, run Financial/Legal/Business, collect
      diagnostics, verify, supervise, return a unified result and persist/report
      through existing Service/Repository boundaries.
- [ ] Keep Market Agent/Predictor non-required for v0.3.
- [ ] Isolate professional-component failures and return explicit partial
      diagnostics without inventing risks.
- [ ] Make Supervisor deduplicate, preserve provenance, surface conflicts,
      preserve status/owner, aggregate diagnostics and never invent Evidence or
      recalculate professional metrics.

### 7. Conditional Service integration

- [ ] Run `enhanced_v2` through IPOAnalysisService and DependencyContainer.
- [ ] Preserve `mvp_v1`, persistence, public result type and diagnostics.
- [ ] Add service integration and partial-failure tests.

### 8. Conditional reviewed-Golden evaluation

- [ ] Use only formal `double_reviewed` or `adjudicated` real rows.
- [ ] Do not count draft, preselection, unreviewed or single-reviewed rows.
- [ ] Reuse existing batch/evaluation infrastructure and generate the standard
      small result set outside committed fixtures unless policy requires it.
- [ ] Report actual Recall@3, numeric accuracy, verified precision, complete-run
      rate and crash count; report `FORMAL_GOLDEN_EVAL = NOT_READY` when data is
      insufficient.
- [ ] Never tune with 2025 blind cases or alter thresholds to manufacture PASS.

### 9. Conditional v0.3 UI and report

- [ ] Keep Streamlit service-only and present Financial/Legal/Business risks,
      evidence, calculations, verification, diagnostics and component status.
- [ ] Clearly state that v0.3 rule scores are not calibrated market-decline
      probabilities.
- [ ] Generate evidence-driven sections for verified, needs-review, rejected/
      not-applicable, failures, Evidence, Calculations, diagnostics and limits.
- [ ] Do not add v0.4 market prediction UI or investment recommendations.

### 10. Conditional no-LLM and release hardening

- [ ] Validate deterministic operation with unavailable real LLM and a separate
      Mock configuration, without substituting fake real-provider output.
- [ ] Run full tests, validators, compileall, v0.2 Retriever and 2410 E2E,
      targeted prompt/verifier/container/workflow/service/report/UI/evaluation
      checks, and `git diff --check`.
- [ ] Attempt a clean supported environment rerun; report `NOT_TESTED` with a
      concrete reason if environment/network restrictions prevent it.
- [ ] Synchronize active project documentation only to evidence-supported state.
- [ ] Evaluate every v0.3 release-candidate exit condition without checking an
      unsupported box.

### 11. Produce audit artifacts

- [ ] Create the master Execution Report at the frozen report path.
- [ ] Record every changed path and justify protected-boundary changes.
- [ ] Record Gate A, human review, conditional-phase execution, tests, metrics,
      blind guard, limitations, blockers and exact next action.
- [ ] Create an external temporary final review packet containing the full
      relevant diff/status/validation evidence; do not place it in the repo.
- [ ] Do not stage, commit, push, create PR, merge, tag or release.

## Acceptance Criteria

### Legal prompt runtime

- The frozen Legal instructions are selected deterministically by exact
  `(task_name, prompt_version)`.
- Unknown/mismatched Legal identities fail safely and no generic Legal fallback
  occurs.
- The actual structured request includes domain instruction, JSON schema and
  only supplied Evidence.
- Generic non-Legal calls, Mock behavior, Pydantic validation, retry/security
  behavior and the frozen public Provider signature remain compatible.

### Human Gate integrity

- A03/A04/A05/A06 PASS only with genuine, independent and traceable human
  records.
- Missing human evidence produces a precise row-level review gap packet and
  `V03_COMPLETION_HUMAN_GATE_BLOCKED`.
- V3-8 and every later conditional phase remain unimplemented while Gate A is
  BLOCKED.

### Conditional v0.3 completion

- If and only if Gate A is genuinely PASS: all eight specialized verification
  routes, shared integration, enhanced_v2, failure isolation, Supervisor,
  Service, reviewed-Golden evaluation, UI/report, no-LLM mode and hardening meet
  the material requirements above.
- `mvp_v1`, Mock and 2410.HK remain stable.
- Market models, full Market Agent, calibrated probability and market labels
  are absent.

### Safety and contracts

- No public Parser, Retriever, RiskAgent, Predictor, Evidence, RiskItem or
  LLMProvider contract changes.
- No issuer/stock/page/Evidence-ID production special case, secret, absolute
  path, hidden network dependency, test-only production branch or weakened test.
- No 2025 blind file is opened, parsed, searched, previewed, summarized,
  evaluated or used for tuning.
- No commit, push, PR, merge, tag or release occurs.

## Required Validation

At the applicable execution boundary run at least:

```text
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python -m compileall -q app src scripts
git diff --check
python scripts/check_real_keyword_retriever.py
python scripts/check_real_v02_e2e.py
```

Additionally run focused tests for every changed capability, Plan validation,
scope inspection, Golden manifest integrity, and reviewed-Golden evaluation only
when genuinely reviewed real rows exist. Do not claim PASS for a command that
was not executed.

## Manual Validation

- Inspect the actual provider request messages and verify domain instruction,
  schema and Evidence without logging credentials or external responses.
- Audit every real Golden row's reviewer, second reviewer, status,
  disagreement and adjudication provenance.
- Inspect final production diff for public-contract drift, issuer/page
  special-cases, credentials, absolute paths and 2025 references.
- Verify the final Gate state and release checklist against direct artifacts,
  not summaries.

## Stop Conditions

- If `origin/main` moves from the approved starting SHA before execution, stop
  without rebasing or chasing main.
- If the starting worktree is dirty, stop without stashing/resetting/cleaning.
- If the frozen public `LLMProvider.generate_structured(...)` or another frozen
  public contract must change, return
  `V03_COMPLETION_PLAN_CHANGE_REQUIRED_PUBLIC_CONTRACT`.
- If any required human review is absent, complete only GATE-A-10 and the human
  gap/report artifacts, then return `V03_COMPLETION_HUMAN_GATE_BLOCKED` without
  implementing V3-8 or later phases.
- If a different concrete prerequisite makes progress impossible, return
  `V03_COMPLETION_BLOCKED` with direct evidence.
- Stop if success would require fabricated reviewer identity, fake metric,
  weakened/skipped/xfail test, 2025 blind access, a secret, issuer-specific
  production logic, market-model scope or unrelated refactoring.
- Never automatically commit, push, create/merge a PR, tag or release.

## Expected Deliverables

- `docs/execution/plans/V03_COMPLETION_ONE_SHOT_PLAN.md`
- Deterministic Legal domain prompt registry/resolver and request integration.
- Network-free Legal prompt runtime tests.
- Honest updated Gate A documentation.
- `docs/review/V03_REMAINING_HUMAN_GOLDEN_REVIEW_PACKET.md` when human evidence
  is incomplete.
- Conditional V3-8 through V3-12 implementation only if Gate A is genuinely
  unblocked.
- `docs/execution/reports/V03_COMPLETION_ONE_SHOT_EXECUTION_REPORT.md`
- External `V03_COMPLETION_FINAL_REVIEW_PACKET.md` (or numbered split files).
- Clean evidence that no commit, push, PR, merge, tag, release or 2025 access
  occurred.

## Notes

The one-shot authorization broadens engineering scope but does not override the
human Gate A prerequisite. Tests and automation can validate review artifacts;
they cannot create human review. Market prediction remains v0.4 scope.
