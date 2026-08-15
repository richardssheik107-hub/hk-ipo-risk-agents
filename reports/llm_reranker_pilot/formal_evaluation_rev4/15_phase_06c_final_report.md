# Phase 0.6C Final Report — Revision 4

## One-line answer

**LLM reranker effective: true for semantic ordering; runtime reliability remains poor at 18.75% fallback, and this pilot is not production-ready.**

## 1. Research Question

Given a high-recall deterministic candidate set, does an LLM provide incremental semantic ranking value beyond keyword/rule-based retrieval?

## 2. Experimental Integrity

- Pre-Gold Revision 4 verified before unlock: `true`.
- Official tasks: `80/80`; completed `65`; fallback `15`.
- Candidate SHA-256: `51037b682dad4d133db14417915fd9eaf749b8109ea8e1641ff1685ebeb17bfe`.
- Official judgment aggregate SHA-256: `aa1b62e87158ccc8e46cb3fe296bfc624fee9b6b8994a4d71355e730c60b3912`.
- Gold was used only by this evaluator after output freeze.
- Real LLM calls during evaluation: `0`.
- 2025 blind accessed: `false`.
- No post-Gold tuning or output replacement was performed.
- Diagnostic replay interpretation: **diagnostic non-reproduction**. The original structured-output failures were not reproducible under identical diagnostic replay, but their original official fallbacks were retained as Revision-4 reliability costs.

## 3. Dataset

This is a **post-freeze retrospective development benchmark**, not blind or unseen validation. The 10 cases were previously exposed at project level, while the LLM semantic contract was frozen before Gold evaluation.

- Cases: `10`
- Risk tasks: `80`
- Evidence / required / primary: `143 / 116 / 92`
- Unique Gold pages: `114`
- Canonical manifest uses `ipo_2021_00013`; the frozen runtime cache uses `ipo_2020_00013`. The evaluator records a unique suffix-based identity alias and does not change the sample.

## 4. Variants

- A: V1 KeywordDocumentRetriever
- B: V2 DomainAwareRetrieverV2
- C: V2.1 frozen PR-46 research ranking
- D: Stage1 Union baseline, no semantic reranking
- E: Revision-4 LLM reranker; official failures use Stage1 order

## 5. Main Results

| Variant | Required@1 | Required@3 | Required@5 | Required@10 | Required@20 | Completion@3 | Completion@5 | Completion@10 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1 | 14.66% | 34.48% | 41.38% | 50.00% | 56.90% | 27.50% | 36.25% | 47.50% | 0.2669 |
| v2 | 14.66% | 31.03% | 37.93% | 50.86% | 59.48% | 25.00% | 32.50% | 46.25% | 0.2616 |
| v21 | 12.07% | 31.90% | 45.69% | 50.86% | 58.62% | 27.50% | 45.00% | 50.00% | 0.2495 |
| stage1_union | 14.66% | 34.48% | 42.24% | 50.86% | 59.48% | 27.50% | 37.50% | 46.25% | 0.2690 |
| llm_rev4 | 21.55% | 40.52% | 50.86% | 58.62% | 59.48% | 38.75% | 45.00% | 55.00% | 0.3304 |

The four primary decision metrics are Required@3, Required@5, Completion@5 and MRR. Baseline reproduced: `true`.

## 6. Incremental LLM Value — E vs D

| Metric | Stage1 Union | LLM Rev4 | Delta |
| --- | ---: | ---: | ---: |
| required_at_1 | 0.1466 | 0.2155 | 0.0690 |
| required_at_3 | 0.3448 | 0.4052 | 0.0603 |
| required_at_5 | 0.4224 | 0.5086 | 0.0862 |
| required_at_10 | 0.5086 | 0.5862 | 0.0776 |
| required_at_20 | 0.5948 | 0.5948 | 0.0000 |
| completion_at_3 | 0.2750 | 0.3875 | 0.1125 |
| completion_at_5 | 0.3750 | 0.4500 | 0.0750 |
| completion_at_10 | 0.4625 | 0.5500 | 0.0875 |
| mrr | 0.2690 | 0.3304 | 0.0614 |

## 7. Reliability

| Metric | Value |
| --- | ---: |
| Official Tasks | 80 |
| LLM Completed | 65 |
| Fallback | 15 |
| Fallback Rate | 18.75% |
| Diagnostic Replays | 3 |
| Replays Included in Metrics | 0 |
| Gold Leakage | false |
| 2025 Accessed | false |

Structured-output reliability: **POOR**. Semantic and engineering conclusions are intentionally separate.

## 8. Completed-only Diagnostic

Completed-only results are a **diagnostic upper bound only** and never replace the all-task official result. See `11_completed_only_diagnostic.json`.

## 9. Domain Results

| Domain | Variant | Required@3 | Required@5 | Required@20 | Completion@5 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| business | v1 | 0.00% | 0.00% | 15.38% | 0.00% | 0.0151 |
| business | v2 | 0.00% | 0.00% | 7.69% | 0.00% | 0.0048 |
| business | v21 | 7.69% | 15.38% | 38.46% | 20.00% | 0.0706 |
| business | stage1_union | 0.00% | 0.00% | 15.38% | 0.00% | 0.0098 |
| business | llm_rev4 | 0.00% | 7.69% | 15.38% | 0.00% | 0.0278 |
| financial | v1 | 47.95% | 53.42% | 65.75% | 46.00% | 0.3342 |
| financial | v2 | 42.47% | 52.05% | 71.23% | 44.00% | 0.3328 |
| financial | v21 | 39.73% | 54.79% | 64.38% | 52.00% | 0.2919 |
| financial | stage1_union | 47.95% | 54.79% | 69.86% | 48.00% | 0.3405 |
| financial | llm_rev4 | 53.42% | 61.64% | 69.86% | 54.00% | 0.4050 |
| legal | v1 | 16.67% | 30.00% | 53.33% | 30.00% | 0.2122 |
| legal | v2 | 16.67% | 20.00% | 53.33% | 20.00% | 0.1997 |
| legal | v21 | 23.33% | 36.67% | 53.33% | 40.00% | 0.2237 |
| legal | stage1_union | 16.67% | 30.00% | 53.33% | 30.00% | 0.2075 |
| legal | llm_rev4 | 26.67% | 43.33% | 53.33% | 45.00% | 0.2800 |

## 10. Risk Results — Official LLM Rev4

| Risk | Required | Required@3 | Required@5 | Required@20 | Completion@5 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cash_runway | 20 | 55.00% | 75.00% | 95.00% | 50.00% | 0.3748 |
| continuous_loss | 11 | 36.36% | 45.45% | 45.45% | 50.00% | 0.3818 |
| customer_concentration | 15 | 53.33% | 60.00% | 66.67% | 50.00% | 0.3763 |
| material_litigation_compliance | 14 | 21.43% | 57.14% | 71.43% | 50.00% | 0.2833 |
| precommercial_product | 13 | 0.00% | 7.69% | 15.38% | 0.00% | 0.0278 |
| redemption_rights | 16 | 31.25% | 31.25% | 37.50% | 40.00% | 0.2771 |
| revenue_growth | 11 | 45.45% | 45.45% | 54.55% | 50.00% | 0.3690 |
| supplier_concentration | 16 | 68.75% | 68.75% | 68.75% | 70.00% | 0.5104 |

## 11. Candidate Coverage vs Ranking Errors

- Stage1 Required Recall@20: `59.48%`.
- Candidate-coverage misses among required rows: `47`.
- Stage1 interpretation: `severe bottleneck`.

## 12. Head Recoveries

- Recoveries to Top 3/5 or deep gains: `20`.
- Full rows: `08_promotion_regression_matrix.csv`.

## 13. Head Regressions

- Demotions from Top 3/5: `8`.
- No ranking policy was changed after inspection.

## 14. Facet Coverage

Facet coverage is diagnostic and is not a substitute for Gold Evidence Recall. Full @3/@5/@10 results are in `12_facet_coverage.json`.

## 15. Semantic Error Taxonomy

Top-5 required misses: `57`. Counts: `{"AUTHORITY_CONFUSION": 0, "CANDIDATE_COVERAGE_MISS": 47, "CURRENT_STATUS_CONFUSION": 0, "FALLBACK_NO_LLM": 4, "FINANCIAL_MULTIPAGE_FRAGMENTATION": 1, "GENERIC_BOILERPLATE_CONFUSION": 0, "LLM_HEAD_DEMOTION": 3, "LLM_INSUFFICIENT_PROMOTION": 0, "MULTIPAGE_COMPLETION_FAILURE": 2, "OTHER": 0}`.

## 16. Promotion Decision

- `SEMANTIC_RANKING_RESULT = POSITIVE`
- `STRUCTURED_OUTPUT_RELIABILITY = POOR`
- `LLM_RERANKER_PILOT_PROMISING = false`
- `PRODUCTION_READY = false`

## 17. Limitations

- Retrospective benchmark; all 10 cases were previously exposed at project level.
- 18.75% structured-output fallback is a material reliability cost.
- Single-pass Stage1 candidate ceiling constrains reranking.
- No 2025 validation was accessed.
- No end-to-end Agent/Verifier evaluation is part of this phase.
- The completed-only slice is diagnostic, not an official result.

## 18. Next Phase Recommendation

`NEXT_RECOMMENDED_PHASE = PHASE_0_6D_RERANKER_V1_1`

No Phase 0.7/0.6D implementation is performed here. Any Reranker V1.1 work must use a fresh benchmark and cannot claim validation on these 10 cases.

## Frozen Decision Fields

```text
BASELINE_REPRODUCED = true
GOLD_SET_DRIFT = false
GOLD_LEAKAGE = false
2025_BLIND_ACCESSED = false
REAL_LLM_CALLS_DURING_EVALUATION = 0
STAGE1_REQUIRED_RECALL_AT20 = 0.594827586207
LLM_REQUIRED_RECALL_AT3 = 0.405172413793
LLM_REQUIRED_RECALL_AT5 = 0.508620689655
LLM_COMPLETION_AT5 = 0.450000000000
LLM_MRR = 0.330402419589
LLM_DELTA_VS_STAGE1_AT3 = 0.060344827586
LLM_DELTA_VS_STAGE1_AT5 = 0.086206896552
OFFICIAL_FALLBACK_RATE = 0.187500000000
SEMANTIC_RANKING_RESULT = POSITIVE
STRUCTURED_OUTPUT_RELIABILITY = POOR
LLM_RERANKER_PILOT_PROMISING = false
NEXT_RECOMMENDED_PHASE = PHASE_0_6D_RERANKER_V1_1
```
