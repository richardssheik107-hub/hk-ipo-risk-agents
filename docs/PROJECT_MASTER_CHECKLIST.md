# HK IPO Risk Agents 项目主计划

> 审核版本：v0.3 开发路线（覆盖旧版总清单）
>
> 发布候选基线：`main@cdc3c69`，2026-08-06
>
> Word 版：`docs/PROJECT_MASTER_PLAN_v0.3.docx`

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>当前正式基线</strong></p>
<p>发布候选基线为 main 提交 cdc3c69（2026-08-06）：真实 PDF 现金跑道纵向闭环与 B 线赛事数据治理均已合入主线。远程 main 全新克隆、Python 3.12.10 虚拟环境安装、284 项测试、项目校验、赛事数据校验、编译检查和 2410.HK 真实 E2E 全部通过；第562/563页已完成第二次独立证据复核。v0.2 发布闸门通过，正在创建 Tag 与 Release。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

| **项目**       | **当前状态**                             |
|:---------------|:-----------------------------------------|
| v0.1.0         | 架构级MVP已发布                          |
| v0.2.0代码     | 已全部进入main                           |
| v0.2.0 Release | 发布闸门通过，正在创建Tag与Release       |
| 下一开发版本   | v0.3.0真实多Agent文档风险分析            |
| 远期版本       | v0.4市场预测、v0.5正式评测、RC与v1.0提交 |

适用对象：5人参赛团队 / 技术负责人 / 数据治理 / 财务 / 法务 / 业务与产品

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

## 1.1 v0.2已经完成的能力

- [x] 真实PyMuPDF解析：保留物理页码、原文和稳定Chunk。

- [x] 确定性关键词Evidence检索：现金及现金等价物、经营活动现金流。

- [x] 财务数值提取：币种、单位、报告期、期间长度和括号负数。

- [x] 现金跑道Skill：以Decimal完成月度消耗和可持续月数计算。

- [x] 现金跑道RiskItem、专用Verifier和verified-only规则评分。

- [x] Workflow、IPOAnalysisService、JSON Repository和Streamlit真实模式。

- [x] 565份招股书manifest、555/10行情覆盖和562/3官方IPO主数据桥接。

- [x] 24份影子样本、12份人工核对、A2.6复测与全量manifest自动对账。

## 1.2 当前尚未真实实现的能力

- □ Legal Agent仍为unavailable，不输出虚构法律风险。

- □ Business Agent仍为unavailable，不输出虚构业务风险。

- □ Market Agent和正式MarketDataProvider尚未接入。

- □ LLMProvider尚未作为生产组件接入。

- □ 当前规则风险分不是经过校准的上市后下跌概率。

- □ 1/5/20/60交易日标签、Logistic和LightGBM模型尚未建立。

## 1.3 数据基线

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
| v0.2.0 | 能否从真实PDF得到一条可信风险 | 真实现金跑道闭环、赛事数据治理、影子测试 | 发布闸门通过，待创建Release |
| v0.3.0 | 能否进行真实多Agent文档风险分析 | 3个真实Agent、8类风险、黄金案例、批量评测 | 下一开发版本 |
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

# 3. 阶段R0：v0.2正式发布收尾

v0.2的开发代码已进入main，本阶段不得新增大功能，只完成发布、复盘和v0.3输入冻结。

| **编号** | **任务** | **主要交付物** | **负责人** | **完成标准** |
|:---|:---|:---|:---|:---|
| R0-1（自动验收完成） | 最新main完整复跑 | 测试日志与环境记录 | 技术负责人 | 全部测试、校验、编译和真实E2E通过 |
| R0-2（独立环境复跑完成） | 技术备份独立复跑 | `V0.2_RELEASE_ACCEPTANCE.md` | 技术备份 | 新环境安装、Mock、真实PDF和数据验证成功 |
| R0-3（独立证据复核完成） | 第二次复核2410.HK | `V0.2_RELEASE_ACCEPTANCE.md` | Codex独立复核 | 第562/563页、金额、单位、期间及2.76个月确认 |
| R0-4（数据治理完成） | 特殊证券治理记录 | 02191/04801/04841说明 | 数据成员 | 明确REIT、SPAC股份/权证映射及资格 |
| R0-5（本次同步完成） | 发布文档同步 | README、CHANGELOG、ROADMAP、总清单 | 技术负责人 | 所有文档口径一致 |
| R0-6 | 创建Tag与Release | v0.2.0 Release | 技术负责人 | 冻结SHA、已知限制和回退点 |
| R0-7（完成） | 版本复盘 | `V0.2_RETROSPECTIVE.md` | 全组 | 明确成功项、问题和v0.3输入 |

## 3.1 建议Release名称

| v0.2.0-real-document-slice |
|----------------------------|

## 3.2 v0.2发布门

- ☑ 审核基线完整测试通过：284 passed

- ☑ 2410.HK真实E2E保持：706 chunks、Evidence第563/562页、现金跑道2.76个月、verified、90/critical

- ☑ 第二次独立证据复核完成；执行者为Codex，方法和结论已披露

- ☑ 远程main全新克隆和Python 3.12.10独立虚拟环境复跑完成

- ☑ README、ROADMAP、CHANGELOG和总清单已于本次同步

- ☑ 已记录证券主表截断、10份无行情、3份特殊证券和金额单位等限制

- □ Tag、Release Notes和回退SHA完成

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
| 4 | customer_concentration | 客户集中度过高 | Financial / Business | 占比提取 + 规则 |
| 5 | supplier_concentration | 供应商集中度过高 | Financial / Business | 占比提取 + 规则 |
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
| V3-0（本次完成） | 冻结v0.3范围与文档 | 以本文件替换旧版总清单，并同步README、ROADMAP和CHANGELOG；冻结风险目录、接力顺序和退出门槛。 | 技术负责人 | 只改文档，不改业务代码和公共Schema。 |
| V3-1 | 黄金案例与标注规范 | 选择5—10份真实招股书，建立风险适用性、主证据页、原文、数值、单位、期间和标准核验状态。 | 财务/法务/业务 | 每类风险至少一个正例，关键案例双人复核，2025盲测不得进入。 |
| V3-2 | IPO基础信息Provider | 从官方主数据桥接生成IPOProfile，处理匹配、占位、代码复用和特殊证券。 | 技术备份/数据 | 562个匹配案例稳定加载，缺失案例结构化降级。 |
| V3-3 | Retriever查询族泛化 | 增加收入、亏损、客户、供应商、特殊权利、诉讼、商业化和核心管线等查询族。 | 技术负责人 | 接口不变，支持简繁英、章节权重、稳定Evidence ID和无匹配空结果。 |
| V3-4 | 可替换LLMProvider | 建立Mock、真实和Unavailable Provider；只处理Retriever筛选后的少量Evidence。 | 技术负责人 | 输出Pydantic结构化事实，无API Key时确定性链路仍可运行。 |
| V3-5 | Financial Agent扩展 | 持续亏损、收入增长、客户集中度、供应商集中度及相关Skills。 | 财务成员 | Decimal、单位、期间严格一致；不破坏2410.HK回归。 |
| V3-6 | Legal Agent真实化 | 特殊股东权利、重大诉讼和合规事项。 | 法务成员 | 识别权利是否有效、是否终止、是否恢复；防止模板化章节误报。 |
| V3-7 | Business Agent真实化 | 未商业化、核心产品和管线依赖。 | 业务成员 | 区分产品销售收入、授权收入和研发服务收入。 |
| V3-8 | 专用Verifier体系 | 财务趋势、集中度、法律权利、诉讼合规、业务管线及整体一致性核验。 | 技术负责人+专业成员 | 错误结论可被拒绝，歧义进入needs_review。 |
| V3-9 | Supervisor与enhanced_v2 | 多Agent去重、冲突识别、组合风险、单Agent失败降级和新工作流。 | 技术负责人 | 保留mvp_v1；单个Agent失败时整体返回partial。 |
| V3-10 | 批量运行与评测 | 批量分析脚本、黄金案例评测、断点续跑、失败报告和指标JSON。 | 技术备份/数据 | 默认禁止2025盲测；单案例失败不终止批次。 |
| V3-11 | Streamlit与报告 | 三Agent页签、Evidence、Calculation、核验状态、诊断和规则分构成。 | 业务/产品+技术 | 前端只调用IPOAnalysisService，不直接调用Agent或LLM。 |
| V3-12 | 发布加固 | 完整测试、独立复跑、文档同步、Tag和Release。 | 全组 | 黄金案例100%运行、v0.2回归不变、无非预期崩溃。 |

# 7. 黄金案例与人工标注计划

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

# 15. 当前立即执行顺序

**1.** v0.2独立复跑和第二次金标准证据复核已完成。

**2.** 创建v0.2 Tag、GitHub Release和版本复盘文档。

**3. 本计划已写入ROADMAP和PROJECT_MASTER_CHECKLIST，v0.3范围已冻结。**

**4.** 建立v0.3黄金案例和标注规范。

**5.** 开发CatalogIPODataProvider并正式治理三个特殊证券。

**6.** 扩展Retriever并建立可替换LLMProvider。

**7.** 分别实现Financial、Legal、Business Agent。

**8.** 建立专用Verifier、Supervisor和enhanced_v2工作流。

**9.** 完成批量评测、Streamlit和证据化报告。

**10.** 完成独立复跑并发布v0.3。

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>项目主线总结</strong></p>
<p>v0.2已经完成真实单风险闭环和赛事数据治理；当前先完成正式发布。v0.3集中实现真实多Agent文档分析，v0.4再进入市场标签和预测，v0.5负责正式评测与实证证明，随后完成产品化、RC冻结和v1.0正式提交。</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 附录A：v0.3退出条件检查表

- □ Financial、Legal、Business三个真实Agent可用

- □ 8类风险进入正式风险注册表

- □ 至少5份、建议8—10份黄金案例

- □ 所有正式风险都有Evidence

- □ 所有数字风险都有Calculation

- □ 专用Verifier能够拒绝错误结论

- □ Supervisor能够去重、处理冲突和失败降级

- □ enhanced_v2工作流可配置运行

- □ 批量运行器和评测脚本可运行

- □ Streamlit能展示多Agent结果

- □ mvp_v1和Mock模式继续可用

- □ 2410.HK现金跑道结果不回归

- □ 无LLM API时确定性功能可运行

- □ 黄金主证据Recall@3达到90%

- □ 确定性金额/比例准确率达到95%

- □ verified风险精确率达到90%

- □ 黄金案例完整运行率100%

- □ 2025盲测集未参与开发调试

- □ 独立环境复跑通过

- ☑ README、ROADMAP、CHANGELOG和总清单已于本次同步

- □ 创建v0.3 Tag和Release

# 附录B：来源基准与版本说明

本计划基于GitHub仓库 richardssheik107-hub/hk-ipo-risk-agents 的main分支审核基线编制；文档提交后的main SHA会前移，因此以附录所列审核基线复现实证。

- 发布候选基准提交：cdc3c69d9f638077593e73f08acc673b995ae1db

- 提交说明：docs: replace master plan with audited v0.3 roadmap

- 提交记录：284 passing tests and GitHub Actions

- 独立环境复跑和第二次证据复核已完成；本文件提交后创建v0.2 Tag与GitHub Release。

- 后续如公共Schema、赛题要求或数据源发生变化，应先更新本计划再启动新开发棒。
