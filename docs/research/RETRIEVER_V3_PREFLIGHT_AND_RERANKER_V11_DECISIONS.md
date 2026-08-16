# Retriever V3 Preflight Findings and LLM Reranker V1.1 Design

## Status

`PHASE = R3-A1 WEB PREFLIGHT / RERANKER V1.1 DESIGN ONLY`

This document records the work that can be completed without the original 60 prospectus PDFs and without new LLM calls. It does not tune production retrieval and does not unlock the 10-case locked implementation-validation split.

## 1. Verified 60-case Retrieval Gold inventory

GitHub Actions preflight on `agent/expert-annotation-phase2c` verified:

- cases: **60**
- total Evidence rows: **823**
- Required Evidence rows: **669**
- development cases: **50**
- locked implementation-validation cases: **10**
- development Evidence rows: **689**
- development Required Evidence rows: **558**
- pass1/audit mutation during preflight: **none**
- production Retriever modification: **false**
- LLM calls: **0**

The locked split remains an engineering/research lock, not a strict external blind claim. Locked Evidence text is not exported by preflight and locked metrics require an explicit unlock flag.

## 2. Development Evidence pattern snapshot

| Risk | Evidence | Required | Dominant authority pattern | Table-like rate |
| --- | ---: | ---: | --- | ---: |
| cash_runway | 105 | 98 | accountants report 94/105 | 89.52% |
| continuous_loss | 53 | 52 | accountants report 47/53 | 84.91% |
| revenue_growth | 58 | 53 | accountants report 45/58 | 87.93% |
| customer_concentration | 88 | 77 | business section 65/88 | 87.50% |
| supplier_concentration | 78 | 66 | business section 71/78 | 91.03% |
| redemption_rights | 95 | 65 | pre-IPO investment 45/95; corporate structure 18/95 | 28.42% |
| material_litigation_compliance | 128 | 83 | legal disclosure 114/128 | 15.62% |
| precommercial_product | 84 | 64 | business section 49/84; accountants report 27/84 | 55.95% |

These are **Gold-distribution diagnostics**, not retrieval-performance results.

### Research implications that can already be frozen

1. A single universal recall strategy is unlikely to be optimal across all eight risks.
2. Table-aware/microchunk hypotheses deserve explicit testing for the five financial/concentration risks because their Gold is strongly table-like.
3. Legal recall should not be optimized primarily through table handling; authority/status semantics and lexical/semantic coverage are more plausible bottlenecks.
4. `precommercial_product` is intrinsically cross-section: business/product status and financial/product-sales evidence frequently live in different authority classes.
5. Source authority should be a feature/routing signal, not a hard filter. Valid required evidence can appear outside the dominant authority.
6. No BM25, dense, microchunk or authority lane should be promoted before the frozen 50-case PDF baseline identifies actual candidate-coverage misses.

## 3. Retriever V3 feature inventory for later LTR

The existing Retriever family already exposes a large deterministic feature set. Future Learning-to-Rank work should reuse it rather than replace it.

### V1-derived features

- exact query hit
- alias hit count
- domain positive/negative context
- preferred/discouraged section text signal
- financial-table heuristic
- structured-table-row signal
- statement-neighborhood context
- summary/note/negative context
- deterministic relevance score

### V2-derived features

- query hit provenance
- first/second round
- neighbor provenance
- missing completeness groups
- fusion position/score
- matched query multiplicity

### V2.1-derived features

- query-family identity
- specificity tier
- family-capped RRF contribution
- query-family multiplicity
- V1 head anchor
- neighbor-only / round2-only flags
- Legal boilerplate flag
- final candidate tier

### Evaluation-only/future-lane features

- predicted source authority
- numeric density
- percentage/currency/year signals
- table/microchunk provenance
- future BM25 rank/score
- future dense rank/score

No company, stock code, document ID, physical Gold page, Evidence ID or outcome variable may be used as a production ranking feature.

## 4. Hard-negative governance

R3-A1 will export Top-5/20/50 pages that are not selected Gold for a `case × risk` as **sampled hard negatives**.

They are not automatically formal semantic negatives. A non-Gold page may still contain useful but redundant evidence. Before supervised LTR promotion, the training policy must distinguish:

- Gold positive
- sampled hard negative
- adjudicated true negative (if later created)

This prevents treating expert selection sparsity as proof of irrelevance.

## 5. LLM Reranker V1.1: problem statement

Revision 4 established positive semantic ordering but poor structured-output reliability:

- official tasks: 80
- LLM completed: 65
- fallback: 15
- fallback rate: **18.75%**
- Stage1 Union Required@5: 42.24%
- LLM Required@5: 50.86%
- Stage1 Union MRR: 0.2690
- LLM MRR: 0.3304

The current structured contract asks the model to return one `LLMCandidateJudgmentBundle` containing judgments for the full candidate batch. Deterministic validation then requires exact candidate-ID coverage and valid facet enums. One malformed/missing/duplicate member can therefore invalidate the whole batch and force Stage1 fallback.

V1.1 should improve **engineering reliability without changing the semantic role of the LLM**: the model judges evidence quality; Python remains responsible for final deterministic ordering.

## 6. Reranker V1.1 design requirements

### 6.1 Preserve semantic contract

The LLM must continue to judge only:

- risk relevance
- evidence specificity
- source authority
- evidence role
- boilerplate
- current-status relevance
- whether the evidence supports risk assessment
- completeness facets
- confidence/reason

It must not decide the issuer's final risk, assign the final risk score, or directly emit the final rank.

### 6.2 Remove batch-atomic failure as the default failure unit

Candidate V1.1 architecture:

```text
Stage1 Top20
    ↓
stable candidate IDs
    ↓
small deterministic micro-batches
    ↓
validate each returned judgment independently
    ↓
keep valid judgments
    ↓
missing/invalid candidate → candidate-level deterministic fallback
    ↓
Python tier ordering
```

The exact micro-batch size must be benchmarked rather than guessed. Candidate sizes such as 5 or 10 may be compared, but no value is promoted by this document.

### 6.3 Partial recovery

A failure affecting one candidate must not automatically discard validated judgments for unrelated candidates. Recovery rules must be deterministic and auditable:

- valid candidate judgment: retain
- missing candidate: Stage1 fallback metadata for that candidate
- duplicate candidate ID: reject duplicates and fall back for the affected ID
- unknown candidate ID: ignore for ranking and record telemetry
- unknown completeness facet: strip nothing silently; mark that judgment invalid and fall back for that candidate
- provider/transport failure for an entire micro-batch: fallback only that micro-batch

### 6.4 Sanitized telemetry

Persist no raw provider response or credentials. Persist enough sanitized diagnostics to reproduce reliability statistics:

- task/case/risk
- candidate-set hash
- micro-batch index and size
- attempt count
- expected/actual candidate count
- missing/unknown/duplicate candidate IDs
- Pydantic validation error paths
- unknown facet counts
- provider failure class
- candidate-level fallback count
- validated-judgment count
- final aggregate output hash

### 6.5 Stable caching and freeze

A formal run must freeze:

1. candidate pool
2. prompt/schema version
3. micro-batch partition
4. model/provider identity
5. validated judgment cache
6. fallback records

Gold evaluation occurs only after those artifacts are frozen.

## 7. Reranker V1.1 reliability gates

The next reranker experiment should report semantic value and engineering reliability separately.

Minimum required reliability metrics:

- task-level complete success rate
- candidate-level judgment success rate
- candidate-level fallback rate
- micro-batch failure rate
- coverage mismatch rate
- schema/Pydantic failure rate
- retry count distribution

A working development target is to reduce candidate-level fallback to a low single-digit percentage while preserving the semantic gains of Revision 4. This is a development gate, not a claimed result.

Do not compare V1.1 semantic performance until its candidate input set is frozen. If Retriever V3 changes Stage1 coverage, V1.1 must be evaluated on that newly frozen candidate distribution rather than directly reusing the old 10-case numeric result as if it were the same experiment.

## 8. Work intentionally deferred until PDFs / execution capacity are available

The web preflight cannot truthfully produce the following without the original prospectus PDFs:

- 50-case V1/V2/V2.1 Recall@K
- V1∪V2∪V2.1 candidate-coverage ceiling
- real failure-taxonomy counts
- real hard-negative pages/excerpts
- evidence preservation vs parser on all 50 development cases
- BM25/microchunk/dense lane gains
- LTR training/CV metrics

Those are execution tasks, not documentation gaps. The infrastructure is now designed so they can be produced by a single frozen development run once exact PDFs are supplied by catalog SHA-256.
