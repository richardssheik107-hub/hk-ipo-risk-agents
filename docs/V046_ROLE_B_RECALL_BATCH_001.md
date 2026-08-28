# v0.4.6 Role-B Recall Batch 001

> Status: **IMPLEMENTED ON FEATURE BRANCH — FIXED-10 RERUN REQUIRED**
>
> Branch: `fix/v046-role-b-recall-batch-001`
>
> Base: `34553ebcd230b34417775359133761b27e49e204`

## 1. Forensic input

The local `forensic_011` report supplied for this batch records:

```text
fixed-10 cases = 10
M1 = 8 / 30 = 26.67%
M2 = 11 / 48 = 22.92%
Candidate Recall@20 = 43.75%
structured-valid rate = 94.29%
```

Proven earliest failures:

| Root cause | M1 units | M2 units |
|---|---:|---:|
| retrieval candidate miss | 6 | 16 |
| parser text missing | 5 | 10 |
| risk absent caused Evidence miss | 0 | 7 |
| deterministic extraction miss | 4 | 0 |
| retrieval ranking / top-K miss | 1 | 1 |

This branch does not reinterpret those counts as additive gains. It implements a
single broad, testable hypothesis: improve the text and candidate substrate
before changing prompts, Gold, the evaluator, or risk thresholds.

## 2. Changes

### Multi-view, page-stable parser

`pymupdf_role_b_recall` keeps one original physical-page chunk and attaches
retrieval-only alternate views:

```text
default text
sorted text
block reading order
word stream
reconstructed financial-table rows
```

A page blank only in the default view is retained from the first non-empty
alternate view. No OCR, Gold anchor, issuer rule, stock code, or page rule is
used.

### Hybrid candidate generation

The opt-in Role-B retriever now combines:

```text
DomainAware V2.1 exact/family lane
+ parser alternate views
+ case-local overlapping-window BM25
+ weighted page-level reciprocal-rank fusion
```

The released keyword behaviour remains unchanged for unknown queries. The
Role-B lane applies to the five Financial risks, Redemption Rights,
litigation/compliance, and the two precommercial-product query intents.

Every returned candidate is mapped back to the original document/chunk/physical
page. Context is capped at 6,000 characters and Evidence IDs remain
deterministic.

### Table-aware deterministic extraction

Both v0.4.6 provider profiles now use:

```text
parser = pymupdf_role_b_recall
financial_extractor = table
retriever = role_b_v046_financial_high_recall
```

The change is opt-in and does not alter the shipped competition UI runtime.

## 3. Expected effects

The batch is designed to improve:

- Parser anchor preservation;
- candidate Recall@20;
- actual Agent top-K consumption;
- Financial table/period/value extraction;
- final Evidence anchor retention;
- Legal/Business access to non-exact but relevant passages.

It does not claim that all recovered candidates become correct risks. Builder,
normalization, reconciliation, Verifier, status, level, and calculation checks
remain unchanged and fail closed.

## 4. Acceptance gate

Run a new identity-bound fixed-10 measurement, for example `forensic_012`, with
fresh journal/config identity.

Accept this batch only when all are true:

```text
Candidate Recall@20 > 43.75%
M1 >= 26.67%
M2 >= 22.92%
no supported risk family regresses without a proven trade-off
structured-valid rate remains >= 90%
no Gold/runtime leakage
Validation remains closed
2025 Blind input/outcome is not used
```

If Candidate Recall improves but M1/M2 do not, the next iteration must use the
new lifecycle trace to isolate extraction, Builder, reconciliation, Verifier, or
Evidence-binding loss. Do not broaden retrieval again without that evidence.

## 5. Governance

Unchanged:

- Existing Gold and evaluator;
- fixed-10 identity;
- official M1/M2 formula;
- Validation one-shot boundary;
- Evidence scope guard;
- deterministic Calculation authority;
- PIT/Blind/secret/licensed-data protections.

The competition target remains ALL 79 Development M1 >= 80% and M2 >= 85%; this
fixed-10 batch is only the first measured remediation step.
