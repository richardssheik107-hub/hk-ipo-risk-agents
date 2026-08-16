# `precommercial_product` Candidate Recall 分析与 V2.2 第一轮结果

## 最简单的结论

**FAIL。** V2.2 在 development 找回了 3 条 required evidence，但在 locked validation 没有找回任何新 evidence。整体数字上升，却没有证明能泛化到未用于设计规则的 IPO，因此不应晋升为新的默认 Retriever。

实验代码只作为研究记录保留；它没有注册到生产组件、没有改变 V1/V2/V2.1，也没有修改 ranking。

## 1. 原来为什么找不到

`precommercial_product` 共有 **56** 条 required evidence。

| Version | R@3 | R@5 | R@10 | R@20 | R@50 |
|---|---:|---:|---:|---:|---:|
| V1 | 3.57% | 5.36% | 7.14% | 10.71% | 16.07% |
| V2 | 3.57% | 3.57% | 5.36% | 14.29% | 37.50% |
| V2.1 | 8.93% | 10.71% | 16.07% | 26.79% | 44.64% |
| V2.2 experiment | 8.93% | 10.71% | 19.64% | 30.36% | 50.00% |

V2/V2.1 的错误构成：

| Version | candidate miss（Top50 外） | ranking miss（已进 Top50、但 >5） | Top20 miss | Top50 miss |
|---|---:|---:|---:|---:|
| V2 | 35 | 19 | 48 | 35 |
| V2.1 | 31 | 19 | 41 | 31 |

31 条 V2.1 candidate miss 的 Gold 来源为：`accountants_report` 16 条、`business_section` 14 条、`financial_information` 1 条；其中 primary 24 条、supporting 7 条。Annotation 没有可用的 `section` 值，因此没有用 Retriever 猜测章节来冒充 Gold section。

逐条读取 Gold 页及必要邻页后，得到以下可解释分类：

| 原因 | 数量 | 典型表现 |
|---|---:|---|
| `product_sales_vocabulary_gap` | 8 | 产品、商品、软件或车辆已经销售，但用词不在原 query family 的有效候选头部 |
| `business_revenue_model_phrase_gap` | 5 | “收益主要来自”“产生收入”等业务收入来源叙述 |
| `revenue_disaggregation_heading_gap` | 4 | 会计师报告中的“收入分拆/明细”“货品或服务类型”表头 |
| `service_business_identity_gap` | 4 | 公司已经提供工程、教育、管理等服务，证据不是产品管线措辞 |
| `clinical_or_approval_stage_gap` | 3 | 二期研究、注册申请审核、待批准后商业化等阶段表达 |
| `business_stage_expression_gap` | 2 | 经营分部或物业销售等方式间接说明已运营 |
| `commercialisation_phrase_variation` | 2 | 已开始商业化或商业化阶段收入的变体 |
| `generic_revenue_counterevidence_gap` | 2 | 财务表仅给出“收入”及金额，词汇过于宽泛 |
| `multi_page_context` | 1 | Gold 页本身是财务结果，真正的收入来源短语在相邻页 |

主要规律不是只有“尚未商业化”的正面句式漏掉。约 28/31 条 candidate miss 实际是**反证**：公司已经销售产品、提供服务或产生收入。原 Retriever 偏向产品管线、研发和商业化状态词，对财务收入表及服务型公司的“已经在经营”表达覆盖不足。

完整小表见 `precommercial_product_candidate_misses.csv`。它只保存 240 字符 preview 和 evidence ID，没有复制完整 annotation 文本。

## 2. V2.2 具体改了什么

只根据 `historical_development + development` 中跨多个 IPO 重复的模式，冻结了 3 个小型 query family，共 10 个短语：

1. `commercial_revenue_source`：`收益主要來自`、`收入主要來自`、`收益源自`
2. `revenue_disaggregation_heading`：`收入分拆`、`收入明細`、`貨品或服務類型`、`商品或服務類型`
3. `product_or_goods_sales`：`產品銷售`、`銷售產品`、`商品收入`

每个 query 最多取 5 页，并允许直接页的前后 1 页进入候选。没有公司名、产品名、股票代码、case ID 或页码规则。

实现是严格 append-only：

- V2.1 原候选顺序全部保留；
- 只有 V2.1 候选少于 50 时才追加；
- 总候选仍硬限制为 50；
- 没有修改 fusion、family cap、head guard、score、source authority 权重或 LLM reranker；
- 其他 risk 完全委托给 V2.1，不改变结果；
- 实验 Retriever 未加入生产 registry。

## 3. 修改前后数字

V2 → V2.2：

- R@20：14.29% → 30.36%
- R@50：37.50% → 50.00%

更严格的直接前代 V2.1 → V2.2：

- R@20：26.79% → 30.36%，新增 2 条进入 Top20
- R@50：44.64% → 50.00%，新增 3 条进入 Top50
- 原有 evidence regression：0

候选规模：

| Version | 平均 candidate 数 | P95 | 硬上限 |
|---|---:|---:|---:|
| V2.1 | 39.18 | 50 | 50 |
| V2.2 | 42.75 | 50 | 50 |

平均增加 3.58 页（约 9.1%），没有无限膨胀。

### Split 结果

| Split | Gold | V2.1 R@20 | V2.2 R@20 | V2.1 R@50 | V2.2 R@50 |
|---|---:|---:|---:|---:|---:|
| historical_development | 13 | 38.46% | 38.46% | 53.85% | 53.85% |
| development | 14 | 21.43% | 35.71% | 28.57% | 50.00% |
| locked_validation | 29 | 24.14% | 24.14% | 48.28% | 48.28% |

所有 3 条增益都来自 development；historical 和 locked 都是 0 增益。这是本轮 FAIL 的决定性原因。

## 4. 新找回的 Evidence

本轮实际只新找回 3 条，因此不能列出 5–10 条；以下完整列出全部增益：

| case | page | 旧版本为什么没找到 | V2.2 为什么找到 |
|---|---:|---|---|
| `ipo_2020_06618` | 447 | V2.1 没覆盖会计师报告中的收入细分表头，且原候选仅 31 页 | `商品或服務類型` 直接命中，V2.2 rank 39 |
| `ipo_2021_01024` | 633 | Gold 是直播、线上营销及其他服务收入明细，原候选仅 3 页 | `收入明細` query family 命中，V2.2 rank 7 |
| `ipo_2021_02518` | 146 | Gold 页主要是净收益数字，收入来源表达在相邻页 | `收益源自` 命中邻页，±1 扩展带回 Gold，V2.2 rank 8 |

## 5. Promotion gate 判定

| Gate | 结果 |
|---|---|
| 整体 R@20 高于 V2/V2.1 | 满足 |
| 整体 R@50 高于 V2/V2.1 | 满足 |
| 多个不同 case 获益 | 满足，3 个 case |
| locked validation 有稳定增益 | **不满足，0 个新命中** |
| parser/input regression | 满足，parser errors=0；V2.1 重跑与基准 0 mismatch |
| candidate 数量受控 | 满足，P95=50，硬上限 50 |

**最终判定：FAIL。** 当前短语对开发集中的稀疏候选池有效，但没有在 locked validation 复现。不能因为整体指标变好就把它当作稳定的新版本，也不应继续查看 locked 错误后无止境加词。

下一步不应立即开始 `revenue_growth`，也不应把这一版升级为默认。若未来重新处理 `precommercial_product`，更值得研究的是不依赖个别固定表头的、可解释的“已产生产品/服务收入”结构化 Candidate Generation，并重新准备真正未暴露的 case-level validation。

## 6. 可复现性、磁盘与限制

- 正式结果：`precommercial_product_v22_results.json`，保存 56 条紧凑 rank/provenance，不保存候选全文。
- 正式冻结运行：56 条 Gold；@50 gains=3，regressions=0；V2.1 baseline mismatches=0；parser errors=0。
- 正式运行前 D: 可用空间：8,412,377,088 bytes（7.83 GiB）。
- 正式运行后 D: 可用空间：8,412,344,320 bytes（7.83 GiB）。
- 临时目录：已删除，无 `.tmp_precommercial_v22_*` 残留。
- 没有复制 PDF 数据集、保存 parsed text/chunks、创建 embedding cache/vector DB、下载模型或生成 candidate 全文 dump。
- 严格盲法限制：继承的 40-case baseline 本身已经包含 locked rank/preview；本轮 query 只使用 historical/development 重复模式冻结，locked 仅运行冻结实现，且没有根据 locked 结果修改规则。中途曾因外部暂停中止，未生成结果；恢复后以同一冻结配置操作性重跑。
