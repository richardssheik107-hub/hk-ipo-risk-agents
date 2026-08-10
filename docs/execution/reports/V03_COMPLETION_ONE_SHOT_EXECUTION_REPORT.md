---
plan_id: V03-COMPLETION-ONE-SHOT
plan_revision: 1
execution_status: HUMAN_GATE_BLOCKED
base_commit: cb7197558510bb92c454e5ab22c8413fa91147c0
start_head: cb7197558510bb92c454e5ab22c8413fa91147c0
end_head: cb7197558510bb92c454e5ab22c8413fa91147c0
branch: feat/v03-completion-one-shot
executor: codex
---

# v0.3 One-Shot Completion Execution Report

## 1. Starting main SHA

`origin/main@cb7197558510bb92c454e5ab22c8413fa91147c0` was fetched and
verified before execution. The starting worktree was clean.

## 2. Branch

`feat/v03-completion-one-shot` was created directly from the approved SHA.
No work was performed on `main`.

## 3. Plan compliance

The master Plan was created at its frozen path, validated as `APPROVED`, and
executed without commit, push, PR, merge, tag or release. The human Gate stop
condition triggered after technical GATE-A-10 closure, so V3-8 and all
dependent phases were not implemented.

## 4. Files created

- `docs/execution/plans/V03_COMPLETION_ONE_SHOT_PLAN.md`
- `docs/execution/reports/V03_COMPLETION_ONE_SHOT_EXECUTION_REPORT.md`
- `docs/review/V03_REMAINING_HUMAN_GOLDEN_REVIEW_PACKET.md`
- `src/ipo_risk/providers/prompt_registry.py`
- `tests/contract/test_v03_legal_prompt_runtime.py`

## 5. Files modified

- `docs/PROJECT_MASTER_CHECKLIST.md`
- `docs/ROADMAP.md`
- `docs/V03_GATE_A_CLOSEOUT.md`
- `docs/V03_LEGAL_PROMPT_SPEC.md`
- `src/ipo_risk/providers/llm.py`
- `src/ipo_risk/providers/mock.py`

No Golden CSV, Agent, Schema, Retriever, Container, Workflow, Service, UI,
configuration, dependency or 2025 artifact was modified.

## 6. Public contract impact

```text
PUBLIC_CONTRACT_CHANGED = false
LLM_PROVIDER_SIGNATURE_CHANGED = false
V03_CONTRACT_VERSION = v03_contract_v1
```

The internal prompt resolver is additive. Parser, Retriever, RiskAgent,
Predictor, Evidence, RiskItem and LLMProvider public signatures are unchanged.

## 7. GATE-A-10 result

```text
GATE_A_10 = PASS
LEGAL_DOMAIN_PROMPT_RUNTIME_STATUS = INTEGRATED
```

Exact mappings now resolve:

- `shareholder_rights_extract` + `legal_shareholder_rights_v1`;
- `litigation_compliance_extract` +
  `legal_litigation_compliance_v1`.

The frozen instructions are included in the actual OpenAI-compatible system
message. Schema and supplied Evidence remain in the user payload. A known Legal
task with the wrong version, or a known Legal version with the wrong task,
fails before any client request. Generic non-Legal structured requests retain
the original generic system constraint. Mock uses the same Legal identity guard
and retains deterministic configured payload validation.

## 8. Human Golden Gate audit

Direct CSV evidence proves that the required human work is incomplete:

- canonical manifest: 29 rows; 3 synthetic `double_reviewed`; 26 real `draft`;
  all 26 real rows lack `second_reviewer`;
- Financial: 23 real rows, first reviewer `member-3`, no second reviewer;
- Business: 3 real rows, first reviewer `member-5`, no second reviewer;
- Legal: 8 rows, reviewer `codex_preselection`, no human primary reviewer, no
  second reviewer, all `draft`;
- Case C has no completed human adjudication artifact;
- reviewed Legal rows are therefore not ready for canonical merge.

The row-level evidence and required actions are recorded in
`docs/review/V03_REMAINING_HUMAN_GOLDEN_REVIEW_PACKET.md`. No reviewer name,
review status, annotation value or adjudication was fabricated.

## 9. Gate A final result

```text
PASS = A01,A02,A07,A08,A09,A10,A11,A12
FAIL = A03,A04,A05,A06
GATE_A_OVERALL_STATUS = BLOCKED
V3-8_START_STATUS = BLOCKED
```

Tests do not satisfy a human-review criterion.

## 10. Specialized Verifier result

`NOT_EXECUTED_HUMAN_GATE_BLOCKED`. Existing standalone Financial and Legal
domain verifiers were not rewritten or integrated into a new shared router.

## 11. Shared Component integration

`NOT_EXECUTED_HUMAN_GATE_BLOCKED`. Existing shared Container/Registry remains
unchanged.

## 12. enhanced_v2 result

`NOT_IMPLEMENTED_HUMAN_GATE_BLOCKED`. Stable `mvp_v1` remains the only shared
workflow implemented by this execution.

## 13. Supervisor result

`NOT_EXECUTED_HUMAN_GATE_BLOCKED`. Existing `RuleSupervisor` remains unchanged.

## 14. Service result

`NOT_EXECUTED_HUMAN_GATE_BLOCKED`. `IPOAnalysisService` remains unchanged.

## 15. Golden evaluation

```text
FORMAL_REVIEWED_GOLDEN_EVALUATION = NOT_READY
REVIEWED_GOLDEN_RECALL_AT_3 = NOT_READY
DETERMINISTIC_NUMERIC_ACCURACY = NOT_READY
VERIFIED_PRECISION = NOT_READY
GOLDEN_COMPLETE_RUN_RATE = NOT_READY
UNEXPECTED_CRASH_COUNT = NOT_READY
```

Draft, preselection, unreviewed, single-reviewed and synthetic rows were not
counted as formal real-Golden metrics. Historical GATE-A-09 development A--H
Top-3 remains 6/8 (75%), but is not presented as formal reviewed-Golden
Recall@3.

## 16. UI and report

`NOT_EXECUTED_HUMAN_GATE_BLOCKED`. Existing Streamlit and Mock report behavior
remain unchanged. No market prediction or calibrated-probability UI was added.

## 17. No-LLM behavior

Existing unavailable/Mock Provider and deterministic regressions passed as part
of the full suite. This execution did not add fake real-provider output. The
new prompt guard is network-free and deterministic.

## 18. v0.2 regression

PASS:

- parsed pages/chunks: 706;
- parser errors: 0;
- Evidence pages: 563 / 562, both ranked first;
- cash runway: 2.76 months;
- verification: `verified`;
- prediction: `90.0 / critical`;
- legal/constitution decoy pages 665 and 683: not matched.

## 19. Full test results

- Legal prompt runtime + Provider/Legal regressions: `52 passed`.
- Full suite: `860 passed in 14.54s` on the final reviewed prompt text.
- `python scripts/validate_project.py`: PASS,
  `status=completed verified=3 pending=1`.
- Golden manifest integrity: PASS.
- Manifest/blind guard tests: `17 passed`.
- `python -m compileall -q app src scripts`: PASS.
- `python scripts/check_real_keyword_retriever.py`: PASS.
- `python scripts/check_real_v02_e2e.py`: PASS.
- Scope Guard: `execution_scope=valid`.
- `git diff --check`: PASS.
- Competition-data validation: PASS using system Python plus the desktop
  bundled `openpyxl` package path; the first plain-system invocation exposed
  missing `openpyxl`, and the bundled interpreter alone exposed missing
  `fitz`. No dependency was installed or changed.

## 20. Clean-environment rerun

```text
INDEPENDENT_ENV_RERUN = NOT_TESTED
```

The conditional release-hardening phase was not reached because the mandatory
human Gate failed. A separate bundled interpreter was inspected but lacked
PyMuPDF, while system Python lacked openpyxl. The combined read-only package
path was sufficient for competition-data validation but is not claimed as an
independent clean-environment rerun.

## 21. Blind guard

```text
BLIND_2025_ACCESSED = false
BLIND_2025_PARSED = false
BLIND_2025_RETRIEVED = false
BLIND_2025_USED_FOR_TUNING = false
```

Only committed manifests, synthetic tests and the existing 2410.HK v0.2 local
fixture were used. No 2025 prospectus or derived blind label was opened,
searched, previewed, summarized or evaluated.

## 22. v0.3 exit checklist

- [x] Financial real standalone Agent available
- [x] Legal real standalone Agent available
- [x] Business real standalone Agent available
- [x] Eight v0.3 risk codes registered
- [ ] At least five formal reviewed real Golden cases
- [x] Contract requires Evidence for all formal risks
- [x] Contract requires Calculation for numeric risks
- [ ] Specialized shared Verifier operational
- [ ] Supervisor dedupe/conflict/failure degradation operational in enhanced_v2
- [ ] enhanced_v2 configurable and runnable
- [x] Batch runner/evaluator infrastructure available
- [ ] Streamlit multi-Agent enhanced_v2 display operational
- [x] mvp_v1 preserved
- [x] Mock preserved
- [x] 2410.HK regression preserved
- [x] Deterministic/unavailable-LLM regressions passed
- [ ] Reviewed Golden Evidence Recall@3 at least 90%
- [ ] Reviewed Golden deterministic numeric accuracy at least 95%
- [ ] Reviewed Golden verified precision at least 90%
- [ ] Reviewed Golden complete run rate 100%
- [ ] Reviewed Golden unexpected crash count 0
- [x] 2025 blind untouched
- [ ] Independent clean-environment rerun passed

## 23. Known limitations

- Human Golden primary/second review and Case C adjudication are not engineering
  tasks Codex can complete.
- Formal real-Golden metrics cannot be calculated honestly.
- Shared specialized verifier routing, integration, enhanced_v2, v0.3 UI/report
  and release hardening remain blocked by the mandatory human Gate.
- Legal prompts have network-free request-boundary coverage; no live external
  credentialed smoke was run or required.

## 24. Unresolved blockers

- GATE-A-03: 23 real Financial rows need independent second review.
- GATE-A-04: three real Business rows need independent second review.
- GATE-A-05: Legal A--H need genuine human primary and independent second
  review; Case C requires adjudication; A/E require severity reconciliation.
- GATE-A-06: reviewed Legal rows cannot be merged until A05 is complete.

## 25. Exact next action

Assign real human reviewers under the frozen annotation guide, complete and
record A03/A04/A05 including Case C adjudication, then have the data-governance
owner validate provenance and mechanically merge only approved Legal rows for
A06. After those artifacts are committed and audited, rerun the final Gate A
audit before authorizing V3-8.

## Final status

```text
V03_COMPLETION_HUMAN_GATE_BLOCKED
NO_COMMIT = true
NO_PUSH = true
NO_PR = true
NO_MERGE = true
NO_TAG_OR_RELEASE = true
```
