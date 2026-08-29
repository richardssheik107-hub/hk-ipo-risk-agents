# Role-B v0.4.6 — Period Candidate Batch 006

## Decision

```text
BATCH_006 = REJECTED_NO_ACTIVE_TARGET_UNITS
base = ea46cb2a8e1923225e783640c418e0829de55225
production_change = none
```

The controller ranked `period_candidate_generation` using the Batch 003 audit.
After Batch 005 was merged, the same read-only audit was rerun against the
canonical fixed-journal output. No unit remained classified as
`period_candidate_missing`, and no selector bug was proven. A production patch
would therefore have targeted stale evidence rather than a current failure.

## Current Development-only audit

```text
units = 22
correct = 8
parser_text_missing = 6
deterministic_fact_missing = 6
numeric_extraction_miss = 1
conflict_fail_closed = 1
period_candidate_missing = 0
proven_selector_bug = 0
network_calls = 0
runtime Gold = false
Validation opened = false
2025 Blind accessed = false
```

The audit did not persist raw Gold text or prospectus text. Existing Gold,
evaluator, fixed-10, production code, Retriever, Parser, Prompt, provider/model,
and frozen Role-D artifacts were unchanged.

## Next root

The largest remaining first-failure class is `parser_text_missing` (6 units).
The next iteration may investigate only a bounded, issuer-agnostic preservation
defect. A broad Parser rewrite remains out of scope. If the six units do not
share one narrow deterministic defect, the root must be deferred rather than
forcing a generalized rewrite.
