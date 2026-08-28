# FIXED-10 BASELINE AND METRIC RECONCILIATION

Date: 2026-08-28  
Scope: measurement / reconciliation / baseline restoration only  
Production algorithm changed: **NO**

## A. Fixed-10 Recovery

| Item | Result |
|---|---|
| Status | **PARTIALLY RECOVERED**: governed manifest, Gold, evaluator and offline scoring work; exact historical real-LLM predictions are unavailable |
| Manifest | `reports/v045_role_b/fixed10_development_subset.json` |
| Cases | 10 Development cases; subset hash `5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a` |
| Gold | Existing-Gold manifest hash `fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c` |
| Historical prediction source | Not recoverable in the current workspace, the older `D:\Multi-Project\hk-ipo-risk-agents` workspace, or tracked files on remote branch `fix/v045-role-b-case-id-recovery` at `f4705897d3302b0ca1adf880cde7e9c7d52c118d` |
| Current prediction source | `fixed10_offline_predictions.jsonl`, newly reproduced from the governed current Hybrid pipeline with the provider deliberately unavailable |
| LLM rerun required? | **YES, only to obtain the missing real-LLM baseline; no LLM rerun was performed in this task** |

The remote branch contains the recovery code but not the iteration payloads. Its `.gitignore` ignores `reports/*`, and its tracked tree contains no `reports/v045_role_b/iterations/*`, `analysis_result.json`, `analysis_results.jsonl`, `iteration_context.json`, or `iteration_summary.json`. The recovery command correctly requires all ten persisted results to exist and to be real-LLM results. Consequently, fabricating a mapping from the historical smoke 10 to the Metric-v2 fixed-10 would be invalid: only `ipo_2020_01961` and `ipo_2020_09600` overlap.

The current `case_id` handoff is correct: `run_v045_role_b_iteration._write_results_jsonl` validates any existing identity and writes canonical top-level `case_id`; the new offline artifact carries both top-level and metadata identity. The previous evaluator failure is fixed in code, but its ignored input files are gone.

Leakage audit:

- Gold is not included in the runtime cases manifest or prompt.
- The prediction adapter imports no evaluator or Expert-Gold module and records `gold_used_for_prediction=false`.
- The fixed-10 itself is deliberately selected using Development Gold support, so it is a diagnostic subset, not an unbiased competition PASS set.
- No `if case_id == ...` production special case was found.
- 2024 Validation was not opened for scoring and no 2025 outcome label was accessed.

## B. Prospectus Source

Source is the supplied outer ZIP, with six nested annual ZIPs and catalog-based member identity. `case_id -> data/catalog/ipo_prospectus_manifest.csv -> source year/member -> bytes -> parser` resolves all fixed-10 PDFs.

The benchmark adapter opens each annual ZIP through `ZipExtFile`, does not persist it, and stages at most one PDF because the production parser requires a path. Every staged PDF is checked against filename, size, SHA-256 and physical page count, then deleted in `finally`. Fixed-10 maximum PDF size is 53,051,317 bytes (50.59 MiB), below the 100 MB redesign boundary. Verification passed 10/10.

`prospectus root missing` in this machine means both:

1. `IPO_RISK_PROSPECTUS_ROOT` is not set; and
2. the existing runner only accepts a real directory and cannot resolve the nested ZIP.

It is not missing source data: all ten PDFs exist in the ZIP and match the frozen catalog.

## C. LLM Config

Secrets were never printed.

| Setting | Required fixed-10 value | Current status |
|---|---|---|
| Provider | `openai_responses` | `IPO_RISK_LLM_PROVIDER = missing`; YAML static value is `openai_compatible`, so effective preflight fails without an environment override |
| Model | `ark-code-latest` | `IPO_RISK_LLM_MODEL = missing` |
| Endpoint | Responses-compatible base URL | `IPO_RISK_LLM_BASE_URL = missing` |
| API key | `IPO_RISK_LLM_API_KEY` | missing |
| Prospectus directory | `IPO_RISK_PROSPECTUS_ROOT` | missing; ZIP adapter verified source instead |
| Timeout | 300 seconds | present in YAML |
| Transport retries | 0 | present in YAML |
| Temperature | unspecified / provider default | no explicit value |
| Reasoning | low | hard-coded by Responses adapter |
| Structured output | required strict function tool, one call, `parallel_tool_calls=false`, max output 2048 | implemented |
| Structured correction | one bounded correction even when transport retries are zero | implemented; two maximum structured attempts |

Because the provider, model, endpoint and key are missing, a real run was not authorized or technically runnable. A real baseline would analyze exactly 10 documents. External HTTP call count is data-dependent (Legal/Business tasks and optional supervisor/re-check calls), so it cannot be truthfully stated before telemetry exists; this task made **0** external calls and created no raw request/response corpus.

## D. Metric Reconciliation

### METRIC_RECONCILIATION

| Dimension | Current Hybrid headline | Historical Retriever V3 quoted result |
|---|---|---|
| dataset | Retriever V3 frozen feature table | Retriever V3 locked Phase E |
| split | 50-case Development | 10-case locked validation (all 2022) |
| PDFs | 0 in replay; features already materialized | 10 at locked evaluation creation |
| cases | 50 | 10 |
| tasks | 400 case-risk queries | 80 case-risk queries |
| Gold source | frozen Retriever V3 qrels | same source family, locked subset |
| Evidence definition | all positive `gold_label > 0` pages | 93 required Gold Evidence units |
| candidate definition | V1 keyword + BM25-B only; selective lane policy | V1 + V2 + V2.1 + BM25-B + Table-C |
| Oracle definition | lane-union coverage before final RRF | full five-source union coverage |
| Recall definition | per positive qrel row | per required Evidence unit |
| top-k | 5/10/20/50 | 5/10/20/50/100 |
| keyword lane | V1 | V1 + V2 + V2.1 |
| BM25 | BM25-B | BM25-B |
| Table lane | no | Table-C |
| LTR | no | LTR-C |
| reranker | equal RRF, keyword-rank tie-break | frozen LightGBM LambdaMART LTR-C |
| evaluator | `evaluate_hybrid_bm25_adapter.py` | Retriever V3 `evidence_recall` / locked Phase E |
| filtering | cash runway and litigation remain keyword-only | all five sources available for every supported risk |
| leakage policy | Development evaluation; no learned model | Development five-fold OOF training; locked set opened once after freeze |

The quoted `Oracle@50=94.62%` and `LTR Recall@20=89.25%` are therefore not comparable to `89.60%/73.28%`. Classification: **B. 部分可比，需要重新统一 evaluator**, with **E. 当前实验缺少 V3/LTR component** as the concrete implementation reason. There is no evidence of a measurement bug.

Apples-to-apples replay on the same 50 Development cases, 400 tasks, 576 historical `requirement=required` Evidence units and one evaluator definition:

| Metric | Historical V3 LTR-C | Current Hybrid | Delta (Current - V3) |
|---|---:|---:|---:|
| Oracle@20 | 85.94% | 76.04% | -9.90 pp |
| Oracle@50 | 93.92% | 86.81% | -7.12 pp |
| Recall@5 | 63.02% | 54.17% | -8.85 pp |
| Recall@10 | 73.26% | 63.72% | -9.55 pp |
| Recall@20 | 80.90% | 72.74% | -8.16 pp |
| Recall@50 | 89.06% | 85.59% | -3.47 pp |
| Evidence-unit MRR | 0.4742 | 0.3857 | -0.0884 |

Historical report MRR is query-level and current headline MRR is evidence-unit-level; those original MRR numbers must not be compared. The table above recomputes both as evidence-unit MRR.

## E. Current Frozen Baseline

### Retrieval — existing 50-case Development replay (all 625 positive qrels)

| Metric | Value |
|---|---:|
| Oracle@20 | 77.12% |
| Oracle@50 | 89.60% |
| Recall@5 | 52.96% |
| Recall@10 | 63.20% |
| Recall@20 | 73.28% |
| Recall@50 | 88.48% |
| MRR | 0.3773 |
| Required@1 (`gold_label>=2`) | 25.05% |
| Required@3 | 49.50% |
| Required@5 | 56.66% |
| Required@10 | 66.20% |
| Required@20 | 75.75% |

### Current Metric-v2 fixed-10 — offline governed lower bound

| Metric | Value |
|---|---:|
| Cases completed / mapped | 10 / 10 |
| Positive Risk Units | 30 |
| Existing Evidence Units | 48 |
| M1 official-aligned accuracy | 0.00% (0/30) |
| M2 Evidence coverage | 0.00% (0/48) |
| Recall@1/@3/@5/@10/@20 | all 0.00% |
| Real-LLM cases | 0 |
| Network LLM calls | 0 |
| Mean full case latency | 27.291 s (not LLM latency) |
| Input/output/total tokens | Not available |

This is not the requested real-LLM frozen baseline. It is the reproducible deterministic/offline degradation baseline and proves that case mapping, ZIP source, parser, current Hybrid wiring and Metric-v2 evaluator now run end to end.

### Real-LLM runtime baseline

| Metric | Value |
|---|---|
| Call count | Not available |
| Structured success / parse failure / validation failure | Not available |
| Retry count/rate | Not available |
| Request fallback count/rate | Not available |
| Tokens / LLM latency | Not available |
| M1 / M2 | Not available |

Reason: exact persisted fixed-10 real-LLM outputs are absent and current credentials/effective configuration are incomplete. No result was invented or substituted.

## F. LLM Failure Breakdown

No external LLM request occurred, so request-level categories (`JSON_PARSE_FAIL`, `SCHEMA_FAIL`, `MISSING_CANDIDATE`, `DUPLICATE_CANDIDATE`, `UNKNOWN_ENUM`, `TIMEOUT`, `PROVIDER_ERROR`, `EMPTY_RESPONSE`, `VALIDATION_FAIL`) are **Not available**, not zero. All 10 offline cases honestly recorded `llm_provider=unavailable` and `llm_status=offline_unavailable`.

The research-only LLM reranker is batch-atomic: `LLMCandidateJudgmentBundle` validates the whole list, and coverage mismatch, duplicate candidate IDs, or unknown facets rejects the whole rerank. It has no per-candidate salvage. This is a valid next-phase concern, but it is **not active in the current `hybrid_bm25` production path**, so it did not cause this fixed-10 offline result. No salvage change was made.

## G. M1/M2 Diagnosis

Observed offline pattern is M2 low / M1 low, but it must not be diagnosed as a retrieval failure because the semantic provider was intentionally unavailable:

- 29/30 positive Risk Units are `semantic_extraction_miss`;
- one `customer_concentration` RiskItem has correct status/level but does not retain an exact matching Gold anchor (`evidence_not_retained_in_final_risk`);
- only one primary mapped RiskItem was produced across ten cases;
- current Development retrieval already demonstrates substantial, non-zero candidate coverage.

Therefore the currently proven bottleneck is **measurement/runtime availability**, followed by a **mixed Evidence -> RiskItem conversion question that requires real-LLM results**. Evidence packaging, structured output, normalization, verifier and supervisor cannot be ranked from this offline run. The real M1/M2 relationship remains Not available.

## H. Corpus Health

| Item | Value |
|---|---:|
| Outer ZIP members | 29 |
| Nested annual archives | 6 (`2020`–`2025`) |
| PDFs | 565 |
| PDF compressed bytes | 6,487,199,980 |
| PDF uncompressed bytes | 7,776,164,822 |
| Parse success | 565 |
| Parse failure | 0 |
| Median pages | 614 |
| Maximum pages | 2,834 |
| Total physical pages | 354,497 |
| Text-bearing pages (`chunk_count` health proxy) | 354,122 |
| Blank pages | 375 |
| Zero-page PDFs | 0 |
| Suspicious PDFs (<10% text-bearing pages or parse failure) | 0 |
| Exceptions | none |

`chunk_count` in the metadata CSV is explicitly a lightweight count of text-bearing physical pages, not the production segmentation chunk count. The scan read one PDF into memory at a time, persisted no text and did not access any 2025 outcome label.

## I. Regression Analysis

`ipo_2020_08489` is a fusion/top-k crowding regression, not a Gold anomaly:

- the lost required Evidence is `revenue_growth`, page 299;
- V1 keyword rank = 15 (inside top 20);
- BM25 rank = 39;
- equal RRF hybrid rank = 25 (outside top 20);
- 24 non-Gold candidates, including revenue-like pages, outrank it after fusion.

Three other Evidence units show the same displacement mechanism: `ipo_2020_01167/precommercial_product/page225`, `ipo_2020_09986/revenue_growth/page411`, and `ipo_2021_02137/revenue_growth/page564`. Only `ipo_2020_08489` becomes a net case-level Recall@20 regression because gains offset losses in the other cases.

Classification: `fusion weight problem + BM25 disagreement + top-k crowding`. Mechanism systemic: **YES (4 Evidence units / 4 cases)**. Net case regression systemic: **NO (1/50 cases)**. No case-specific fix was made.

## J. Disk Audit

| Item | Result |
|---|---|
| ZIP extracted? | **NO** |
| PDF copies created? | One temporary fixed-10 PDF at a time; all deleted |
| Annual ZIP copies created? | NO |
| Temporary files remaining? | NO benchmark PDF/year ZIP; pytest owns its normal OS temp lifecycle |
| New cache / index / embedding | NO |
| Parsed full text / page images persisted | NO |
| Raw LLM corpus persisted | NO |

Persistent artifacts are only compact scripts/tests, prediction/evaluation metadata, corpus metadata, reconciliation JSON and this report:

- new persistent files: 14;
- total size: 147,954 bytes (0.141 MiB);
- largest: `CORPUS_HEALTH_SUMMARY.csv`, 57,306 bytes;
- removed reproducible Python/pytest caches: 36 directories / 9,026,189 bytes;
- remaining task cache directories: 0;
- D: free after task: 8,015,101,952 bytes (7.465 GiB).

## K. Recommendation

1. **Restore one authentic real-LLM fixed-10 run and persist a compact governed iteration bundle.** Expected impact: highest, because it unlocks real M1/M2 and failure attribution. Risk: provider cost/config errors. Cost: 10 document runs; data-dependent bounded calls. Use ZIP-backed sequential source handling and retain case ID, per-call failure class, token/latency metadata and final results only.
2. **Add measurement-only LLM telemetry before that run.** Expected impact: high for reliability diagnosis. Risk: low if secrets/raw Evidence are excluded. Cost: small. Record call count, schema/parse/validation failures, correction attempts, fallback stage and affected case without changing prompt/model/Agent behavior.
3. **Only after the authentic baseline, choose one A/B based on M1/M2.** Expected impact: conditional. Risk: premature EvidencePack work would destroy attribution. Cost: moderate. If M2 is high but M1 low, prioritize Evidence-to-RiskItem/normalization/verifier trace; if candidate trace is low, reconcile production Hybrid versus frozen V3 components before EvidencePack.

`READY_FOR_EVIDENCEPACK_AB = NO`

Reason: authentic fixed-10 real-LLM M1/M2, runtime/fallback telemetry and candidate traces remain unavailable. The current offline 0/0 result cannot isolate EvidencePack quality.
