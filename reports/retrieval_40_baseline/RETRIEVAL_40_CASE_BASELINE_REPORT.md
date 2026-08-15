# RETRIEVAL 40-CASE BASELINE REPORT

## Phase 0：仓库审计

- 当前入口：`ComponentRegistry` 中的 `keyword`，生产 V1 为 `KeywordDocumentRetriever`。
- V1：固定风险 query family + 确定性关键词/章节/财务表信号排序；输入为物理页 `DocumentChunk`，输出 `Evidence`。
- V2：研究态可执行 `DomainAwareRetrieverV2`；多语种领域 query、全局融合、邻页扩展、一次 completeness round。未注册为生产默认。
- V2.1：研究态可执行 `DomainAwareRetrieverV21`；不新增 V2 query，使用 family-capped RRF、V1 head anchor、邻页/round-2 头部限制与法律 boilerplate 降权。未注册。
- Candidate generation：V1 关键词后端及 `domain_aware_v2.py`/`domain_aware_v21.py` 的风险 query plans。
- Ranking/fusion：`keyword.py` 的确定性 score、V2 weighted global rank fusion、V2.1 lexicographic tiers + RRF。
- LLM reranker：`src/ipo_risk/retrieval/llm_reranker.py`；冻结 10-case candidate union/judgment 产物可复现，但本基准不调用 LLM。
- 现有 evaluator：`raw_retrieval_audit.py`、V2 four-case、V2.1 ten-case、LLM reranker rev4；本次沿用其物理页和全局去重排名语义并扩至 @50。
- expert annotations：发现 41 份（40 个 `ipo_*` + 1 个 `real_case_001`）；本基准评测 40 个 IPO，保留 real case 但不混入 40-case。
- 原始 retrieval input：PDF available=40，parsed text only=0，missing=0。PDF 从外层 ZIP 按 case 临时读取，未长期复制。
- 页码语义：严格匹配 PDF physical page / parser `page`；没有使用 ±1 容差。

## Phase 1：标注概况

- IPO 数：40
- risk annotation 数：320
- Evidence 数：632
- required：481
- supporting/supporting_only：147
- primary：372

### 各 risk Evidence

| risk_code | Evidence | 平均 gold pages/case |
|---|---:|---:|
| cash_runway | 85 | 1.95 |
| continuous_loss | 44 | 1.07 |
| customer_concentration | 81 | 1.77 |
| material_litigation_compliance | 132 | 2.70 |
| precommercial_product | 78 | 1.70 |
| redemption_rights | 93 | 2.20 |
| revenue_growth | 48 | 1.18 |
| supplier_concentration | 71 | 1.50 |

### source_authority 分布

`accountants_report`=222, `audited_financial_statement`=13, `business_section`=182, `corporate_structure`=20, `financial_information`=24, `legal_disclosure`=130, `other`=4, `pre_ipo_investment`=36, `summary`=1

### evidence_role 分布

`context`=12, `cross_check`=91, `primary`=372, `supporting`=157

### requirement 分布

`alternative`=4, `required`=481, `supporting_only`=147

## 一、40 篇整体结果（required evidence micro）

| Version | Recall@3 | Recall@5 | Recall@10 | Recall@20 | Recall@50 | Primary R@5* | Any-valid Hit@5* | Completion@5* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 | 40.33% | 47.19% | 54.05% | 59.67% | 65.90% | 48.39% | 58.75% | 41.25% |
| V2 | 36.59% | 44.70% | 53.64% | 63.20% | 69.85% | 45.16% | 56.25% | 40.00% |
| V21 | 37.84% | 49.48% | 55.51% | 62.16% | 69.02% | 51.61% | 62.81% | 45.62% |

\* 沿用现有 evaluator：Primary 是 Evidence-level micro；Any-valid/Completion 是全部 case×risk 的 macro。

### Macro-risk

| Version | R@3 | R@5 | R@20 | R@50 |
|---|---:|---:|---:|---:|
| V1 | 37.19% | 43.57% | 56.96% | 64.31% |
| V2 | 33.87% | 41.24% | 59.97% | 66.76% |
| V21 | 36.77% | 46.95% | 59.22% | 66.41% |

## 二、按 risk_code

| risk_code | Gold | V1 R@5 | V2 R@5 | V2.1 R@5 | V1 R@20 | V2 R@20 | V2.1 R@20 | V2.1 R@50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cash_runway | 77 | 84.42% | 84.42% | 76.62% | 92.21% | 92.21% | 92.21% | 92.21% |
| continuous_loss | 43 | 27.91% | 25.58% | 51.16% | 53.49% | 53.49% | 53.49% | 53.49% |
| customer_concentration | 69 | 50.72% | 43.48% | 52.17% | 56.52% | 69.57% | 63.77% | 73.91% |
| material_litigation_compliance | 79 | 55.70% | 51.90% | 55.70% | 72.15% | 78.48% | 72.15% | 78.48% |
| precommercial_product | 56 | 5.36% | 3.57% | 10.71% | 10.71% | 14.29% | 26.79% | 44.64% |
| redemption_rights | 56 | 33.93% | 33.93% | 41.07% | 48.21% | 48.21% | 48.21% | 48.21% |
| revenue_growth | 43 | 23.26% | 23.26% | 20.93% | 46.51% | 44.19% | 39.53% | 55.81% |
| supplier_concentration | 58 | 67.24% | 63.79% | 67.24% | 75.86% | 79.31% | 77.59% | 84.48% |

结论：V1 的 R@3 最高；V2 的 Candidate R@20/@50 最高；V2.1 的 R@5 最高。不存在一个版本在所有 cutoff 都胜出，V2.1 改善头部，但没有超过 V2 的深层 candidate recall。

### V2.1 按 source_authority

| source_authority | Required Gold | R@5 | R@50 |
|---|---:|---:|---:|
| accountants_report | 188 | 47.34% | 62.77% |
| audited_financial_statement | 12 | 41.67% | 50.00% |
| business_section | 143 | 55.24% | 81.12% |
| corporate_structure | 12 | 0.00% | 0.00% |
| financial_information | 18 | 16.67% | 44.44% |
| legal_disclosure | 79 | 55.70% | 78.48% |
| other | 1 | 0.00% | 100.00% |
| pre_ipo_investment | 28 | 64.29% | 75.00% |

`corporate_structure` 是完整候选缺口，`financial_information` 的头部排序也很弱。`business_section` 整体不差，但其中 `precommercial_product` 仍很差，说明 authority 汇总会掩盖 risk-specific 问题。

### V2.1 按 evidence_role

| evidence_role | Required Gold | R@5 | R@50 |
|---|---:|---:|---:|
| context | 1 | 0.00% | 100.00% |
| cross_check | 8 | 50.00% | 50.00% |
| primary | 371 | 51.75% | 72.24% |
| supporting | 101 | 41.58% | 58.42% |

### section 可用性

40 份 annotation 的 Evidence 均未提供 `section` 字段，因此不能诚实地计算 annotation-section recall；报告不使用 Retriever 猜测的 section 冒充 Gold section。`source_authority` 是本轮可用的章节代理。

## 三、V2.1 漏检原因

Top5 总漏检：243

- candidate_miss：149
- ranking_miss：94
- parser_or_input_miss：0
- partial_completion（正交标记）：52

| risk_code | candidate_miss | ranking_miss | parser/input | partial_completion |
|---|---:|---:|---:|---:|
| cash_runway | 6 | 12 | 0 | 10 |
| continuous_loss | 20 | 1 | 0 | 1 |
| customer_concentration | 18 | 15 | 0 | 11 |
| material_litigation_compliance | 17 | 18 | 0 | 18 |
| precommercial_product | 31 | 19 | 0 | 0 |
| redemption_rights | 29 | 4 | 0 | 6 |
| revenue_growth | 19 | 15 | 0 | 0 |
| supplier_concentration | 9 | 10 | 0 | 6 |

## 四、最差的 3 个 risk（V2.1 R@5，R@20 作 tie-break）

1. `precommercial_product`：R@5=10.71%，R@20=26.79%
2. `revenue_growth`：R@5=20.93%，R@20=39.53%
3. `redemption_rights`：R@5=41.07%，R@20=48.21%

## 五、旧版本改好了什么

### V1 → V2

- Candidate@50 gains：37
- Top5 gains：5
- Top5 regressions：17
- gains sample：ipo_2020_01167/customer_concentration/p294, ipo_2021_02137/material_litigation_compliance/p398, ipo_2021_02190/material_litigation_compliance/p366, ipo_2021_03658/material_litigation_compliance/p261, ipo_2021_06821/customer_concentration/p236
- regressions sample：ipo_2020_01167/continuous_loss/p416, ipo_2020_01942/material_litigation_compliance/p165, ipo_2020_01942/material_litigation_compliance/p165, ipo_2020_02135/customer_concentration/p244, ipo_2021_00606/customer_concentration/p222, ipo_2021_01024/material_litigation_compliance/p318, ipo_2021_01413/supplier_concentration/p187, ipo_2021_02015/customer_concentration/p292, ipo_2021_02015/material_litigation_compliance/p302, ipo_2021_02160/customer_concentration/p255, ipo_2021_02190/precommercial_product/p272, ipo_2021_03658/customer_concentration/p243
### V2 → V2.1

- Candidate@50 gains：6
- Top5 gains：35
- Top5 regressions：12
- gains sample：ipo_2020_00368/precommercial_product/p97, ipo_2020_01167/continuous_loss/p416, ipo_2020_01408/redemption_rights/p111, ipo_2020_01408/precommercial_product/p127, ipo_2020_01942/continuous_loss/p306, ipo_2020_01942/material_litigation_compliance/p165, ipo_2020_01942/material_litigation_compliance/p165, ipo_2020_02135/continuous_loss/p458, ipo_2020_02135/customer_concentration/p244, ipo_2020_02263/continuous_loss/p397, ipo_2020_02599/redemption_rights/p205, ipo_2020_06063/continuous_loss/p362
- regressions sample：ipo_2020_02263/customer_concentration/p165, ipo_2020_02599/cash_runway/p610, ipo_2020_02599/cash_runway/p612, ipo_2020_09901/cash_runway/p392, ipo_2021_02137/material_litigation_compliance/p398, ipo_2021_02190/material_litigation_compliance/p366, ipo_2021_03658/revenue_growth/p447, ipo_2021_03658/material_litigation_compliance/p261, ipo_2021_06601/cash_runway/p451, ipo_2021_06628/cash_runway/p555, ipo_2021_06628/cash_runway/p557, ipo_2021_09898/cash_runway/p398

## Candidate pool 深度说明

共 960 个 case×risk×version 排名中，700 个实际候选少于 50；@50 使用实际可获得最大池，不填充虚假候选。

## 六、数据切分建议

历史 V2/V2.1 与 LLM reranker 明确使用的 10 个 case 标为 `historical_development`；其余 30 个 case 用 case_id 的 SHA-256 固定排序，10 个 development、20 个 locked_validation。切分单位始终是 IPO。

| split | cases |
|---|---|
| historical_development | ipo_2020_00368, ipo_2020_01167, ipo_2020_01408, ipo_2020_01942, ipo_2020_01961, ipo_2020_02057, ipo_2020_02135, ipo_2020_02263, ipo_2020_02599, ipo_2021_00013 |
| development | ipo_2020_06618, ipo_2020_06900, ipo_2020_06968, ipo_2020_08489, ipo_2020_09600, ipo_2021_01024, ipo_2021_01927, ipo_2021_02518, ipo_2021_06601, ipo_2021_06668 |
| locked_validation | ipo_2020_03347, ipo_2020_06063, ipo_2020_06688, ipo_2020_09633, ipo_2020_09901, ipo_2020_09986, ipo_2021_00606, ipo_2021_01413, ipo_2021_02015, ipo_2021_02137, ipo_2021_02160, ipo_2021_02190, ipo_2021_02215, ipo_2021_02235, ipo_2021_03658, ipo_2021_06628, ipo_2021_06821, ipo_2021_09626, ipo_2021_09898, ipo_2021_09982 |

## 七、下一阶段建议

现在机器最主要的问题：**A. 根本找不到正确页面**。

最应该先修的 3 个 risk：

1. `precommercial_product`
2. `revenue_growth`
3. `redemption_rights`

下一阶段：**Candidate Generation**。

为什么：V2.1 Top5 漏检中 candidate_miss=149，ranking_miss=94；应按各 risk 在上表中的错误构成分别保护或改进。现金跑道等高 Recall risk 应作为 regression protection，不做无差别大改。

## 可复现性与限制

- Retriever source SHA-256（LF-normalized）：`{"v1": "677259d5cf94b7bba19ed5ffb743c624795211d24882a25488f08ec15132609a", "v2": "4ff86be134ec88de2d62be5d381c9d7a8f45d689cd748a0cd0ed279430fcebe0", "v21": "e7c1214feb398b9e0e8263b5b598b1ce6288a2d1b0e3c7851ec522fbcd11412e"}`。V2/V2.1 与历史冻结 hash 一致；V1 后续增加的 structured-table hook 在本轮普通 PyMuPDF chunks 上不触发。
- 历史 10-case inventory 与当前仓库相比有 5/10 annotation hash 不同；本报告是冻结 Retriever × 当前 40-case Gold 的统一重评，不冒充旧数字的逐位复现。
- 随机过程：无；切分使用固定 SHA-256 排序。
- benchmark 前 D: 可用空间：7.84 GiB；结束后：7.84 GiB。
- 未调用 LLM、未下载模型、未创建 embedding/vector cache、未保存 page/chunk/candidate 全文 dump。
- not_evaluable_cases：[]
- `exact_text` 仅在 CSV 保存 240 字符 preview；紧凑 JSON 不复制 preview。
