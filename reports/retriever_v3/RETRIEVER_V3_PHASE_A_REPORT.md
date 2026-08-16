# Retriever V3 Phase A Baseline Audit

PHASE R3-A RESULT:

PASS

Local annotations before deletion: 41 (40 IPO + real_case_001)

origin/main annotations: 60 IPO annotations (`real_case_001` excluded)

Local annotations after restore: 60

Historical Development: 40

New Development: 10

Locked Validation: 10

Locked metrics opened: NO

R3-0 source checks：60/60 JSON readable；60 unique case IDs；duplicate paths=0；年份分布为 2020=20、2021=20、2022=20；`real_case_001` excluded。

## 50-case Development baseline

| Retriever | R@1 | R@3 | R@5 | R@10 | R@20 | R@50 | Native Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | 20.83% | 42.01% | 48.61% | 54.34% | 59.72% | 66.15% | 66.15% |
| V2 | 20.83% | 39.41% | 47.22% | 55.03% | 63.37% | 70.31% | 71.53% |
| V21 | 21.18% | 38.54% | 49.65% | 56.08% | 62.67% | 69.27% | 71.88% |

Macro risk average: V1 R@20=56.68%, V2 R@20=59.96%, V21 R@20=59.63%

### Required Completion

| Retriever | Completion@5 | Completion@20 | Completion@50 |
|---|---:|---:|---:|
| V1 | 43.83% | 54.91% | 62.22% |
| V2 | 43.58% | 57.68% | 65.24% |
| V2.1 | 46.10% | 57.18% | 63.48% |

## Per-risk

| Risk | Gold | V1 R@20 | V2 R@20 | V2.1 R@20 | Best R@50 | Oracle@50 |
|---|---:|---:|---:|---:|---:|---:|
| cash_runway | 97 | 91.75% | 91.75% | 91.75% | 91.75% | 91.75% |
| continuous_loss | 53 | 49.06% | 50.94% | 50.94% | 54.72% | 56.60% |
| customer_concentration | 79 | 59.49% | 72.15% | 67.09% | 75.95% | 75.95% |
| material_litigation_compliance | 92 | 71.74% | 78.26% | 71.74% | 90.22% | 93.48% |
| precommercial_product | 67 | 10.45% | 14.93% | 25.37% | 43.28% | 44.78% |
| redemption_rights | 67 | 47.76% | 47.76% | 47.76% | 47.76% | 47.76% |
| revenue_growth | 53 | 45.28% | 41.51% | 41.51% | 77.36% | 83.02% |
| supplier_concentration | 68 | 77.94% | 82.35% | 80.88% | 86.76% | 86.76% |

### Per-risk Required Completion

| Risk | V1 C@20 | V2 C@20 | V2.1 C@20 | V1 C@50 | V2 C@50 | V2.1 C@50 |
|---|---:|---:|---:|---:|---:|---:|
| cash_runway | 84.00% | 84.00% | 84.00% | 84.00% | 84.00% | 84.00% |
| continuous_loss | 50.00% | 52.00% | 52.00% | 54.00% | 52.00% | 52.00% |
| customer_concentration | 56.00% | 64.00% | 60.00% | 58.00% | 66.00% | 68.00% |
| material_litigation_compliance | 60.00% | 68.00% | 60.00% | 76.00% | 86.00% | 68.00% |
| precommercial_product | 8.00% | 14.00% | 22.00% | 14.00% | 32.00% | 34.00% |
| redemption_rights | 51.06% | 51.06% | 51.06% | 51.06% | 51.06% | 51.06% |
| revenue_growth | 48.00% | 44.00% | 44.00% | 78.00% | 62.00% | 62.00% |
| supplier_concentration | 82.00% | 84.00% | 84.00% | 82.00% | 88.00% | 88.00% |

## CURRENT_STAGE1_CEILING

最佳单一 Retriever @50（V2）最多能找到：70.31%

最佳单一 native ceiling（V21）：71.88%

V1 + V2 合起来理论上能看到：73.78%

V1 + V2 + V2.1 合起来理论上能看到：74.65%

仍然三个系统全部找不到：144 条 Gold

Deterministic equal-weight RRF：R@5=50.35%，R@20=63.02%，R@50=73.44%。Oracle 仅表示覆盖上限，不是排序结果。

## Unique Gold contribution

- @20: V1 独有 2；V2 独有 19；V2.1 独有 10；三者全无 191。
- @50: V1 独有 18；V2 独有 7；V2.1 独有 5；三者全无 146。
- @native: V1 独有 18；V2 独有 0；V2.1 独有 2；三者全无 144。

## Failure taxonomy（50 Development only）

- RANKING_ONLY_MISS: 47
- QUERY_COVERAGE_MISS: 40
- SECTION_AUTHORITY_MISS: 21
- TABLE_FRAGMENTATION: 33
- MULTIPAGE_FRAGMENTATION: 20
- LEXICAL_VARIATION: 0
- NEIGHBOR_PAGE_MISS: 30
- BOILERPLATE_DISPLACEMENT: 0
- PARSER_OR_INPUT_MISS: 0
- UNKNOWN: 0

真正 Candidate Generation miss：144

Ranking-only：47

## 旧40与远程新版标注

- same hashes: 13
- changed hashes: 27
- changed case_ids: ipo_2020_00368, ipo_2020_01167, ipo_2020_01408, ipo_2020_02057, ipo_2020_02135, ipo_2020_06063, ipo_2020_06688, ipo_2020_06968, ipo_2021_00606, ipo_2021_01024, ipo_2021_01413, ipo_2021_01927, ipo_2021_02015, ipo_2021_02137, ipo_2021_02160, ipo_2021_02190, ipo_2021_02215, ipo_2021_02235, ipo_2021_02518, ipo_2021_03658, ipo_2021_06601, ipo_2021_06628, ipo_2021_06668, ipo_2021_06821, ipo_2021_09626, ipo_2021_09898, ipo_2021_09982
- new cases: 20

尽管27个旧 case 的 annotation 文件哈希变化，历史40 required-page 指标仍逐位复现旧报告（四舍五入到两位百分比）。加入10篇 New Development 后，V2仍是R@20/R@50最佳，V2.1仍是R@5最佳，旧结论没有明显变化。

## RECOMMENDED R3-B

#1 = BM25

依据：Development failure taxonomy 中最大可行动类为 QUERY_COVERAGE_MISS（40 条）；BM25 是最有机会覆盖这批固定短语查询未触达页面的首选。该数量是诊断上限，不是承诺收益。

#2 = Table（33 条严格表格碎片类 miss，作为独立后续 Lane）

## LOCKED VALIDATION

10 cases

Metrics opened: NO

Gold inspected for tuning: NO

Pattern mining: NO

## Reproducibility / storage

- PDF locatable: 60/60; missing=[]
- Retriever source hashes: `{"v1": "677259d5cf94b7bba19ed5ffb743c624795211d24882a25488f08ec15132609a", "v2": "4ff86be134ec88de2d62be5d381c9d7a8f45d689cd748a0cd0ed279430fcebe0", "v21": "e7c1214feb398b9e0e8263b5b598b1ce6288a2d1b0e3c7851ec522fbcd11412e"}`
- V2/V2.1 candidate_depth remained 20; V1 preserved its historical 50-page final universe; no bottom query was widened for Top100.
- Available disk before: 7.83 GiB
- Available disk after: 7.83 GiB
- Peak temporary usage: 1358.4 MiB
- Temporary PDFs remaining: 0
- Temporary ZIP copies remaining: 0
- Embedding/model downloads: 0

Push: NO

Remote GitHub modified: NO
