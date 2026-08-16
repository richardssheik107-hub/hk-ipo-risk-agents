# Retriever V3 Phase D — Learning-to-Rank

PHASE R3-D RESULT:

PASS

Model:
LightGBM LambdaMART

Development:
50 cases

Validation:
5-fold Group CV

Locked:
10 cases

Locked metrics opened:
NO

## OOF Ranking Performance

| Ranker | R@5 | R@10 | R@20 | R@50 | R@100 |
|---|---:|---:|---:|---:|---:|
| Equal-weight RRF | 54.51% | 64.41% | 75.35% | 87.15% | 94.79% |
| LTR-A | 57.64% | 67.71% | 77.78% | 88.19% | 94.62% |
| LTR-B | 60.42% | 69.62% | 76.56% | 87.67% | 94.97% |
| LTR-C | 63.02% | 73.26% | 80.90% | 89.06% | 94.79% |

Selected: **LTR-C**（仅依据 OOF Development）。

## Completion

| Ranker | Completion@5 | Completion@20 |
|---|---:|---:|
| RRF | 50.88% | 71.79% |
| LTR-C | 61.46% | 78.84% |

## Ranking quality

| Ranker | MRR | NDCG@5 | NDCG@10 | NDCG@20 |
|---|---:|---:|---:|---:|
| RRF | 0.4707 | 0.4381 | 0.4751 | 0.5023 |
| LTR-C | 0.6100 | 0.5608 | 0.5946 | 0.6125 |

## Ranking Ceiling

Candidate Source Oracle@20: 85.94%

Pre-cap Pool Oracle@20: 96.01%

RRF@20: 75.35%

Best LTR@20: 80.90%

Ranking Gap Closed (source oracle): 52.46%

Pre-cap Pool Oracle@5: 96.01%

Top5 Gap Closed: 20.50%

## Per-Risk

| Risk | RRF R@5 | LTR R@5 | RRF R@20 | LTR R@20 |
|---|---:|---:|---:|---:|
| cash_runway | 83.51% | 90.72% | 95.88% | 98.97% |
| continuous_loss | 54.72% | 81.13% | 86.79% | 94.34% |
| customer_concentration | 59.49% | 55.70% | 83.54% | 77.22% |
| material_litigation_compliance | 56.52% | 63.04% | 80.43% | 85.87% |
| precommercial_product | 16.42% | 16.42% | 29.85% | 35.82% |
| redemption_rights | 40.30% | 41.79% | 64.18% | 67.16% |
| revenue_growth | 35.85% | 73.58% | 56.60% | 86.79% |
| supplier_concentration | 70.59% | 76.47% | 91.18% | 95.59% |

## Fold Stability

| Fold | RRF R@20 | LTR R@20 | Delta |
|---|---:|---:|---:|
| 1 | 69.11% | 75.61% | 6.50% |
| 2 | 70.87% | 73.23% | 2.36% |
| 3 | 76.36% | 86.36% | 10.00% |
| 4 | 78.85% | 84.62% | 5.77% |
| 5 | 83.04% | 86.61% | 3.57% |

## Gold movement

Top20 promoted: 58
Top20 lost: 28
Top20 net: 30

Top5 promoted: 74
Top5 lost: 30
Top5 net: 44

Gold absent from the pre-cap source union: 23
RRF Top100 Gold lost specifically to cap/ranking: 7
LTR Top100 Gold lost specifically to cap/ranking: 7

## Weak-negative sensitivity

40/query LTR-C R@20: 80.90%
20/query LTR-C R@20: 80.56%
Absolute difference: 0.35%

## Top feature importance

1. bm25_score_norm: 13641.43
2. page_numeric_density: 3000.62
3. v1_rank: 1023.13
4. risk_precommercial_product: 980.72
5. page_currency_count_log: 717.06
6. v21_rank: 700.46
7. rrf_rank: 628.97
8. table_block_hit_count: 614.30
9. equal_rrf_score: 577.74
10. page_percentage_count_log: 477.69
11. page_text_length_log: 458.34
12. v2_rank: 448.13
13. risk_customer_concentration: 403.74
14. table_candidate_signal: 303.43
15. bm25_rank: 236.57
16. table_score_norm: 221.88
17. page_table_signal: 220.86
18. table_rank: 129.97
19. risk_continuous_loss: 106.85
20. risk_material_litigation_compliance: 43.49

## Representative promotions

| Case | Risk | Page | RRF rank | LTR rank | Main ranking signals |
|---|---|---:|---:|---:|---|
| ipo_2020_01408 | customer_concentration | 390 | 40 | 6 | bm25_score_norm, page_numeric_density, rrf_rank |
| ipo_2020_01961 | revenue_growth | 466 | 30 | 7 | bm25_score_norm, page_numeric_density, v1_rank |
| ipo_2020_01961 | supplier_concentration | 466 | 52 | 15 | bm25_score_norm, page_numeric_density, page_currency_count_log |
| ipo_2020_01961 | redemption_rights | 150 | 38 | 14 | bm25_score_norm, page_numeric_density, rrf_rank |
| ipo_2020_01961 | material_litigation_compliance | 270 | 25 | 9 | bm25_score_norm, page_numeric_density, v21_rank |
| ipo_2020_01961 | precommercial_product | 167 | 21 | 4 | bm25_score_norm, page_numeric_density, risk_precommercial_product |
| ipo_2020_02057 | revenue_growth | 300 | 25 | 2 | bm25_score_norm, page_numeric_density, v1_rank |
| ipo_2020_02263 | revenue_growth | 397 | 23 | 1 | bm25_score_norm, page_numeric_density, v1_rank |
| ipo_2020_02263 | customer_concentration | 397 | 26 | 3 | bm25_score_norm, page_numeric_density, page_currency_count_log |
| ipo_2020_02263 | material_litigation_compliance | 212 | 36 | 14 | bm25_score_norm, page_numeric_density, page_currency_count_log |

## Serious regression audit

- customer_concentration: R@20 83.54% → 77.22%（-6.33%）

这是唯一超过5pp的核心 risk 回退；已显式保留为 Locked validation 前的风险项。


## Disk and freeze

- Available disk before: 7.83 GiB
- Peak temporary disk: 1358.4 MiB
- Available disk after: 7.83 GiB
- Feature dataset size: 3.365 MB
- Final model size: 0.109 MB
- Temporary PDFs remaining: 0
- Temporary ZIPs remaining: 0
- Training checkpoints remaining: 0
- Temporary dirs: CLEAN

## Locked validation

Metrics opened: NO

Gold inspected: NO

Used for training/tuning: NO

Push: NO

Remote GitHub modified: NO

## 简单结论

LTR PASS。

等权RRF的Top20为75.35%；LTR-C在完全OOF评测中达到80.90%。Top5从54.51%提高到63.02%。提升通过fold、risk和Top100回归Gate，因此值得保留为实验性V3排序层。

LTR frozen. Candidate Generation frozen.

Recommended next step: Run final locked validation on the complete frozen V3 package.

Awaiting approval before opening Locked 10.
