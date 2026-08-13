# HK IPO Risk Agents 项目主计划

> 审核版本：v0.3 正式发布冻结版
>
> 正式发布基线：`v0.2.0-real-document-slice@916df5d`，2026-08-06
>
<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>当前正式基线</strong></p>
<p>v0.2.0 已于2026-08-06正式发布，Tag为 v0.2.0-real-document-slice，冻结提交为 916df5d。远程 main 全新克隆、Python 3.12.10 虚拟环境安装、284 项测试、项目校验、赛事数据校验、编译检查和 2410.HK 真实 E2E 全部通过；第562/563页已完成第二次独立证据复核。当前进入v0.3.0真实多Agent文档风险分析。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

| **项目**       | **当前状态**                             |
|:---------------|:-----------------------------------------|
| v0.1.0         | 架构级MVP已发布                          |
| v0.2.0代码     | 已全部进入main                           |
| v0.2.0 Release | 已发布：Tag `v0.2.0-real-document-slice` |
| v0.3.0 Release | 已发布：Tag `v0.3.0-multi-agent-risk-analysis` |
| 下一规划版本   | v0.4市场预测（尚未开始）                 |
| 远期版本       | v0.4市场预测、v0.5正式评测、RC与v1.0提交 |

适用对象：5人参赛团队 / 技术负责人 / 数据治理 / 财务 / 法务 / 业务与产品

# 0. 当前权威状态快照

本文件是项目进度的唯一主入口。README和ROADMAP只保留摘要；Gate A的专项PASS/FAIL门槛由`V03_GATE_A_CLOSEOUT.md`维护并链接回本文件。

| 项目 | 当前事实 |
| --- | --- |
| 功能状态基线 | PR #39与PR #40合并后的v0.3发布主线 |
| 当前验证 | 900项测试、Mock健康检查、赛事数据校验、Golden integrity、2410.HK真实回归与`enhanced_v2`验收通过 |
| 稳定回退基线 | `v0.2.0-real-document-slice@916df5d442030e3443249a881f995b5d039a5b33` |
| v0.2真实回归 | 706页、0解析错误、Evidence第563/562页、2.76个月、verified、90/critical |
| v0.3当前阶段 | **RELEASED / FROZEN** |
| 当前稳定工作流 | `mvp_v1`继续兼容；`enhanced_v2`已完成 |

上述SHA是本轮文档状态核验所依据的功能实现基线，不要求等于本文档PR合并后的`main` HEAD。

## 0.1 Workstream状态

| Workstream | Status | Main evidence | Remaining gate |
| --- | --- | --- | --- |
| Planner → Executor | COMPLETED / MERGED | PR #21 | 每一棒继续使用独立Approved Plan |
| V3-1 Golden Cases | COMPLETE / FORMAL-EVALUATED | 23行Financial与3行Business具名一审正式晋级；8行Legal双审/仲裁保持 | 维护审计与回归 |
| V3-2 Catalog Provider | COMPLETE / REGISTERED | PR #20 + final integration | 单文档配置可选择`request`或`catalog` |
| V3-3 Retriever | COMPLETED / MERGED | PR #23 | 复核后真实金标评测 |
| V3-4 LLMProvider | COMPLETE / INTEGRATED | PR #24、#32 + final integration | 可选安全外部smoke尚未执行 |
| V3-5 Financial core | COMPLETE / INTEGRATED / FORMAL-GOLDEN | PR #22 + final integration | 23条`first_reviewed`正式评测 |
| V3-6 Legal | INTEGRATED / FORMAL-GOLDEN-PROMOTED | PR #26 + final integration | 已进入共享runtime |
| V3-7 Business | COMPLETE / INTEGRATED / FORMAL-GOLDEN | PR #28 + final integration | 3条`first_reviewed`正式评测 |
| V3-8 Specialized Verifier | COMPLETE | [Owner Waiver](V03_OWNER_WAIVER_FOR_FINAL_TECHNICAL_COMPLETION.md) + final integration | 专业规则路由与失败隔离已集成 |
| V3-9 Supervisor / enhanced_v2 | COMPLETE | final integration | `mvp_v1`兼容保留 |
| V3-10 batch/evaluation infrastructure | MERGED | PR #20 | 复核后的真实黄金批量评测 |
| V3-11 UI / Report | COMPLETE | v0.3 Streamlit + Markdown/JSON | PDF导出不在本版范围 |
| V3-12 Hardening / Release | COMPLETE / RELEASED | `v0.3.0-multi-agent-risk-analysis` | v0.3冻结；不在该版本继续开发 |

# 1. 项目总体目标与当前基线

项目目标是构建一个证据驱动的港股IPO招股书解析与上市后风险预警系统。系统以招股书PDF为核心输入，将文档解析、证据检索、专业Agent分析、确定性计算、Verifier核验、Supervisor协同和市场预测逐层组合。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>最终完整链路</strong></p>
<p>招股书PDF → Parser → Retriever → Financial / Legal / Business Agent → Skills → Verifier → Supervisor → IPO与市场数据 → Market Agent / Predictor → Evidence化报告与风险预警。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 1.1 当前能力边界

- Financial、Legal与Business三个真实Agent已合并并进入共享Container与`enhanced_v2`；旧流程仍保留disabled/Mock回退。
- Market Agent和正式MarketDataProvider尚未接入。
- LLMProvider基础设施与Legal domain prompt real-provider runtime routing均已合并，GATE-A-10为PASS；真实外部endpoint smoke仍未执行。
- `V03FinancialAgent`、`V03FinancialVerifier`及其他专业组件既可独立调用，也已进入共享Container/Workflow/Service。
- `CatalogIPODataProvider`已进入全局ComponentRegistry；默认v0.3单文档配置仍使用请求字段，避免缺失catalog阻断分析。
- 当前规则风险分不是经过校准的上市后下跌概率。
- 1/5/20/60交易日标签、Logistic和LightGBM模型尚未建立。

## 1.2 数据基线

| **数据范围** | **数量** | **用途**                 |
|:-------------|:---------|:-------------------------|
| 2020—2023    | 376份    | 开发集                   |
| 2024         | 72份     | 验证集                   |
| 2410.HK      | 1份      | v0.2开发例外             |
| 2025         | 116份    | 盲测集，禁止调规则或调参 |
| 全部招股书   | 565份    | 文档分析主宇宙           |
| 有日行情覆盖 | 555份    | 未来市场标签候选         |
| 无日行情覆盖 | 10份     | 仅文档链路与降级测试     |

# 2. 更新后的版本总路线图

| **版本** | **核心问题** | **主要交付物** | **当前状态** |
|:---|:---|:---|:---|
| v0.1.0 | 系统架构能否完整运行 | 统一Schema、Mock组件、LangGraph、Service、UI、测试 | 已发布 |
| v0.2.0 | 能否从真实PDF得到一条可信风险 | 真实现金跑道闭环、赛事数据治理、影子测试 | 已正式发布 |
| v0.3.0 | 能否进行真实多Agent文档风险分析 | 3个真实Agent、8类风险、共享runtime与产品UI | RELEASED / FROZEN / HUMAN GOLDEN COMPLETE |
| v0.4.0 | 文档风险能否连接上市后真实表现 | 行情、标签、Market Agent、Logistic、LightGBM | 待规划 |
| v0.5.0 | 系统效果是否经过正式证明 | 20—30家公司、200—300条标注、消融与失败分析 | 待规划 |
| 提交准备 | 如何形成参赛产品 | 页面、报告、PPT、视频、手册 | 待规划 |
| RC | 别人能否稳定复现 | 冻结、独立环境、异常测试、离线演示 | 待规划 |
| v1.0.0 | 正式参赛提交 | 完整源码、模型、结果和材料包 | 待规划 |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>路线原则</strong></p>
<p>v0.2解决“读得出来并算得正确”；v0.3解决“分专业分析得全面”；v0.4解决“连接市场并预测”；v0.5解决“证明系统有效”；随后完成产品化、RC冻结和正式提交。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 3. 当前稳定基线

| **项目** | **值** |
|:---|:---|
| Release | `v0.2.0-real-document-slice` |
| 冻结提交 | `916df5d442030e3443249a881f995b5d039a5b33` |
| 自动测试 | 284 passed |
| 真实回归 | 2410.HK第563/562页，现金跑道2.76个月，verified，90/critical |

v0.3开发必须保持该Tag可回退、Mock模式可运行、2410.HK真实E2E不回归。

# 4. v0.3.0总体设计

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>版本名称</strong></p>
<p>v0.3.0-multi-agent-risk-analysis</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

v0.3的唯一目标是：将当前单一现金跑道真实闭环，升级为Financial、Legal、Business三个真实Agent协同运行，并在5—10份真实招股书上完成可重复的多案例评测。

## 4.1 最终运行流程

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>PDF上传<br />
↓<br />
Parser：一次解析，生成带物理页码的DocumentChunk<br />
↓<br />
Retriever：按财务、法务、业务查询族寻找Evidence<br />
↓<br />
Financial / Legal / Business Agent：提取结构化事实<br />
↓<br />
Skills：完成精确计算<br />
↓<br />
RiskItem(pending)<br />
↓<br />
专用Verifier：verified / needs_review / rejected<br />
↓<br />
Supervisor：去重、冲突识别、组合风险和降级<br />
↓<br />
规则风险评分、报告、Repository和Streamlit展示</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 4.2 v0.3明确不做

- 不训练Logistic、LightGBM或深度学习市场预测模型

- 不输出经过校准的真实下跌概率

- 不正式构造上市后1/5/20/60日标签

- 不实现完整Market Agent

- 不使用2025盲测集调规则、选特征或调参

- 不把565份PDF全部人工标注

- 不引入微服务、Kafka、Redis、Neo4j或Kubernetes

- 不让LLM完成精确财务计算或直接决定最终分数

# 5. v0.3正式风险目录

| **序号** | **风险代码** | **风险名称** | **Agent** | **核心方法** |
|:---|:---|:---|:---|:---|
| 1 | cash_runway | 现金跑道不足 | Financial | v0.2已有，保持回归 |
| 2 | continuous_loss | 持续亏损 | Financial | 表格提取 + 亏损趋势Skill |
| 3 | revenue_growth | 收入增长异常或放缓 | Financial | 期间对齐 + 增长率Skill |
| 4 | customer_concentration | 客户集中度过高 | Financial | 占比提取 + 规则；Business仅提供依赖事实 |
| 5 | supplier_concentration | 供应商集中度过高 | Financial | 占比提取 + 规则；Business仅提供依赖事实 |
| 6 | redemption_rights | 赎回权及特殊股东权利 | Legal | 检索 + LLM候选提取 + 规则 |
| 7 | material_litigation_compliance | 重大诉讼与合规 | Legal | 语义提取 + 重大性与状态核验 |
| 8 | precommercial_product | 未商业化及核心产品依赖 | Business | 业务事实提取 + 规则 |

## 5.1 RiskItem统一要求

- 所有正式风险必须具有Evidence，包含物理页码和原文。

- 涉及数字的风险必须具有Calculation，记录输入、公式、结果、单位和Evidence ID。

- Agent生成的候选风险初始状态为pending，不能自我宣布verified。

- Verifier决定verified、needs_review或rejected。

- 无证据、计算失败、币种/单位/期间冲突的风险不得进入正式评分。

- 规则型或条款型风险可不包含Calculation，但必须有足够Evidence。

# 6. v0.3分棒任务清单

| **棒次** | **唯一任务** | **主要输出** | **负责人** | **验收重点** |
|:---|:---|:---|:---|:---|
| V3-0A（已完成） | 冻结v0.3范围与路线 | 以本文件替换旧版总清单，并同步README、ROADMAP和CHANGELOG；冻结接力顺序和退出门槛。 | 技术负责人 | 文档范围与发布基线一致。 |
| V3-0B（已完成） | 冻结开发契约 | 冻结角色输入输出、唯一风险所有权、候选模型、诊断、Supervisor和LLMProvider契约；新增兼容Schema和契约测试。 | 技术负责人 | 公共接口只做带默认值的兼容扩展；全量回归通过。 |
| V3-1（COMPLETE） | 黄金案例与标注规范 | Financial/Business具名一审按当前政策晋级；Legal A—H正式双审、仲裁保持。 | 财务/法务/业务 | 2025盲测不得进入调优。 |
| V3-2（COMPLETE / REGISTERED） | IPO基础信息Provider | `CatalogIPODataProvider`、特殊证券治理和全局注册已完成。 | 技术备份/数据 | 单文档默认仍可使用请求字段。 |
| V3-3（COMPLETED / MERGED） | Retriever查询族泛化 | 八类查询族、简繁英、章节权重与稳定Evidence已合并。 | 技术负责人 | 复核后真实金标评测。 |
| V3-4（COMPLETE / INTEGRATED） | 可替换LLMProvider | Mock、OpenAI-compatible、Unavailable Provider及Legal domain prompt runtime routing已合并。 | 技术负责人 | 可选安全外部smoke尚未执行。 |
| V3-5（COMPLETE / INTEGRATED / FORMAL-GOLDEN） | Financial Agent扩展 | 五类Financial风险、抽取、Skills、Verifier、共享装配与正式评测已完成。 | 财务成员 | 维护回归。 |
| V3-6（COMPLETE / INTEGRATED / FORMAL-GOLDEN） | Legal Agent真实化 | 两类风险、失败隔离、Prompt、Verifier、共享装配与8条正式reviewed Golden均已完成。 | 法务成员+技术负责人 | 维护回归。 |
| V3-7（COMPLETE / INTEGRATED / FORMAL-GOLDEN） | Business Agent真实化 | `precommercial_product`正/负例闭环、共享装配与正式评测已完成。 | 业务成员 | 维护回归。 |
| V3-8（COMPLETE） | 专用Verifier体系 | Domain/risk-code路由、契约核验与失败隔离已完成。 | 技术负责人+专业成员 | 维护回归。 |
| V3-9（COMPLETE） | Supervisor与enhanced_v2 | 多Agent去重、冲突识别、跨域综合、失败降级和共享工作流已完成。 | 技术负责人 | 保留`mvp_v1`兼容。 |
| V3-10（INFRASTRUCTURE MERGED） | 批量运行与评测 | 批量、resume、blind guard和评测框架已合并。 | 技术备份/数据 | 复核后真实黄金批量评测。 |
| V3-11（COMPLETE） | Streamlit与报告 | IPO画像、Dashboard、三Agent、证据、Calculation、核验、Supervisor、诊断及Markdown/JSON。 | 业务/产品+技术 | PDF报告不在v0.3范围。 |
| V3-12（COMPLETE / RELEASED） | 发布加固 | 完整测试、真实回归、文档同步与安全检查。 | 全组 | Tag `v0.3.0-multi-agent-risk-analysis`。 |

# 7. 黄金案例与人工标注计划

## 7.0 当前Manifest审计

对`tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`的实际统计：

| 指标 | 当前值 |
| --- | ---: |
| 总行数 | 37 |
| synthetic rows | 3 |
| real rows | 34 |
| unique real cases/documents | 14 |
| review_status=first_reviewed | 26（23条Financial、3条Business） |
| review_status=double_reviewed | 7（3条synthetic、4条Legal） |
| review_status=adjudicated | 4（全部Legal） |
| review_status=draft | 0 |
| second_reviewer为空 | 26（`first_reviewed`政策预期，不伪造二审） |
| 全部risk_code覆盖 | 8/8 |
| 真实risk_code覆盖 | 8/8（Financial五类、Business一类、Legal两类） |

canonical Manifest中的真实Financial覆盖五类风险，Business覆盖`precommercial_product`，
均按Owner于2026-08-12冻结的`single_named_human_review_v1`以`first_reviewed`
正式晋级。Legal A—H原有4条`double_reviewed`和4条`adjudicated`保持不变。
一审政策不等于独立双审；`second_reviewer`继续为空且不得伪造。

## 7.1 推荐案例构成

| **案例类型**           | **建议数量** | **主要覆盖风险**                       |
|:-----------------------|:-------------|:---------------------------------------|
| 18A未商业化生物科技    | 2            | 未商业化、核心管线、持续亏损、现金跑道 |
| 持续亏损但已有收入公司 | 1—2          | 持续亏损、收入增长、现金消耗           |
| 高客户集中度公司       | 1            | 客户集中度、业务依赖                   |
| 高供应商集中度公司     | 1            | 供应商集中度、经营稳定性               |
| 特殊股东权利案例       | 1            | 赎回权、清算优先权、反摊薄等           |
| 重大诉讼或合规案例     | 1            | 诉讼、处罚、牌照或整改状态             |
| 相对低风险对照案例     | 1—2          | 负例、误报控制                         |

## 7.2 每条金标准必须包含

- case_id和股票代码

- risk_code及是否适用

- 标准风险等级或不适用原因

- 物理PDF页码和章节

- 支持原文

- 金额、比例、币种和单位

- 报告期与期间长度

- 标准Calculation

- 标准verification_status

- 第一标注人、第二复核人和分歧记录

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>重要原则</strong></p>
<p>“没有找到证据”不等于“风险不存在”。黄金案例必须区分 not_applicable、evidence_not_found、extraction_failed、conflicting_values、needs_review 和 component_failure。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 8. 三类真实Agent的实现边界

| **Agent** | **主要职责** | **优先实现方式** | **禁止事项** |
|:---|:---|:---|:---|
| Financial | 现金、亏损、收入、客户和供应商集中度 | 规则、表格解析、Decimal Skill为主 | 不得用LLM做精确计算 |
| Legal | 特殊股东权利、诉讼、处罚和合规 | 关键词检索 + LLM结构化提取 + 规则核验 | 不得仅凭章节标题判风险 |
| Business | 商业化状态、产品、管线和合作依赖 | 规则/LLM混合提取 + 业务规则 | 不得重复计算财务指标 |
| Verifier | 检查证据、数值、条款状态和结论 | 确定性规则为主 | 不得放过无证据正式风险 |
| Supervisor | 去重、冲突、组合摘要和失败降级 | 确定性规则，LLM仅可选摘要 | 不得创造新事实或新证据 |

## 8.1 LLM在v0.3中的正确位置

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>Retriever选出5—10段相关Evidence<br />
↓<br />
LLM只提取结构化候选事实<br />
↓<br />
Pydantic校验<br />
↓<br />
Python Skill / 规则判断<br />
↓<br />
Verifier核验<br />
↓<br />
正式RiskItem</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

不应把整份数百页PDF直接交给通用大模型，也不应让大模型直接生成最终分数。没有API Key时，财务确定性链路和部分规则型法务/业务链路仍应运行。

# 9. enhanced_v2工作流与失败语义

## 9.1 建议工作流

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>load_ipo_profile<br />
→ load_market_snapshot<br />
→ document<br />
→ financial<br />
→ legal<br />
→ business<br />
→ market<br />
→ specialized_verifiers<br />
→ supervisor<br />
→ predictor<br />
→ report<br />
<br />
Repository不进入LangGraph；IPOAnalysisService在工作流返回后负责持久化。</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 9.2 必须保留的兼容性

- 保留mvp_v1，不删除v0.1/v0.2工作流。

- 保留Mock实现，Mock与真实实现通过配置切换。

- 不改变专业Agent统一返回list\[RiskItem\]的公共契约。

- 不改变IPOAnalysisService对外返回IPOAnalysisResult的契约。

- 公共Schema新增字段优先提供默认值，避免破坏旧结果。

- Repository由IPOAnalysisService在工作流完成后调用；必须能够读取旧结果并记录schema_version。

## 9.3 v0.3内部结构化诊断码

| **诊断码** | **含义** | **前端/评测处理** |
|:---|:---|:---|
| not_applicable | 该风险对当前文档或证券不适用 | 不计为漏报 |
| evidence_not_found | 未找到足够证据 | 显示检索失败，不能当作无风险 |
| extraction_failed | 找到了候选页但提取失败 | 记录失败原因 |
| conflicting_values | 存在相互冲突的金额、单位或期间 | 进入needs_review |
| unsupported_layout | 跨页表格或版式超出当前能力 | 记录能力边界 |
| component_failure | Agent、Provider或Skill异常 | 整体可返回partial |
| needs_review | 有证据但结论存在歧义 | 人工复核，不进入满额评分 |

# 10. v0.3多案例评测体系

| **评测层级** | **核心指标** | **建议退出门槛** |
|:---|:---|:---|
| Retriever | Recall@1、Recall@3、Recall@5、主证据页命中率 | 主证据Recall@3 ≥ 90% |
| Extractor | 金额、比例、币种、单位、期间准确率 | 确定性数值准确率 ≥ 95% |
| Agent | RiskItem Precision、Recall、F1、误报与漏报 | 核心风险可稳定复现 |
| Verifier | verified precision、错误拒绝率、needs_review合理性 | verified precision ≥ 90% |
| Supervisor | 重复风险数、冲突处理正确率、证据覆盖率 | 无明显重复与无证据综合结论 |
| 系统 | 案例完成率、partial比例、Agent失败率、平均耗时 | 黄金案例完整运行率100%，崩溃0 |
| 回归 | 2410.HK现金跑道和Mock模式 | 结果100%保持 |

## 10.1 批量输出文件

- analysis_results.jsonl

- risk_items.csv

- evidence_results.csv

- case_summary.csv

- failure_report.csv

- evaluation_metrics.json

## 10.2 数据泄漏防线

- 2025年116份盲测案例默认禁止批量运行和调试。

- v0.3只分析招股书中的文档风险，不使用上市后行情作为特征。

- 2024验证集不用于反复修改黄金规则；只用于时间外验证。

- 任何提示词、规则和阈值的修改必须记录版本。

# 11. 五人团队分工

| **成员角色** | **v0.3主责任** | **关键产出** | **避免事项** |
|:---|:---|:---|:---|
| 1号 技术负责人 | 架构、Retriever、LLM接口、Verifier、Supervisor、Workflow和发布 | 公共接口审查、集成PR、版本冻结 | 不要独自承担全部专业标注 |
| 2号 技术备份/数据 | IPO Provider、特殊证券、批量运行、评测和独立复跑 | Provider、评测脚本、部署记录 | 不要修改核心Workflow边界 |
| 3号 财务成员 | 持续亏损、收入增长、客户和供应商集中度 | 财务黄金案例、Skills、规则和测试 | 不要在前端计算财务指标 |
| 4号 法务成员 | 特殊股东权利、诉讼合规和第二复核 | 法律词典、标注、Legal Verifier规则 | 不要把一般性风险提示当成已发生事实 |
| 5号 业务/产品 | 未商业化、核心产品依赖、UI和报告验收 | 业务黄金案例、页面原型、演示材料 | 不要直接调用Agent或LLM |

## 11.1 受保护的共享边界

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>src/ipo_risk/schemas/<br />
src/ipo_risk/agents/base.py<br />
src/ipo_risk/parsers/base.py<br />
src/ipo_risk/retrieval/base.py<br />
src/ipo_risk/providers/<br />
src/ipo_risk/core/container.py<br />
src/ipo_risk/domain/risk_codes.py<br />
src/ipo_risk/workflows/<br />
src/ipo_risk/services/</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

这些文件由技术负责人统一集成，多个成员不得在不同分支同时进行大范围重写。

# 12. 分支、接力顺序与阶段里程碑

## 12.1 建议分支

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>docs/v03-master-plan<br />
feat/v03-golden-cases<br />
feat/catalog-ipo-provider<br />
feat/retrieval-query-families<br />
feat/llm-provider<br />
feat/financial-multi-risk-agent<br />
feat/legal-risk-agent<br />
feat/business-risk-agent<br />
feat/v03-risk-verifiers<br />
feat/enhanced-v2-workflow<br />
feat/v03-batch-evaluation<br />
feat/v03-reporting-ui<br />
fix/v03-release-validation</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 12.2 建议阶段节奏

| **阶段** | **主要任务** | **可并行事项** | **阶段出口** |
|:---|:---|:---|:---|
| 第1阶段 | R0发布收尾 + V3-0计划冻结 | 文档复核、独立复跑 | v0.2正式Release |
| 第2阶段 | V3-1黄金案例 + V3-2 IPO Provider | 财务/法务/业务标注可并行 | 案例和基础信息可稳定加载 |
| 第3阶段 | V3-3 Retriever + V3-4 LLMProvider | 词典和Prompt设计 | 三类Evidence查询可运行 |
| 第4阶段 | V3-5/6/7三个真实Agent | 专业Agent可分支并行 | 每个Agent完成最小风险闭环 |
| 第5阶段 | V3-8 Verifier + V3-9 Supervisor/Workflow | Verifier规则复核 | 完整单案例多Agent闭环 |
| 第6阶段 | V3-10批量评测 + V3-11 UI/报告 | 评测与页面可并行 | 5—10案例评测完成 |
| 第7阶段 | V3-12发布加固 | 独立复跑、材料同步 | v0.3正式Release |

# 13. 每一棒统一验收命令

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>pytest -q<br />
python scripts/validate_project.py<br />
python scripts/validate_competition_data.py<br />
python -m compileall -q app src<br />
git diff --check</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

涉及真实PDF时增加：

| python scripts/check_real_v02_e2e.py |
|--------------------------------------|

v0.3批量评测完成后增加：

| python scripts/evaluate_v03_golden_cases.py |
|---------------------------------------------|

## 13.1 每一棒汇报模板

- 创建了哪些文件

- 修改了哪些文件

- 实现了哪些功能

- 是否影响公共接口

- 执行了哪些测试及结果

- 如何启动和复现

- 当前仍使用哪些Mock或Unavailable组件

- 已知限制

- 下一棒的明确输入

# 14. v0.4及后续版本计划

## 14.1 v0.4.0-market-risk-prediction

| **编号** | **任务** | **主要输出** |
|:---|:---|:---|
| V4-1 | 证券类别、上市日期和发行价语义治理 | 普通股/REIT/SPAC/权证资格与时间边界 |
| V4-2 | 正式MarketDataProvider | 按证券和交易日读取OHLCV |
| V4-3 | 上市后标签 | 首日、5日、20日、60日收益、破发和回撤 |
| V4-4 | 上市前市场特征 | 恒指、行业、近期IPO、波动率和市场活跃度 |
| V4-5 | 真实Market Agent | 上市前市场风险Evidence和MarketSnapshot |
| V4-6 | 模型基线 | Rule、Logistic和LightGBM |
| V4-7 | 时间外验证 | 2020—2023开发、2024验证 |
| V4-8 | 最终盲测 | 2025一次性评估，不再调参 |

## 14.2 v0.5.0-evaluation-and-validation

- 选择20—30家公司，建立200—300条人工风险标注。

- 系统评测覆盖Parser、Retriever、Extractor、Agent、Verifier和市场模型。

- 开展无LLM、无Verifier、单Agent、多Agent、无市场特征等消融实验。

- 形成错误分类、失败案例、模型校准和可复现实验报告。

## 14.3 提交准备、RC和v1.0

| **阶段** | **核心任务** | **退出标准** |
|:---|:---|:---|
| 提交准备 | 页面、自动报告、PPT、视频、操作与部署手册 | 评委能理解、运行和验证 |
| RC | 依赖、Prompt、规则、模型、黄金案例冻结；新电脑和异常复跑 | 无阻塞Bug，核心链路100%复现 |
| v1.0 | 完整源码、模型、配置、结果、报告和材料包 | 完成正式参赛提交并保留备份 |

# 15. 当前状态与下一步

当前统一阶段：**v0.3 Released / Frozen**。v0.4仍为`NOT STARTED`。

## v0.3.5 Evidence Intelligence 当前主任务

v0.3 Release 保持冻结。Phase 0.5 已完成真实 Responses API、2410.HK real-LLM
gate 与 14-case Human Golden A/B。结论是 Precision 改善但 Risk Recall 未改善，
Evidence Recall@3 仍低；静态共享检索覆盖是主要瓶颈，LLM 抽取/运行是次要瓶颈，
Legal downstream Verifier 是额外瓶颈。

现有 Human Golden 同时暴露 evidence-role ambiguity、主证据权威性不一致、risk
instance/evidence row 混合与评测语义不一致。直接 Retriever 调优暂停，优先建立
Expert Golden v2 和 Evidence Intelligence 架构。

| 阶段 | 状态 | 验收 |
|---|---|---|
| Phase 0.6A Blind preparation | COMPLETED | 3-case inventory、schema、packet、validator、importer、tests |
| Phase 0.6B Protocol/collaboration | CURRENT | Protocol v1.1、14-case safe packets、assignment、research docs |
| Phase 0.6C Three-case pilot | NOT STARTED | 2410 Financial、2517 Legal、1167 Business |
| Phase 0.6D Expert Golden v2 | NOT STARTED | Risk/Evidence/relationship/calculation/confidence/policy provenance |
| Phase 0.7 Architecture | NOT STARTED | Shared Index、domain search、bounded iteration、completeness |
| Phase 0.8 A/B | NOT STARTED | 同 PDF/LLM/policy/verifier/Expert Golden |
| Phase 0.9 Retrieval optimization | NOT STARTED | 算法选择与排序优化 |
| v0.4 Market Prediction | NOT STARTED | 必须通过 v0.3.5 Gate 后启动 |

### Expert Golden 治理

```text
Original Prospectus
-> GPT Expert Blind Annotation
-> Deterministic Validation
-> Independent GPT Audit
-> Conflict Detection
-> Selective Human Adjudication
-> Expert Golden v2
```

第一轮 2410 结果状态为 `PILOT_DIAGNOSTIC_ONLY` / informative-but-not-gold，不能
作为 Retriever tuning target。当前协作目录不包含该答案、Human Golden、PDF、
本地路径、Retriever/Agent 输出或 2025 blind。

已冻结：cash-flow-statement cash 口径；non-applicable 的 rejected/not_applicable
一致性；四类财务风险 Calculation；dash/blank/N/A 不自动视为 zero。

未冻结：OPEN-01 zero-revenue concentration；OPEN-02 precommercial severity；
OPEN-03 Expert Fact Layer 与 policy-derived Label Layer 分层。

权威研究入口：

- `docs/research/GPT_EXPERT_GOLDEN_PLAN.md`
- `docs/research/EXPERT_GOLDEN_OPEN_POLICY_ITEMS.md`
- `docs/research/EVIDENCE_INTELLIGENCE_ARCHITECTURE_PLAN.md`
- `docs/annotation/gpt_expert_v1_1/README.md`

| 角色 | 当前任务 |
| --- | --- |
| 1号技术负责人 | 维护Protocol、确定性校验、协作隔离与v0.3.5 A/B设计 |
| 2号数据治理 | 维护source manifest、Case分工与结果导入审计 |
| 3号财务 | 负责Financial expert pilot与计算事实核对 |
| 4号法务 | 负责Legal expert pilot与政策歧义升级 |
| 5号业务 | 负责Business expert pilot与产品/收入语义核对 |

### 软件门槛与 Golden 门槛

V3-8、V3-9、V3-11 和 V3-12 的软件实现已经完成。A03/A04按
`single_named_human_review_v1`关闭，Human Golden与正式跨域评测均已完成；历史
Owner waiver已被当前政策取代。完整语义见
[V03_GATE_A_CLOSEOUT.md](V03_GATE_A_CLOSEOUT.md)。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>项目主线总结</strong></p>
<p>v0.2完成真实单风险闭环，v0.3完成真实多Agent文档分析并发布冻结。当前以v0.3.5重建Expert Golden和Evidence Intelligence，经架构A/B与检索优化Gate后再进入v0.4市场标签与预测。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 附录A：v0.3退出条件检查表

- [x] Financial、Legal、Business三个真实Agent可用
- [x] 8类风险进入正式风险注册表
- [x] 至少5份真实开发/复核案例已进入治理材料
- [x] verified风险均有Evidence
- [x] 要求精确计算的verified风险均有Calculation
- [x] 专用Verifier能够拒绝错误结论
- [x] Supervisor能够去重、处理冲突和失败降级
- [x] enhanced_v2工作流可配置运行
- [x] 批量运行器和评测脚本可运行
- [x] Streamlit能展示多Agent结果
- [x] mvp_v1和Mock模式继续可用
- [x] 2410.HK现金跑道结果不回归
- [x] 无LLM API时确定性功能可运行

- [ ] 正式双审黄金主证据Recall@3达到90%（研究验证延期）

- [ ] 正式双审黄金确定性金额/比例准确率达到95%（研究验证延期）

- [ ] 正式双审黄金verified风险精确率达到90%（研究验证延期）

- [ ] 正式双审黄金案例完整运行率100%（研究验证延期）

- [x] 2025盲测集未参与开发调试

- [ ] 独立干净环境复跑（尚未安全执行）

- [x] 创建v0.3 Tag和Release：`v0.3.0-multi-agent-risk-analysis`

# 附录B：来源基准与版本说明

本计划以`v0.2.0-real-document-slice@916df5d442030e3443249a881f995b5d039a5b33`为稳定回归与回退基线。

- 后续如公共Schema、赛题要求或数据源发生变化，应先更新本计划再启动新开发棒。

## 附录C：v0.3开发契约冻结状态

- [x] 统一Agent输入与`list[RiskItem]`输出保持不变
- [x] 8类v0.3风险代码及唯一owner已冻结
- [x] `material_litigation_compliance`已补入风险注册表
- [x] `weak_ipo_market`保留但在v0.3禁用
- [x] Financial、Legal、Business内部候选Pydantic模型已冻结
- [x] `ComponentDiagnostic`与`last_diagnostics`旁路诊断契约已冻结
- [x] Supervisor去重、冲突和组合发现兼容字段已冻结
- [x] LLMProvider结构化调用、元数据、环境变量与降级规则已冻结
- [x] 黄金案例CSV与双人复核规范已冻结
- [x] PR模板和契约测试已建立

正式编码入口以`V03_DEVELOPMENT_CONTRACT.md`、`V03_RISK_RULES.md`、`V03_ANNOTATION_GUIDE.md`和`V03_LLM_PROVIDER_SPEC.md`为准。契约版本为`v03_contract_v1`；变更必须升级版本并由技术负责人审核。
