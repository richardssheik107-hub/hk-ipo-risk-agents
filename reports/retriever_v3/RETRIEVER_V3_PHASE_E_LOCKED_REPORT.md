# Retriever V3 Phase E — Final Locked Validation

PHASE R3-E FINAL LOCKED RESULT:

CANDIDATE_PASS_RANKING_MIXED

Locked cases: 10
Locked Gold: 93

## Candidate generalization

| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |
|---|---:|---:|---:|
| V1∪V2∪V2.1 | 72.04% | 80.65% | 81.72% |
| + BM25 | 89.25% | 91.40% | 93.55% |
| + Table | 90.32% | 94.62% | 94.62% |

Old union → Full V3 gain:

- Oracle@50: 80.65% → 94.62%（+13.98pp）
- Oracle@100/native: 81.72% → 94.62%（+12.90pp）
- Old complete misses: 17
- Full V3 complete misses: 5
- BM25 unique recovery: 11
- Table unique recovery beyond BM25: 1

Standalone native coverage（93 Gold；仅作 Lane 覆盖诊断）：V1 77.42%，V2 76.34%，V2.1 76.34%，BM25-B 93.55%，TABLE-C 76.34%。

## Locked Final Ranking

| Ranker | R@5 | R@10 | R@20 | R@50 | R@100 |
|---|---:|---:|---:|---:|---:|
| RRF | 60.22% | 68.82% | 80.65% | 91.40% | 93.55% |
| Frozen LTR-C | 69.89% | 78.49% | 89.25% | 91.40% | 94.62% |

## Completion

| Ranker | Completion@5 | Completion@20 |
|---|---:|---:|
| RRF | 55.00% | 77.50% |
| LTR-C | 65.00% | 87.50% |

Ranking delta:

- R@5: +9.68pp（promoted 15，lost 6，net +9）
- R@20: +8.60pp（promoted 11，lost 3，net +8）
- Completion@5: +10.00pp
- Completion@20: +10.00pp

## Ranking quality

| Ranker | MRR | NDCG@5 | NDCG@10 | NDCG@20 |
|---|---:|---:|---:|---:|
| RRF | 0.3996 | 0.4181 | 0.4472 | 0.4799 |
| LTR-C | 0.5637 | 0.5653 | 0.5936 | 0.6233 |

## PREDECLARED WATCH: customer_concentration

Gold count: 10
Case-risk count: 10
RRF R@5: 80.00%
LTR R@5: 60.00%
RRF R@20: 90.00%
LTR R@20: 80.00%
Delta R@20: -10.00%

## Per-risk

| Risk | Gold | RRF R@5 | LTR R@5 | RRF R@20 | LTR R@20 |
|---|---:|---:|---:|---:|---:|
| cash_runway | 20 | 80.00% | 95.00% | 85.00% | 100.00% |
| continuous_loss | 10 | 60.00% | 100.00% | 100.00% | 100.00% |
| customer_concentration | 10 | 80.00% | 60.00% | 90.00% | 80.00% |
| material_litigation_compliance | 12 | 66.67% | 50.00% | 100.00% | 83.33% |
| precommercial_product | 10 | 10.00% | 10.00% | 20.00% | 50.00% |
| redemption_rights | 11 | 54.55% | 63.64% | 90.91% | 90.91% |
| revenue_growth | 10 | 10.00% | 70.00% | 50.00% | 100.00% |
| supplier_concentration | 10 | 100.00% | 90.00% | 100.00% | 100.00% |

## Case-level direction

| Case | RRF R@20 | LTR R@20 | Delta |
|---|---:|---:|---:|
| ipo_2022_01204 | 90.91% | 90.91% | 0.00% |
| ipo_2022_01406 | 80.00% | 80.00% | 0.00% |
| ipo_2022_02179 | 66.67% | 66.67% | 0.00% |
| ipo_2022_02372 | 88.89% | 100.00% | 11.11% |
| ipo_2022_02407 | 77.78% | 88.89% | 11.11% |
| ipo_2022_06698 | 77.78% | 88.89% | 11.11% |
| ipo_2022_06922 | 88.89% | 100.00% | 11.11% |
| ipo_2022_09638 | 66.67% | 88.89% | 22.22% |
| ipo_2022_09886 | 77.78% | 88.89% | 11.11% |
| ipo_2022_09985 | 88.89% | 100.00% | 11.11% |

Locked cases improved: 7

Tied: 3

Regressed: 0

Development → Locked generalization：Development 的 LTR 增益为 R@5 +8.51pp、R@20 +5.56pp；Locked 增益为 R@5 +9.68pp、R@20 +8.60pp。整体排序收益没有缩小，但两个 risk 出现超过 5pp 的局部回退。

## Frozen gates

- A_candidate_generalization: PASS
- B_ltr_r20: PASS
- C_top5: PASS
- D_completion: PASS
- E_case_direction: PASS
- F_per_risk: FAIL

Candidate generalization: **YES**
Ranking generalization: **MIXED**

候选泛化结论是 **YES**：BM25 + Table 在未参与开发的 10 篇 IPO 上仍将 Oracle@50 提高 13.98pp，并把完全漏检从 17 条降到 5 条。

排序泛化结论是 **MIXED**：总体 R@5、R@20、Completion 和全部 10 篇的 case-level 方向均通过；但预声明的 customer_concentration 回退 10.00pp，material_litigation_compliance 回退 16.67pp，因此不满足预注册的 per-risk Gate F，不能称为 FULL_PASS。

## Data governance

LOCKED VALIDATION:

Cases: 10

Opened: YES

Consumed: YES

Used for tuning before evaluation: NO

Can be reused as untouched final test: NO

## Disk

- Available disk before: 7.82 GiB
- Peak temporary disk: 1113.6 MiB
- Available disk after: 7.82 GiB
- Persistent new index: NO
- Model downloads: NO
- Temporary PDFs remaining: 0
- Temporary year ZIP remaining: 0
- Temporary directories: CLEAN

## 简单结论

最终考试没有完全通过。由于Locked 10已经正式打开并消费，不能再用它们调参后继续称为独立测试集；后续修改必须只使用Development并准备新的未见IPO作为最终验证。
