---
report_id: V03-PRE-HUMAN-CHECKPOINT-AUDIT
audit_base: cb7197558510bb92c454e5ab22c8413fa91147c0
branch: feat/v03-completion-one-shot
audit_status: CHECKPOINT_READY_FOR_PR
public_contract_changed: false
human_review_complete: false
formal_reviewed_golden_ready: false
v3_8_start_status: BLOCKED
---

# v0.3 Pre-Human-Gate Checkpoint Audit

## 1. Scope and baseline

This audit covers all repository changes prepared before mandatory human Golden
review. The audited branch started exactly at
`main@cb7197558510bb92c454e5ab22c8413fa91147c0`. No commit existed ahead of
`origin/main` when the checkpoint audit began.

The implementation closes only GATE-A-10 and records the remaining human work.
It does not start V3-8, specialized shared Verifier routing, `enhanced_v2`,
Supervisor integration, shared Service integration, or any later release phase.

Pre-audit worktree classification:

- one-shot Plan/report: the approved one-shot Plan and its Execution Report;
- GATE-A-10 production: `providers/llm.py`, `providers/mock.py` and the additive
  internal `providers/prompt_registry.py`;
- GATE-A-10 tests: `test_v03_legal_prompt_runtime.py`;
- status documentation: the master checklist, roadmap, Gate closeout and Legal
  Prompt specification;
- human gap evidence: the remaining human Golden review packet;
- unexpected/out-of-scope: none.

Files corrected during this audit were limited to the already-authorized scope:
the frozen Legal instructions now explicitly include `closed` status and explicitly
prohibit final score and investment recommendation; the contract test locks those
semantics; the human packet exposes two additional machine-readable false flags;
and the execution report records the final rerun evidence. The audit report itself
is additive documentation.

## 2. Static architecture audit

```text
PUBLIC_CONTRACT_CHANGED = false
LLM_PROVIDER_SIGNATURE_CHANGED = false
RISK_AGENT_SIGNATURE_CHANGED = false
SCHEMA_CHANGED = false
CONTAINER_CHANGED = false
WORKFLOW_CHANGED = false
SERVICE_CHANGED = false
UI_CHANGED = false
DEPENDENCY_CHANGED = false
```

`LLMProvider.generate_structured(...)` remains the frozen keyword-only contract:

```text
task_name: str
prompt_version: str
evidence: list[Evidence]
response_model: type[StructuredModel]
-> StructuredModel
```

The new resolver is internal and additive. Exact Legal task/version pairs resolve
to version-controlled instructions. A known Legal task/version mismatch fails
before client use with a safe, non-recoverable request error and zero attempts.
Unrelated non-Legal structured calls preserve the generic path.

The real Provider still sends the Pydantic response schema and only the supplied
Evidence payload. The system message now includes the resolved domain instruction.
Existing timeout, bounded retry, JSON parsing, Pydantic validation, error
classification, API-key handling and token metadata code is unchanged.

Mock uses the same Legal identity guard and retains deterministic response-model
validation. It performs no network access.

## 3. Prompt semantic audit

Both frozen Legal instructions require facts to be supported by supplied Evidence
and restrict `evidence_ids` to supplied identifiers.

The shareholder-right instruction preserves:

- historical/current and before/on/after-listing distinctions;
- separate termination and restoration facts;
- null/empty output for incomplete Evidence;
- explicit prohibition on final score, level, verification status and investment
  recommendation.

The litigation/compliance instruction preserves:

- actual matters versus generic future-risk language and explicit negatives;
- historical/current and pending/resolved/settled/closed/remediated status;
- no inferred materiality, amount, regulator, counterparty or case status;
- explicit prohibition on final score, level, verification status and investment
  recommendation.

## 4. Test quality audit

The new contract suite is network-free and verifies actual outbound request
messages through a fake client, not only registry constants. It covers:

- exact deterministic resolution for both Legal task/version pairs;
- wrong version and mismatched task fail-closed before any client request;
- frozen instruction presence in the real Provider system message;
- response schema and supplied Evidence retention in the user payload;
- generic non-Legal compatibility;
- Mock exact-pair behavior and mismatch failure;
- explicit Legal safety-boundary wording.

No valid test was deleted, weakened, skipped or marked xfail.

## 5. Security and data-boundary audit

```text
REAL_CREDENTIAL_IN_DIFF = false
AUTHORIZATION_HEADER_IN_DIFF = false
USER_ABSOLUTE_PATH_IN_DIFF = false
BINARY_OR_CACHE_IN_DIFF = false
ISSUER_PAGE_EVIDENCE_ID_PRODUCTION_SPECIAL_CASE = false
GOLDEN_FIXTURE_CHANGED = false
BLIND_2025_ACCESSED = false
BLIND_2025_USED_FOR_TUNING = false
```

The sole key-like value is `synthetic-test-key` in a network-free contract test.
No `.env`, raw prospectus, generated model/result artifact, local path or external
response entered the diff. Existing 2025 guards were checked through committed
metadata and synthetic tests only; no 2025 prospectus content was opened.

## 6. Human Golden audit

The canonical manifest contains 29 rows: 3 synthetic `double_reviewed` fixtures
and 26 real rows. All 26 real rows remain `draft` and all lack
`second_reviewer`. Of those, 23 Financial rows name `member-3` and 3 Business
rows name `member-5` as first reviewer.

The Legal manifest contains 8 real rows. All 8 remain `draft`, all use
`codex_preselection`, and all lack a second reviewer. `codex_preselection` is not
a human primary review. Case C has no completed human adjudication artifact.

No reviewer identity, review status, annotation value or adjudication was changed
or fabricated. Formal reviewed-Golden metrics remain unavailable.

## 7. Gate result

```text
PASS = GATE-A-01,GATE-A-02,GATE-A-07,GATE-A-08,GATE-A-09,GATE-A-10,GATE-A-11,GATE-A-12
FAIL = GATE-A-03,GATE-A-04,GATE-A-05,GATE-A-06
GATE_A_OVERALL_STATUS = BLOCKED
human_review_complete = false
formal_reviewed_golden_ready = false
V3_8_START_STATUS = BLOCKED
```

Required checkpoint declaration:

```text
PRE_HUMAN_TECHNICAL_CHECKPOINT = PASS
GATE_A_10 = PASS
GATE_A_03 = FAIL
GATE_A_04 = FAIL
GATE_A_05 = FAIL
GATE_A_06 = FAIL
GATE_A_OVERALL_STATUS = BLOCKED
V3_8_START_STATUS = BLOCKED
formal_reviewed_golden_ready = false
2025_blind_accessed = false
```

Technical tests cannot satisfy a human-review criterion. The exact remaining
row-level work is recorded in
`docs/review/V03_REMAINING_HUMAN_GOLDEN_REVIEW_PACKET.md`.

## 8. Validation evidence

- Legal prompt/Provider/Legal regressions: `52 passed`.
- Full suite: `860 passed in 14.54s`.
- Manifest/blind guard tests: `17 passed`.
- `python scripts/validate_project.py`: PASS,
  `status=completed verified=3 pending=1`.
- Competition-data validation: PASS using system Python plus the read-only desktop
  bundled `openpyxl` package path.
- `python -m compileall -q app src`: PASS.
- Execution Plan validator: `plan_validation=valid`.
- Scope Guard: `execution_scope=valid`.
- `git diff --check`: PASS.
- 2410.HK Service E2E: 706 parsed chunks, 0 parser errors, Evidence pages
  563/562, 2.76 months, `verified`, `90.0 / critical`.
- Retriever regression: pages 563 and 562 rank first; decoys 665 and 683 are
  absent.

## 9. Independent clean environment

```text
INDEPENDENT_ENV_RERUN = NOT_TESTED
```

An isolated rerun was not practical under the repository rule that forbids
recursive cleanup: creating a disposable virtual environment would leave an
unmanaged directory that this task is not authorized to remove recursively.
The desktop bundled interpreter also lacks PyMuPDF, while system Python lacks
`openpyxl`; the read-only combined package path was used only for the competition
validator and is not claimed as a clean-environment rerun.

## 10. Checkpoint conclusion

```text
CHECKPOINT_TECHNICAL_AUDIT = PASS
CHECKPOINT_READY_FOR_PR = true
HUMAN_GATE = BLOCKED
V3_8_START_STATUS = BLOCKED
```

The repository is suitable for a pre-human-Gate checkpoint PR. Merging or starting
V3-8 requires separate authorization and completion of GATE-A-03 through A-06.
The next human action is genuine Financial and Business independent second review,
plus Legal primary review, independent second review and Case C adjudication. The
Planner's next action is remote review of the checkpoint commit, PR diff and CI;
this execution does not authorize merge.
