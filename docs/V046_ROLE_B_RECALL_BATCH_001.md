# v0.4.6 Role-B Recall Batch 001

> Status: **IMPLEMENTATION MERGED — TRACE CONTRACT CORRECTED — FIXED-10 RERUN REQUIRED**
>
> Branch: `fix/v046-role-b-recall-batch-001`
>
> Initial base: `34553ebcd230b34417775359133761b27e49e204`
>
> The branch has since merged the current-main forensic evidence and tooling.

## 1. Forensic input

The original `forensic_011` artifact records:

```text
fixed-10 cases = 10
M1 = 8 / 30 = 26.67%
M2 = 11 / 48 = 22.92%
Parser expected-page preservation = 38 / 48 = 79.17%
Candidate exact-anchor Recall@20 = 21 / 48 = 43.75% (trace-invalid)
structured-plus-scope-valid rate = 33 / 35 = 94.29%
```

The original earliest-failure table was subsequently found to contain a
measurement defect: the runtime risk-pool call records `query_intent` as
`cash_runway`, but the post-run trace join accepted only the two legacy
free-text intents. It discarded all cash-runway candidates and produced the
artificial `0/11` family value. A deterministic no-LLM replay using the same
forensic-base Parser and Retriever established the corrected pre-batch
diagnostic baseline:

```text
cash-runway expected-page Recall@20 = 11 / 11 = 100%
cash-runway exact-anchor Recall@20  =  9 / 11 = 81.82%
overall expected-page Recall@20     = 38 / 48 = 79.17%
overall exact-anchor Recall@20      = 30 / 48 = 62.50%
```

Official `M1=8/30` and `M2=11/48` remain unchanged. The original trace-derived
root-cause table is retained below as historical input, but its cash-runway
candidate-miss rows are not valid causal evidence:

| Root cause | M1 units | M2 units |
|---|---:|---:|
| retrieval candidate miss | 6 | 16 |
| parser text missing | 5 | 10 |
| risk absent caused Evidence miss | 0 | 7 |
| deterministic extraction miss | 4 | 0 |
| retrieval ranking / top-K miss | 1 | 1 |

Additional isolated M1 failures include wrong-period selection, one Legal
abstention, one builder-not-applicable result, one level mismatch, and one final
Evidence-retention miss. The counts are not additive ceilings.

The batch implements one broad, testable hypothesis: improve the text and
candidate substrate before changing prompts, Gold, the evaluator, frozen
thresholds, or Verifier policy.

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
native PyMuPDF view. No OCR, Gold anchor, issuer rule, stock code, case ID, or
page rule is used.

### Hybrid candidate generation

The opt-in Role-B retriever now combines:

```text
DomainAware V2.1 exact/family lane
+ parser alternate views
+ case-local overlapping-window BM25
+ balanced page-level reciprocal-rank fusion
```

The two retrieval lanes use equal RRF weights. A prior weighted implementation
gave the Domain lane weight `2` at depth `60`; consequently even BM25-only rank
1 scored below Domain-only rank 60 and could be truncated from the 60-page
union. The balanced implementation makes a BM25-only rank-1 page enter ahead of
Domain-only rank 2 while still strongly promoting pages found by both lanes. A
regression test pins this property.

The released keyword behaviour remains unchanged for unknown queries. The
Role-B lane applies to the five Financial risks, Redemption Rights,
litigation/compliance, and the precommercial-product query intents.

Every returned candidate is mapped back to the original document/chunk/physical
page. Context is capped at 6,000 characters and Evidence IDs remain
deterministic. The corpus and BM25 index are reused across risk queries within a
case.

### Table-aware deterministic extraction and bounded transport recovery

Both v0.4.6 provider profiles now use:

```text
parser = pymupdf_role_b_recall
financial_extractor = table
retriever = role_b_v046_financial_high_recall
llm_max_retries = 1
profile_version = v046_role_b_ablation_v3_recall_batch_001
```

This lets table/period/value extraction and Legal/Business structured analysis
consume a fuller, page-stable context without changing decision thresholds or
accepting out-of-scope Evidence. The change is opt-in and does not alter the
shipped competition UI runtime.

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

## 4. Engineering validation

The initial implementation produced one real test failure: merged context was
`6001` characters because the newline separator was not included in the budget.
The implementation was corrected to enforce the full 6,000-character bound.

After that correction, and again after merging the latest `main` and frozen
forensic artifacts, the complete repository workflows passed, including:

- unit and integration tests;
- byte compilation;
- project, competition-data, and competition-runtime validators;
- submission-readiness fail-closed smoke;
- Golden manifest and Role-D receipt validation;
- annotation-governance and deterministic-correction checks.

Engineering CI proves contract safety, not M1/M2 improvement.

## 5. Fixed-10 rerun

Run a fresh identity-bound measurement, for example `forensic_012`, with a new
smoke summary and journal/config identity:

```bash
python scripts/check_v046_role_b_structured_smoke.py

python scripts/run_v046_role_b_ablation.py \
  --config configs/experiments/v046_role_b_ai_responses.yaml \
  --run-id forensic_012 \
  --modes all \
  --execute \
  --prospectus-root "$IPO_RISK_PROSPECTUS_ROOT"

python scripts/audit_v046_role_b_forensics.py \
  --run-root reports/v046_role_b/ablation/forensic_012 \
  --prospectus-root "$IPO_RISK_PROSPECTUS_ROOT" \
  --output-dir reports/v046_role_b/forensics/forensic_012
```

Accept this batch only when all are true:

```text
Expected-page Recall@20 >= 79.17%
Exact-anchor Recall@20 >= 62.50%
M1 >= 26.67%
M2 >= 22.92%
no supported risk family regresses without a proven trade-off
structured-valid rate remains >= 90%
no Gold/runtime leakage
Validation remains closed
2025 Blind input/outcome is not used
```

A more useful success target for this broad batch is:

```text
Parser/expected-page preservation remains at least 79.17%
Exact-anchor Recall@20 materially above 62.50%
Cash-runway expected-page Recall@20 remains 11/11
Cash-runway exact-anchor Recall@20 remains at least 9/11
M1 and M2 both improve, not only candidate diagnostics
```

If Candidate Recall improves but M1/M2 do not, the next iteration must use the
new lifecycle trace to isolate extraction, Builder, reconciliation, Verifier, or
Evidence-binding loss. Do not broaden retrieval again without that evidence.

## 6. Governance

Unchanged:

- Existing Gold and evaluator;
- fixed-10 identity;
- official M1/M2 formula;
- Validation one-shot boundary;
- Evidence scope guard;
- deterministic Calculation authority;
- PIT/Blind/secret/licensed-data protections.

The competition target remains ALL 79 Development M1 >= 80% and M2 >= 85%; this
fixed-10 batch is the first measured remediation step, not a competition PASS.
