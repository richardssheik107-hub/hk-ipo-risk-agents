# Precommercial Product Candidate V2.3 Analysis

## V2.3 RESULT: FAIL

虽然 Route B 在两个没有参与调参的 locked IPO 中真正找回了专家页面，但 bounded union 同时挤掉了 3 条 locked 旧 Gold。Locked R@20、R@50 和净命中数都下降，因此 V2.3 不能保留为新版本。

## 1. Overall `precommercial_product`

Gold required evidence 共 56 条。

| Version | R@3 | R@5 | R@10 | R@20 | R@50 |
|---|---:|---:|---:|---:|---:|
| V1 | 3.57% | 5.36% | 7.14% | 10.71% | 16.07% |
| V2 | 3.57% | 3.57% | 5.36% | 14.29% | 37.50% |
| V2.1 | 8.93% | 10.71% | 16.07% | 26.79% | 44.64% |
| V2.2 | 8.93% | 10.71% | 19.64% | 30.36% | 50.00% |
| V2.3-B | 5.36% | 8.93% | 10.71% | 25.00% | 44.64% |

V2.3 没有优化 head；R@3/@5/@10 仅作为观察值。真正的失败是 Candidate R@20/@50 也下降。

## 2. Locked Validation（最重要）

Locked Gold 共 29 条。

| Version | R@20 | R@50 | Gold Found@20 | Gold Found@50 |
|---|---:|---:|---:|---:|
| V2.1 | 24.14% | 48.28% | 7 | 14 |
| V2.2 | 24.14% | 48.28% | 7 | 14 |
| V2.3-B | 20.69% | 44.83% | 6 | 13 |

最低 PASS 条件没有满足：

- Locked @20 没有提升，反而少 1 条；
- Locked @50 新找回 2 条，但同时丢失 3 条，净增益 −1；
- 两个 locked case 获益，满足 case diversity，但无法抵消回退；
- 全体 56 条中新增 3、丢失 6，净增益 −3。

## 3. Evidence Intent 分布

分类依据是 Evidence 在证明什么事实，而不是它恰好包含哪个短语。每条 Gold 只分配一个主 Intent。

| Intent | All Gold | V2.1 Top50 miss |
|---|---:|---:|
| `NOT_COMMERCIALISED` | 3 | 0 |
| `PRODUCT_LIFECYCLE` | 7 | 3 |
| `PRODUCT_REVENUE_EXISTS` | 13 | 10 |
| `SERVICE_REVENUE_EXISTS` | 22 | 10 |
| `REVENUE_NATURE` | 10 | 8 |
| `OTHER` | 1 | 0 |

V2.1 最大缺口属于 Route B：28/31 个 Top50 miss 是产品收入、服务收入或主营收入性质。Route A 的缺口是 3 条生命周期 evidence；显式 `NOT_COMMERCIALISED` evidence 在 V2.1 Top50 中没有 candidate miss。

### Authority

| Intent | Authority 分布 |
|---|---|
| `NOT_COMMERCIALISED` | business_section=1, financial_information=2 |
| `PRODUCT_LIFECYCLE` | business_section=7 |
| `PRODUCT_REVENUE_EXISTS` | accountants_report=10, business_section=3 |
| `SERVICE_REVENUE_EXISTS` | business_section=19, accountants_report=2, financial_information=1 |
| `REVENUE_NATURE` | accountants_report=5, business_section=5 |
| `OTHER` | other=1 |

Annotation 的 `section` 均不可用；默认 parser 也只给 `section="unknown"`。V2.3 没有把猜测章节冒充 Gold section，而是使用可见页文本、页面表格形态、结构化表 row 和 authority 统计。

## 4. V2.3 两条 Route

### Route A：Commercialisation status / lifecycle

复用现有 `commercialization_status` 与 `core_product_pipeline` family，并增加可解释的“产品概念 × 生命周期状态”页面发现。目标 Intent：

- `NOT_COMMERCIALISED`
- `PRODUCT_LIFECYCLE`

没有增加公司名、产品名、股票代码、case ID 或页码规则。

### Route B：Revenue / commercial activity

不再依赖 V2.2 的 10 个固定表头短语，改为组合：

- 现有 `revenue` query family；
- revenue 页面 + 财务表形态；
- parser 重建出的 structured revenue row；
- 收入/收费与产品销售、服务活动的组合信号；
- 商业活动页面。

目标 Intent：

- `PRODUCT_REVENUE_EXISTS`
- `SERVICE_REVENUE_EXISTS`
- `REVENUE_NATURE`

## 5. Variant 选择与冻结

只在 development 14 条 Gold 上选择版本。三个 variant 共用同一次 parse 和同一份 raw Route，不读取 locked PDF 选版。

| Variant | Top20 base/A/B | Top50 base/A/B | Dev R@20 | Dev R@50 | New/Lost@50 vs V2.2 |
|---|---|---|---:|---:|---:|
| A | 14/3/3 | 34/8/8 | 21.43% | 50.00% | 1/1 |
| B | 12/3/5 | 30/8/12 | 35.71% | 50.00% | 1/1 |
| C | 10/4/6 | 26/10/14 | 35.71% | 50.00% | 1/1 |

B 与 C 的 development Recall 完全相同。冻结 B，因为它比 C 多保护 4 个 V2.1 base slots，潜在回退风险更低。Locked 只对冻结的 B 正式评测一次。

## 6. Oracle / Ceiling：Route 没找到，还是 union 没保留？

Raw Route 每条最多 50 页，仅用于 oracle；最终用于 R@20/@50 的 global pool 始终硬限制为 50。

| Scope | Route A raw | Route B raw | Both | Raw union |
|---|---:|---:|---:|---:|
| historical_development | 2/13 | 7/13 | 1 | 8/13 |
| development | 2/14 | 4/14 | 0 | 6/14 |
| locked_validation | 7/29 | 11/29 | 5 | 13/29 |
| overall | 11/56 | 22/56 | 6 | 27/56 |

只看各 Route 的目标 Intent：

- Route A overall：6/10；locked：4/7。
- Route B overall：17/45；locked：8/21。

结论：两种问题都有。

1. **Route coverage 不足是主问题。** Locked 中 Route B 只覆盖 8/21 个目标 Gold，Route A 覆盖 4/7。
2. **Merge policy 也有问题。** Locked 最终 Top50 miss 中有 3 条已经被至少一个 raw Route 找到，却没有被 B 配额 union 保留。

## 7. 新找回与丢失

```text
V2.3 newly recovered gold: 3
locked newly recovered: 2
涉及 locked IPO: 2 个
lost previous gold: 6
net gold gain: -3

Route A 新找回: 0
Route B 新找回: 3
两 Route 都找到: 0
```

### 新找回

| case | split | page | intent | authority | route/family | old rank | new rank | why |
|---|---|---:|---|---|---|---:|---:|---|
| `ipo_2021_02015` | locked | 477 | PRODUCT_REVENUE_EXISTS | accountants_report | B / revenue_family | miss | 27 | Revenue route 找到车辆销售收入页，union 保留 |
| `ipo_2021_09898` | locked | 208 | SERVICE_REVENUE_EXISTS | business_section | B / commercial_activity | miss | 39 | 商业活动组合识别广告及营销服务收入 |
| `ipo_2021_06668` | development | 436 | REVENUE_NATURE | accountants_report | B / revenue_family | miss | 14 | Revenue route 找到持续经营业务收入页 |

### 被挤出的旧 Gold

| case | split | page | intent | V2.2 rank | V2.3 rank |
|---|---|---:|---|---:|---:|
| `ipo_2020_01961` | historical_development | 167 | PRODUCT_LIFECYCLE | 34 | miss |
| `ipo_2020_02263` | historical_development | 112 | SERVICE_REVENUE_EXISTS | 37 | miss |
| `ipo_2021_01024` | development | 633 | REVENUE_NATURE | 7 | miss |
| `ipo_2021_02160` | locked | 254 | PRODUCT_REVENUE_EXISTS | 50 | miss |
| `ipo_2021_06821` | locked | 197 | SERVICE_REVENUE_EXISTS | 36 | miss |
| `ipo_2021_09626` | locked | 197 | SERVICE_REVENUE_EXISTS | 46 | miss |

其中 locked 的 `ipo_2021_02160/p254` 和 `ipo_2021_09626/p197` 已被 raw Route 找到但没被 union 保留，是明确的 merge failure。`ipo_2021_06821/p197` 的邻页被 Route 找到，但 Gold 页本身没进入 raw Route。

## 8. Locked 仍未进入 Top50 的原因

Freeze 后只分类，不再据此调规则：

| Final miss reason | Count |
|---|---:|
| `candidate_merge_problem` | 3 |
| `lexical_mismatch` | 4 |
| `page_neighbour_problem` | 4 |
| `section_not_routed` | 3 |
| `table_parsing_problem` | 1 |
| `intent_not_covered` | 1 |

## 9. Candidate 数量与磁盘

| Pool | Average | Median | P95 | Max |
|---|---:|---:|---:|---:|
| V2.1 base | 39.18 | 50 | 50 | 50 |
| Route A raw oracle | 41.10 | 50 | 50 | 50 |
| Route B raw oracle | 50.00 | 50 | 50 | 50 |
| Raw dedup universe（仅 oracle） | 101.90 | 99 | 125 | 130 |
| V2.3 final bounded pool | 50.00 | 50 | 50 | 50 |

R@50 始终只在最终 50 页内计算，没有从 100–130 页 raw oracle universe 计算 Recall。

- 正式运行开始可用空间：8,411,942,912 bytes（7.83 GiB）。
- 最大临时占用：1,424,396,288 bytes（1.33 GiB，单个年度 ZIP + 当前 PDF）。
- 正式运行结束可用空间：8,411,942,912 bytes（7.83 GiB）。
- 临时目录：CLEAN。
- 没有保存 PDF、parsed text、chunks、candidate 全文或 A/B/C 完整 dump。

## 10. 普通话结论

这次**不只是又记住了开发集里的表达**：Route B 确实在两个 locked IPO 中找回了以前完全找不到的专家页面，说明“主动找收入及商业活动反证”是一个通用信号。

但机器还没有真正掌握一套稳定的新找法。原因是：Route A/B 本身仍漏掉大量目标 evidence，而且 bounded union 为新 Route 腾位置时丢掉了更多旧正确页面。结果是 locked 新增 2 条、丢失 3 条，整体变差。

**最终判定：FAIL，不推广、不注册、不继续调词。**

最多三个下一步候选方向（本轮不实施）：

1. 设计 preservation-aware union：在保证 raw Route 最小席位的同时，避免无条件淘汰 V2.1 已有高价值 base evidence。
2. 提升 Route B 的结构覆盖：改善 revenue table/segment/service-income 页面识别及邻页成组进入候选，而不是继续加固定表头短语。
3. 提升 Route A lifecycle coverage：利用可见 heading 与状态组合，重点处理注册、临床、批准、上市之间的阶段关系。
