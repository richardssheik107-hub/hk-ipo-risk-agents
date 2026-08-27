# ROLE B — GLM-5.3 REAL-LLM BENCHMARK

## Result

```text
MEASURED_FAIL
```

The governed Development run completed for all ten fixed IPO cases, but it did
not improve the frozen offline baseline and did not meet the competition gates.
This is a measured performance failure, not an execution or data-availability
blocker.

The branch used `origin/main` revision
`279376fc0b36af3984dc960999e3ad7034c20322`. The user authorized at most 60
requests containing only bounded Retriever-selected Evidence from these ten
Development IPOs. Whole PDFs, Gold, 2024 Validation and 2025 Blind were not sent.
The API key was process-only and was not written to a repository file, report,
log, prompt dump or result artifact.

## Frozen execution

```text
Provider:                       Volcengine Ark Coding Plan
API model alias / identity:     glm-5.3
Synthetic structured smoke:     PASS
Development cases completed:    10 / 10
Actual HTTP request attempts:    36 / 60
Structured calls completed:     2 / 30
Structured calls failed:        28 / 30
Cases with >=1 completed call:   1 / 10

2024 Validation opened:          NO
2025 Blind accessed:             NO
```

The 30 Development calls comprise three frozen semantic tasks per IPO. All ten
case pipelines completed because the existing Agents fail closed and retain
their deterministic/offline behavior when a structured model call fails. This
means `10 cases completed` must not be misread as ten cases successfully
analyzed by GLM-5.3: only two structured responses passed the existing schema
contract. No response body was persisted, so the 28 failures are conservatively
reported as structured-call failures rather than attributed to a more specific
cause.

The run was interrupted after six cases and resumed with a strict engineering
guard: identical protocol hash, source revision, model, result identities and
request count were required. Completed cases were not rerun, the synthetic smoke
was not repeated, and the global request counter continued from 24.

## Formal Development metrics

| Metric | Offline governed baseline | GLM-5.3 governed run |
| --- | ---: | ---: |
| Risk Precision | 0.0% | 0.0% |
| Risk Recall | 0.0% | 0.0% |
| Risk F1 | 0.0% | 0.0% |
| Evidence Recall@1 | 20.0% | 20.0% |
| Evidence Recall@3 | 20.0% | 20.0% |
| Evidence Recall@5 | 20.0% | 20.0% |

```text
Risk target >= 80%:       FAIL
Evidence target >= 85%:   FAIL
```

The evaluated Golden contains 11 formally reviewed rows, three expected
verified risks and five Evidence-applicable rows. The run predicted one verified
risk, with zero true positives. The single existing `precommercial_product`
Evidence match remains the same result seen in the offline baseline.

Per-risk Evidence Recall@5:

| Risk | Applicable Gold | Recall@5 |
| --- | ---: | ---: |
| `material_litigation_compliance` | 1 | 0.0% |
| `precommercial_product` | 2 | 50.0% |
| `redemption_rights` | 2 | 0.0% |

Evidence emitted by the completed pipelines remained within the source PDF page
bounds (9/9 for the only verified RiskItem). No whole PDF, Gold label, expected
field, 2024 Validation record or 2025 Blind record entered a model request.

## Interpretation

Connecting an external model was necessary to measure the real provider path,
but it was not sufficient to improve the system. The dominant issue in this run
is structured-call reliability: 28 of 30 real semantic calls did not satisfy the
existing provider/schema contract, so the Agents mostly used their frozen
offline fallback. Consequently, this benchmark does **not** show that GLM-5.3
improves Role-B Legal/Business extraction.

No prompt, schema, Builder, Verifier, Retriever or Agent policy was changed after
observing the result. Any compatibility remediation must be a new Development-
only experiment with a newly frozen protocol; it must not open 2024 Validation
or 2025 Blind and must not present this run as passing.

## Safety, disk and cleanup

```text
Available disk before:          8,022,601,728 bytes
Peak temporary disk:            1,133,293,568 bytes
Available disk after:           about 8,022,585,344 bytes
Temporary PDFs remaining:       0
Temporary year ZIPs remaining:  0
Temporary directory:            CLEAN
Persistent model/index/cache:   NO
Model downloads:                0
Full prompt/response saved:     NO
```

The original outer ZIP was read in place and was not copied, modified or
deleted. At most one annual ZIP and one current PDF existed in the task-owned
temporary directory. The local proxy was restored to its original node after
the run.

## Next decision

Do not open Validation and do not tune against Validation. If Role B continues,
the next narrowly scoped task should diagnose the structured compatibility
failure on synthetic or Development-only bounded Evidence, recording only safe
error categories. It should first determine whether failures are remote request
errors, JSON decoding failures or Pydantic schema-validation failures. Only then
should a maximum-three-variant compatibility experiment be authorized.

The exposed API credential must be rotated before any further external run.
