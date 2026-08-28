# HK IPO LLM Pipeline Root Cause and Controlled A/B Report

Date: 2026-08-28  
Experiment: `EXP-RTR-HYBRID-BM25-001`  
Decision: **KEEP** the selective deterministic retrieval change; do not change prompt/model without a runnable LLM baseline.

## CURRENT PIPELINE MAP

```text
Local PDF path
  -> PyMuPDF parser (one physical page = one DocumentChunk; section=unknown)
  -> shared DocumentChunk list
  -> Financial Agent
       -> Keyword / selective case-local BM25 retrieval
       -> deterministic extraction + calculation + normalization
  -> Legal Agent
       -> Keyword retrieval (BM25 disabled for litigation due development regression)
       -> bounded structured LLM semantics, deterministic failure isolation
  -> Business Agent
       -> Keyword / selective case-local BM25 retrieval
       -> deterministic extraction
       -> bounded structured LLM cross-check, deterministic fallback
  -> specialized Verifier
  -> deterministic V03 Supervisor (dedupe/evidence union; verified items only)
  -> Rule + governed Market + optional frozen Model channels
  -> deterministic conflict detection + one targeted re-check
  -> LLM Final Supervisor synthesis with deterministic fallback
       (cannot mint or mutate RiskItem/Evidence/calculation)
  -> Report + Agent Trace + Human Review
  -> separate Existing-Gold M1/M2 evaluator
```

The production parser still accepts a local path. The competition ZIP was inspected through nested `zipfile.ZipFile` streams only; it was never extracted. No bulk run was attempted because the current fixed-10 prospectus root and LLM credentials are absent.

## A. Root Cause Analysis

### P0 — Retrieval ceiling, not model intelligence

The production registry exposed only `keyword`; the already validated Retriever V3 BM25/Table/LTR work remained research-only. In the historical LLM reranker top-5 miss cohort, 47/57 misses (82.46%) were candidate-coverage misses. A correct answer outside the candidate pool cannot be recovered by a reranker or extractor.

### P0 — Information is discarded before the LLM

`KeywordDocumentRetriever` sends approximately 900 characters around one best lexical match (`-450/+450`). It provides neither previous/next page nor structured table title/header/row/footnote. The provider serializes Evidence identity, page, section and text, but omits Evidence metadata. Because the default parser emits `section="unknown"`, section authority is also weak. The observed `truncated=false` rate in reranker artifacts is misleading: text had already been truncated upstream.

### P1 — Research reranker output is batch-atomic and too dense

The reranker pilot averaged 16.7 candidates/request and 37.7 KB request JSON (maximum 62.3 KB). Each candidate judgment has 11 properties, 10 required fields and 21 enum values across the schema. One missing/duplicate candidate, invalid enum or validation error invalidates the bundle. Of 80 requests, 15 failed (18.75% fallback): 13 response-validation and 2 validation failures. Production Legal/Business calls are independently failure-isolated; this atomic problem belongs to the optional research reranker, not every production LLM call.

### P1 — Ranking gains hide risk-family regressions

Full LTR improved aggregate metrics but regressed customer concentration and material litigation/compliance on locked evaluation. A uniform “turn on the learned ranker everywhere” policy would damage known strong lanes. The retained adapter therefore keeps cash runway and material litigation/compliance on keyword retrieval.

### P2 — Current runtime evidence is incomplete

The repository does not contain the documented `reports/v045_role_b/results` fixed-10 outputs, the prospectus-root environment variable, or usable LLM configuration. Consequently current structured-output success, token/latency, end-to-end RiskItem accuracy, M1 and M2 cannot be reproduced. Historical reports are evidence, but are not presented as a new current run.

### P3 — Supervisor is not the observed corruption source

`V03Supervisor` keeps the highest-scoring same-code/category item and unions Evidence. `LLMFinalSupervisor` produces synthesis/trace metadata and cannot mutate verified RiskItems, calculations or Evidence IDs. No code evidence supports the hypothesis that the current Final Supervisor overwrites correct Financial results.

## B. Baseline

Controlled dataset: frozen Retriever V3 50-case **development** feature table, 625 positive evidence rows (503 required). Locked cases were rejected by the evaluator and were not reopened for tuning.

| Metric | Before |
|---|---:|
| Candidate Oracle@20 | 59.68% |
| Candidate Oracle@50 | 67.68% |
| Recall@5 | 47.68% |
| Recall@10 | 53.28% |
| Recall@20 | 59.68% |
| Recall@50 | 67.68% |
| MRR | 0.3228 |
| Required@5 | 50.50% |
| Required@20 | 61.83% |
| LLM structured success | Not available — no configured provider/current run |
| LLM parse/validation/retry/token/latency | Not available — no configured provider/current run |
| M1 | Not available — fixed-10 predictions/results absent |
| M2 | Not available — fixed-10 predictions/results absent |

Historical reliability reference (not a new baseline): reranker completed 65/80 requests; fallback 15/80 = 18.75%.

## C. Changes

| File | Function / area | Reason | Change |
|---|---|---|---|
| `src/ipo_risk/retrieval/hybrid_bm25.py` | `HybridBM25DocumentRetriever` | Production could not consume validated BM25 | Added deterministic keyword + frozen BM25-B equal-RRF adapter, keyword tie-break, Evidence identity preservation and honest fallback |
| same | `_KEYWORD_ONLY_RISKS` | Preserve strong lanes | Cash runway and litigation/compliance remain keyword-only after development top-5/MRR regressions |
| same | `_index_for` | Avoid repeated index builds | At most one active document index in memory; new document replaces it; no disk index/cache |
| `src/ipo_risk/core/container.py` | `default_registry` | Runtime wiring | Registered additive `hybrid_bm25` retriever |
| `configs/v045_competition_{offline,ai}.yaml` | retriever selection | Fair offline-vs-AI comparison | Both modes now use the identical deterministic candidate policy |
| `scripts/evaluate_hybrid_bm25_adapter.py` | frozen development A/B | Reproducibility and leakage guard | Recomputes metrics from frozen features; rejects locked-case inclusion; reads zero PDFs and makes zero LLM calls |
| tests | unit/contract/evaluation | Boundary protection | Added semantic recovery, receivable-vs-revenue, fallback, cache scope, registry/config and frozen-split A/B tests |

No model, prompt, Financial calculation, ontology, verifier or supervisor rule was changed.

## D. Results

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Candidate Oracle@20 | 59.68% | 77.12% | +17.44 pp |
| Candidate Oracle@50 | 67.68% | 89.60% | +21.92 pp |
| Recall@5 | 47.68% | 52.96% | +5.28 pp |
| Recall@10 | 53.28% | 63.20% | +9.92 pp |
| Recall@20 | 59.68% | 73.28% | +13.60 pp |
| Recall@50 | 67.68% | 88.48% | +20.80 pp |
| MRR | 0.3228 | 0.3773 | +0.0545 |
| Required@5 | 50.50% | 56.66% | +6.16 pp |
| Required@20 | 61.83% | 75.75% | +13.92 pp |
| Retrieval misses@20 | 252 | 167 | -85 |
| LLM fallback rate | Not available | Not available | No current LLM run |
| M1 | Not available | Not available | Missing fixed-10 predictions/results |
| M2 | Not available | Not available | Missing fixed-10 predictions/results |

Smoke test: the existing local 706-page PDF parsed to 706 chunks without disk output. Evidence identities remained valid. Six revenue aliases took 12.55 s on keyword and 13.52 s on hybrid (+0.97 s total); the one-active-document memory index prevents repeated construction and creates no persistent cache.

Verification: 1,699 unit/contract tests passed after the final production change; focused adapter/evaluation tests also passed.

## E. Failure Breakdown

Historical LLM top-5 miss cohort (57 misses):

| Failure type | Count | Percentage | Impact |
|---|---:|---:|---|
| RETRIEVAL_MISS | 47 | 82.46% | P0 — answer absent from candidate pool |
| BATCH_FALLBACK / STRUCTURED_OUTPUT_ERROR | 4 | 7.02% | P1 — no LLM ranking applied |
| LLM_RANKING_ERROR | 3 | 5.26% | P1 — candidate present but demoted |
| MULTIPAGE_MISS | 3 | 5.26% | P1 — disclosure bundle incomplete |

Retriever development A/B:

| Failure type | Before | After |
|---|---:|---:|
| RETRIEVAL_MISS at rank 20 | 252 | 167 |
| All other taxonomy categories | Not available | Not available |

Additional observed but not safely countable from current artifacts: `EVIDENCE_CONTEXT_INCOMPLETE`, `TABLE_RETRIEVAL_MISS`, `NEIGHBOR_PAGE_MISS`, `SECTION_AUTHORITY_MISS`, `PERIOD_ERROR`, `DENOMINATOR_ERROR`, `SCHEMA_VALIDATION_ERROR`. They remain separate from `UNKNOWN`; no counts were invented.

Top five root causes are: candidate coverage miss; incomplete pre-LLM context; batch-atomic structured validation; risk-family ranking regressions hidden by aggregate scores; unavailable current fixed-10/LLM runtime evidence.

## F. Regressions

- `ipo_2020_08489`: Recall@20 64.29% -> 57.14% (-7.14 pp), attributable to one `revenue_growth` evidence page. This case is disclosed, not hidden.
- Cash runway hybrid top-5 would have regressed 82.11% -> 77.89%; the change was **not retained** for that risk.
- Material litigation/compliance hybrid top-5 and MRR would have regressed; the change was **not retained** for that risk.
- No aggregate Required@5, Recall@20 or MRR regression was observed in the retained development policy.

## G. Disk Usage

- Entire ZIP extracted: **No**.
- ZIP PDFs copied: **No**.
- ZIP modified: **No**; size remains 6,741,739,792 bytes.
- Persistent PDF/OCR/embedding/BM25 cache: **None**.
- `__pycache__` directories: 0; `.pytest_cache`: absent.
- New small code/test/audit/experiment files, including this report: 2,800,806 bytes total.
- Largest new file: `reports/v045_role_b/existing_gold_evaluable_manifest.json`, 2,010,669 bytes.
- Current D: free space at final audit: 8,015,118,336 bytes (7.46 GiB).

ZIP inventory (central-directory/stream inspection only): 29 outer entries; six real nested year ZIPs; 565 prospectus PDFs inside them; three real data-dictionary PDFs; three real CSVs; one XLSX. Inner PDFs total 6,487,199,980 compressed bytes and 7,776,164,822 uncompressed bytes. No extraction was required to obtain these counts.

## H. Recommendations

1. Restore the governed fixed-10 prospectus root and current prediction/result directory, then run offline and AI with the now-identical candidate pool. This is required before claiming M1/M2 improvement.
2. Build an explicit dynamic EvidencePack as a separate experiment: target + paragraph context for prose; title/header/row/footnote for tables; bounded neighbor-page context for multipage evidence. Measure denominator/period errors before retaining it.
3. Replace research reranker bundle validation with per-candidate salvage and targeted retry, then rerun the same 80-request reliability set. Target fallback reduction from the historical 18.75% without changing model, candidate pool or evaluator.

Do not run model/prompt A/B until steps 1–3 yield a stable, logged baseline. Deterministic calculation, period/unit normalization, concentration denominator checks, canonicalization, deduplication and verifier authority should remain outside the LLM.
