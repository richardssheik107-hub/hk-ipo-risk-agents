# Retriever V3 Phase B — Page-level BM25

PHASE R3-B RESULT:

PASS

New Lane:
Page-level BM25

Development cases:
50

Locked cases:
10

Locked metrics opened:
NO

## BM25 Standalone

| Retriever | R@5 | R@20 | R@50 | R@100/native |
|---|---:|---:|---:|---:|
| V1 | 48.61% | 59.72% | 66.15% | 66.15% |
| V2 | 47.22% | 63.37% | 70.31% | 71.53% |
| V2.1 | 49.65% | 62.67% | 69.27% | 71.88% |
| BM25 | 49.48% | 75.52% | 87.15% | 92.71% |

### BM25 Primary Required / Completion

| Metric | @5 | @20 | @50 | @100 |
|---|---:|---:|---:|---:|
| Primary Required Recall | 50.86% | 77.25% | 88.63% | 93.35% |
| Required Completion | 46.85% | 72.04% | 85.14% | 91.18% |

### CV variant comparison

| Variant | Tokenizer | Unique@50 | Unique@100 |
|---|---|---:|---:|
| BM25-A | cjk_unigram | 67 | 88 |
| BM25-B | cjk_bigram | 95 | 114 |
| BM25-C | cjk_bigram_trigram | 92 | 114 |

BM25-B 依据预先固定的 selection order 胜出；B 与 C 的 @100 相同，但 B 的 @50 更高。

## Stage1 Ceiling

| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |
|---|---:|---:|---:|
| V1∪V2∪V2.1 | 66.84% | 74.65% | 75.00% |
| V1∪V2∪V2.1∪BM25 | 83.33% | 91.32% | 94.79% |

Oracle Coverage ≠ Fused Recall；Oracle 只表示至少一个 Lane 看到了 Gold。

## 144 Old Complete Misses

Old complete candidate misses: 144

BM25 recovered @20: 71

BM25 recovered @50: 95

BM25 recovered @100: 114

Remaining: 30

## BM25 Unique Contribution by Risk

| Risk | Old Complete Misses | BM25 Recovered@20 | BM25 Recovered@50 | BM25 Recovered@100 |
|---|---:|---:|---:|---:|
| cash_runway | 8 | 7 | 7 | 7 |
| continuous_loss | 23 | 19 | 22 | 23 |
| customer_concentration | 19 | 11 | 13 | 19 |
| material_litigation_compliance | 5 | 3 | 3 | 4 |
| precommercial_product | 36 | 3 | 13 | 20 |
| redemption_rights | 35 | 19 | 23 | 24 |
| revenue_growth | 9 | 5 | 7 | 9 |
| supplier_concentration | 9 | 4 | 7 | 8 |

## Case diversity

New Gold recovered: 114

Across IPO cases: 40

Across risk_codes: 8

BM25-only Gold：@20=71，@50=95，@100=114。

## 5-fold stability

| Fold | Old Misses Recovered@100 | Oracle Gain@50 |
|---|---:|---:|
| 1 | 22 | 16.26% |
| 2 | 22 | 11.02% |
| 3 | 32 | 25.45% |
| 4 | 22 | 20.19% |
| 5 | 16 | 11.61% |

## QUERY_COVERAGE

QUERY_COVERAGE misses: 40

Recovered by BM25 @20: 15

Recovered @50: 25

Recovered @100: 30

Still missing: 10

## Equal-weight RRF

| Fusion | R@5 | R@20 | R@50 | R@100 |
|---|---:|---:|---:|---:|
| Old 3-lane | 50.35% | 63.02% | 73.44% | 75.00% |
| New 4-lane | 53.82% | 73.61% | 86.28% | 93.23% |

Fusion 使用固定 equal-weight RRF，没有按 Gold 调权重。

## Bounded candidate pool

- Mean unique candidates: 100.00
- Median: 100.00
- P95: 100
- Max: 100（上限100）

每个池只保留当前 IPO 中 BM25 分数大于零的真实 physical pages，经四 Lane 去重和固定 RRF 后截断到100；没有补零分页，也没有使用整本 PDF 作为候选。

## Remaining old misses

- QUERY_COVERAGE_MISS: 10
- TABLE_FRAGMENTATION: 8
- NEIGHBOR_PAGE_MISS: 4
- SECTION_AUTHORITY_MISS: 6
- MULTIPAGE_FRAGMENTATION: 2
- OTHER_UNKNOWN: 0

## PASS gates

- A_unique_gold_at_least_10: PASS
- B_at_least_5_cases: PASS
- C_at_least_3_risks: PASS
- D_oracle_gain_at_least_2pp: PASS
- E_candidate_misses_decrease: PASS
- F_positive_recovery_in_4_of_5_folds: PASS

## Frozen BM25 configuration

`{"name": "BM25-B", "tokenizer": "cjk_bigram", "k1": 1.5, "b": 0.75, "top_k": 100, "query_construction": "frozen V1/V2 query families + canonical risk terms", "tie_break": "score desc, physical page asc", "index_scope": "one IPO in memory"}`

Query source: frozen V1/V2/V2.1 query families + canonical risk terminology；没有使用 Gold exact_text 做 query expansion。

## Disk and isolation

- Available disk before: 7.83 GiB
- Peak temporary disk: 1358.4 MiB
- Available disk after: 7.83 GiB
- Persistent BM25 index: NO
- Embedding/model download: NO
- Temporary PDFs remaining: 0
- Temporary year ZIP remaining: 0
- Temporary directories: CLEAN

## Locked validation

Metrics opened: NO

Gold inspected for tuning: NO

Pattern mining: NO

Push: NO

Remote GitHub modified: NO

## 简单结论

BM25 PASS。

原来有144条正确 Evidence 是 V1/V2/V2.1 三个系统全部找不到的；BM25 在 Top100 新找回114条，来自40家 IPO，覆盖8个 risk。Stage1 Oracle@50 从74.65%提高到91.32%，说明 BM25 确实提供了旧 Retriever 没有的通用搜索能力，值得作为 experimental V3 candidate lane 保留。

下一阶段建议单独研究 Table Fragmentation。虽然仍有10条 Query Coverage miss，但继续扩 BM25 词汇容易重新走向关键词工程；剩余8条明确表格碎片是更独立、可验证的下一 Lane。本阶段不实施。
