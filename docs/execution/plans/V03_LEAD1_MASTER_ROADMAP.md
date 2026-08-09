---
document_type: coordination_roadmap
owner: lead-1-tech-lead
status: DRAFT
updated_at: 2026-08-09
snapshot_main: ae41dcee3a042c0098c16c711d97ea499310af69
---

# 1号负责人 v0.3 主执行路线图

> 本文件是 **1号技术负责人协调路线图**，不是单一可执行 Execution Plan。
>
> **禁止直接使用 `$execute-approved-plan` 执行本文件。**
>
> 每一棒仍必须单独生成、审核并批准对应的 `APPROVED` Plan，例如 `V3-3_RETRIEVER_PLAN.md`、后续 `V3-4_LLM_PROVIDER_PLAN.md` 等。

## 1. 当前状态快照

当前 `main` 快照：

```text
ae41dcee3a042c0098c16c711d97ea499310af69
```

已完成或已进入主线：

- V3-0A：v0.3 范围与路线冻结。
- V3-0B：v0.3 开发契约冻结。
- V3-2：`CatalogIPODataProvider`、特殊证券治理已合并。
- V3-10 基础设施：批量运行、断点续跑、2025 盲测保护、黄金案例评测框架与 CI 加固已合并。
- Planner → Executor 基础设施已进入 `main`。
- V3-3：`docs/execution/plans/V3-3_RETRIEVER_PLAN.md` 已批准并进入 `main`，等待 Codex Executor 执行。

尚未完成的关键前置：

- V3-1 真实黄金案例仍需由财务、法务、业务成员完成 5—10 份真实招股书标注与双人复核。
- V3-4 LLMProvider 尚未开始正式实现。
- V3-5 / V3-6 / V3-7 三个真实专业 Agent 尚未正式合入 `main`。
- V3-8 专用 Verifier、V3-9 Supervisor / enhanced_v2、V3-11 UI / 报告和 V3-12 发布加固尚未完成。

## 2. 1号负责人的核心职责

1号不是“把所有业务代码都写完”的角色，而是负责以下五类工作：

1. **架构主线**：Retriever、LLMProvider、Verifier、Supervisor、Workflow、Service 集成与发布冻结。
2. **共享边界治理**：统一控制公共 Schema、Registry、Container、Workflow、Service 等受保护文件的修改。
3. **团队接力与 PR 审核**：确保 2/3/4/5 号分支基于正确主线、接口兼容、测试完整、无越权修改。
4. **Planner → Executor 管理**：每个技术负责人棒次都先生成独立 Plan，再交给 Codex 执行，避免聊天指令代替工程合同。
5. **最终系统集成与发布**：将专业成员产出组合成可运行、可评测、可回归、可复现的 v0.3 系统。

## 3. 后续任务总顺序

推荐主链：

```text
V3-3 Retriever
    ↓
V3-4 LLMProvider
    ↓
接收并审核 V3-1 / V3-5 / V3-6 / V3-7 专业成员产出
    ↓
V3-8 专用 Verifier
    ↓
V3-9 Supervisor + enhanced_v2 + 共享组件集成
    ↓
真实黄金案例批量评测复跑
    ↓
V3-11 UI / 报告集成审核
    ↓
V3-12 发布加固
    ↓
v0.3 Release
```

并行原则：

- 3号财务成员可以继续准备 Financial Skills / Agent / 黄金案例，但涉及共享文件的改动必须等 1号集成。
- 4号 Legal Agent 和 5号 Business Agent 可以先做标注、Prompt、规则和本模块测试，但真实 LLM 链路正式合并应等待 V3-4 稳定。
- V3-8 只能在三个 Agent 最小闭环清晰后收口。
- V3-9 必须在 V3-8 之后完成整体工作流闭环。
- V3-11 可以由 5号先做页面原型，但正式集成必须基于稳定的 Service / enhanced_v2 输出。

## 4. 当前立即任务：V3-3 Retriever 查询族泛化

### 目标

将现有现金 / 经营现金流关键词 Retriever 泛化为 v0.3 财务、法务、业务查询族，同时保持 `DocumentRetriever.retrieve()` 公共接口不变。

### 1号当前动作

- [ ] 本地同步最新 `main`。
- [ ] 在新 Codex 会话确认 `$execute-approved-plan` 可发现。
- [ ] 执行：

```text
Use $execute-approved-plan to execute:
docs/execution/plans/V3-3_RETRIEVER_PLAN.md
```

- [ ] 等待 Codex 生成 `docs/execution/reports/V3-3_RETRIEVER_EXECUTION_REPORT.md`。
- [ ] 审核 Plan / Report / Diff 三方一致性。
- [ ] 确认没有修改 `retrieval/base.py`、Schema、Container、Agent、Workflow、Service 等 Forbidden Files。
- [ ] 确认全量回归与 2410.HK 回归通过。
- [ ] 仅在审核通过后提交、push、PR、CI、merge。

### V3-3 退出门槛

- 八类新查询族存在并有简体 / 繁体 / 英文覆盖。
- 相关章节优先于模板化、错误章节或泛关键词诱饵。
- Evidence ID 与排序稳定。
- 无匹配仍为空结果，不允许 fallback 假证据。
- 不硬编码公司名、股票代码、案例 ID 或页码。
- 不引入 LLM、Embedding、向量库或新依赖。
- 现有现金与经营现金流回归保持稳定。

## 5. 下一棒：V3-4 可替换 LLMProvider

### 依赖

- V3-3 必须完成审核并合并至 `main`。
- 生成 V3-4 Plan 时重新读取最新 `main` SHA，不沿用 V3-3 的 `base_commit`。

### 1号需要实现

- [ ] 冻结 LLMProvider 的最小公共协议与结构化输出边界。
- [ ] 保留 Mock Provider。
- [ ] 实现 Unavailable Provider，缺少 API Key 时返回结构化不可用状态，而不是崩溃。
- [ ] 实现真实 Provider 适配层，只消费 Retriever 筛选后的少量 Evidence。
- [ ] 输出必须经过 Pydantic 校验；不得直接返回任意字典作为跨模块接口。
- [ ] API Key 只能来自环境变量，不写入配置仓库。
- [ ] Prompt / 模型名必须配置化和版本化。
- [ ] LLM 不参与 Decimal 精确金融计算，也不直接给最终风险分。
- [ ] 无 API Key 时 Financial 确定性链路和 Mock 回归必须继续运行。
- [ ] 增加 Mock / Unavailable / malformed output / timeout / provider error 等契约测试。

### V3-4 退出门槛

- Mock / Real / Unavailable 可替换。
- 结构化事实输出稳定可校验。
- 无密钥环境不崩溃。
- 真实 Provider 失败可被转换为结构化诊断 / AnalysisError。
- 不改变 Agent、Service 的公共返回契约。

## 6. 专业成员交付的接收与集成

### V3-1 黄金案例

1号不负责独自标完整黄金集，但必须负责最终验收：

- [ ] 确认真实案例数量达到 5—10 份。
- [ ] 每个正式风险代码至少有覆盖案例或明确的不适用 / 负例设计。
- [ ] 关键案例完成双人复核并保留 reviewer / second_reviewer / disagreement 记录。
- [ ] 物理页码、原文、金额 / 比例、币种、单位、报告期、Calculation、标准核验状态完整。
- [ ] 2025 盲测案例不得进入规则、Prompt、阈值和检索调优。
- [ ] 不允许把 `evidence_not_found` 错写成 `not_applicable`。

### V3-5 Financial Agent

3号主开发，1号主要做边界与集成审核：

- [ ] 检查 Financial Agent 只拥有 `cash_runway`、`continuous_loss`、`revenue_growth`、`customer_concentration`、`supplier_concentration`。
- [ ] 检查 Decimal、单位、币种和期间严格一致。
- [ ] 检查需要数值判断的风险均有 Calculation 与 Evidence 追溯。
- [ ] 检查 2410.HK 现金跑道回归不变。
- [ ] 如需修改 Registry / Container / Schema，由 1号独立集成，不让成员分支直接争抢共享文件。

### V3-6 Legal Agent

4号主开发，1号审核：

- [ ] 确认风险所有权仅限 `redemption_rights` 与 `material_litigation_compliance`。
- [ ] 防止把一般性监管文本、模板条款或历史已终止权利误报为当前重大风险。
- [ ] 条款状态必须区分有效、终止、恢复、条件性生效和歧义。
- [ ] LLM 候选事实必须能追溯到 Evidence。
- [ ] 不确定状态进入 `needs_review`，不能伪装为 verified。

### V3-7 Business Agent

5号主开发，1号审核：

- [ ] 风险所有权只限 `precommercial_product`。
- [ ] Business 可以提供客户 / 供应商依赖事实，但不能生成 concentration 风险码。
- [ ] 区分产品销售收入、授权收入、研发服务收入与未商业化状态。
- [ ] 核心产品 / 管线事实必须有 Evidence。
- [ ] 不得把“研发中”简单等同于“重大风险”。

## 7. 必须补做的共享组件集成

PR #20 已知限制：`CatalogIPODataProvider` 当前由批量运行器运行时注册，尚未正式加入全局 `ComponentRegistry`。

该项由 1号负责，不应让 2号再次跨越核心边界修改。

推荐在 V3-9 前完成一个独立的小型 Integration Plan：

- [ ] 在 `ComponentRegistry` 中注册 `catalog` IPO Provider。
- [ ] 配置增加可选择 `ipo_data_provider: catalog`，但不得破坏默认 Mock / v0.2 行为。
- [ ] Service / enhanced_v2 可通过配置使用 Catalog Provider。
- [ ] 增加注册、配置选择、未知配置和降级测试。
- [ ] 不修改 `IPOProfile` 公共字段语义。

## 8. V3-8 专用 Verifier 体系

### 负责人模式

1号负责统一框架与集成，3/4/5号提供各专业规则复核。

### 需要完成

- [ ] Financial trend verifier：亏损趋势、收入增长、集中度、Calculation / Evidence 一致性。
- [ ] Legal verifier：权利有效状态、终止 / 恢复、诉讼 / 合规重大性。
- [ ] Business verifier：商业化状态、核心产品 / 管线依赖和收入事实一致性。
- [ ] 统一核验 Evidence 是否真实存在并支持结论。
- [ ] 需要 Calculation 的风险在 Calculation 缺失 / 失败时不得 verified。
- [ ] 错误结论可以 rejected。
- [ ] 歧义进入 needs_review。
- [ ] Verifier 不创造新的风险事实和 Evidence。

### V3-8 退出门槛

- verified precision 目标达到项目门槛。
- 典型错误结论可以被拒绝。
- 歧义项稳定进入 needs_review。
- 无证据正式风险不能通过。

## 9. V3-9 Supervisor 与 enhanced_v2

### 核心工作

- [ ] 保留 `mvp_v1`，不得删除旧工作流。
- [ ] 新增 / 完成 `enhanced_v2`。
- [ ] 组织 Financial → Legal → Business → Market 占位 → specialized verifiers → Supervisor → Predictor → Report。
- [ ] Supervisor 去重同风险码重复候选。
- [ ] 记录冲突，不静默覆盖。
- [ ] 组合发现只能引用已有风险，不新增无来源风险。
- [ ] 单个 Agent 失败时整体返回 `partial`，保留其他 Agent 已有结果。
- [ ] Repository 保持由 `IPOAnalysisService` 在 Workflow 返回后持久化。
- [ ] Catalog Provider 通过正式 Registry / config 接入。
- [ ] Mock 与真实组件仍可配置切换。

### 退出门槛

- 完整单案例多 Agent 链路可运行。
- 一个专业 Agent 故障不会击穿整条服务。
- 重复风险和冲突有结构化记录。
- `IPOAnalysisService -> IPOAnalysisResult` 公共契约保持不变。
- mvp_v1、Mock、2410.HK 回归全部通过。

## 10. V3-10 真实黄金案例评测复跑

基础设施已经合并，但真实黄金案例尚未完成，因此 1号后续要推动“框架存在”升级为“真实结果可解释”。

在 V3-1、V3-5、V3-6、V3-7、V3-8、V3-9 基本完成后：

- [ ] 使用 5—10 份已双人复核黄金案例执行批量分析。
- [ ] 检查 `analysis_results.jsonl`、`risk_items.csv`、`evidence_results.csv`、`case_summary.csv`、`failure_report.csv`、`evaluation_metrics.json`。
- [ ] Retriever 主证据 Recall@3 目标 ≥ 90%。
- [ ] 确定性数值提取准确率目标 ≥ 95%。
- [ ] Verifier verified precision 目标 ≥ 90%。
- [ ] 黄金案例完整运行率 100%。
- [ ] 非预期崩溃 0。
- [ ] 2025 盲测仍保持 fail-closed，禁止用于调规则。

如未达到门槛：

- 只能依据 development / reviewed golden cases 定位问题；
- 必须创建新的专项 Plan 修复 Retriever / Extractor / Agent / Verifier；
- 不允许在一个“评测 Plan”中顺手扩大修改范围。

## 11. V3-11 Streamlit 与报告集成

5号业务 / 产品主导 UI，1号负责技术边界与最终集成。

### 1号责任

- [ ] 审核 Streamlit 只能构造 Request、调用 `IPOAnalysisService`、展示 `IPOAnalysisResult` 与错误。
- [ ] 禁止前端直接调用 Agent、LLM、Parser、Predictor 或 Repository。
- [ ] 确保页面可展示 Financial / Legal / Business 结果。
- [ ] 展示 Evidence 物理页码和原文。
- [ ] 展示 Calculation。
- [ ] 展示 verification_status、needs_review、诊断与 AnalysisError。
- [ ] 明确规则分不是校准后的真实下跌概率。
- [ ] 审核报告生成器不重新执行 Agent / Verifier / Predictor。
- [ ] 保持 Mock 演示模式可运行。

## 12. V3-12 发布加固与 v0.3 Release

### 1号主责

- [ ] 冻结功能范围，停止新增功能。
- [ ] 清理未合并 / 过时分支和文档状态。
- [ ] 全量 `pytest -q`。
- [ ] `python scripts/validate_project.py`。
- [ ] `python scripts/validate_competition_data.py`。
- [ ] 黄金清单完整性检查。
- [ ] 真实批量评测。
- [ ] `python -m compileall -q app src scripts`。
- [ ] `git diff --check`。
- [ ] 凭证、Token、本地绝对路径、缓存、模型输出和大型原始文件扫描。
- [ ] 2410.HK 真实 E2E 保持 `2.76 / verified / 90 critical` 回归。
- [ ] Mock E2E 保持稳定。
- [ ] 新环境独立复跑。
- [ ] README、PROJECT_MASTER_CHECKLIST、ROADMAP、CHANGELOG 与实际状态同步。
- [ ] 确认 API Key 缺失时系统诚实降级。
- [ ] 生成最终 v0.3 Release Checklist。

只有以上全部完成后，才进入 Tag / GitHub Release；Tag 和 Release 必须由负责人明确确认后执行。

## 13. 每个 1号棒次的 Planner → Executor 标准流程

以后 1号自己的每个核心开发任务严格执行：

```text
最新 main
    ↓
Web ChatGPT 检查 GitHub / 契约 / 依赖
    ↓
生成单一任务 DRAFT Plan
    ↓
负责人审核
    ↓
改为 APPROVED 并进入 GitHub
    ↓
本地同步 main，工作区必须 clean
    ↓
Use $execute-approved-plan to execute: <PLAN_PATH>
    ↓
Codex 创建 / 使用 Plan 指定分支
    ↓
最小范围实现 + Scope Guard + Required Validation
    ↓
Execution Report
    ↓
负责人审查 Plan / Report / Diff / Tests
    ↓
明确授权 commit / push / PR
    ↓
GitHub CI
    ↓
最终审核并 merge
```

规则：

- 一个 Plan 只解决一个核心问题。
- 每一棒都必须使用合并后的最新 `main` SHA 作为新的基线。
- 不提前批准未来多个 Plan，因为后续基线、接口和依赖会变化。
- Codex 不得自行修改 Plan 状态，不得自行扩大 Allowed Files。
- 出现 `PLAN_CHANGE_REQUIRED` 时回到 Planner 修改 Plan revision，而不是让 Codex现场越权。
- 出现 `BLOCKED` 时先解决环境 / 工作区 / 前置依赖，不用绕过安全检查。

## 14. 1号对团队 PR 的统一审核清单

每个成员 PR 至少检查：

- [ ] 是否基于最新或可兼容的 `main`。
- [ ] 是否只修改自己负责的文件。
- [ ] 是否触碰受保护共享边界；如有，是否应拆给 1号集成。
- [ ] 是否保持公共 Schema 和统一返回类型。
- [ ] 正式风险是否有真实 Evidence。
- [ ] 数值风险是否有 Calculation。
- [ ] 无证据 / 提取失败 / 冲突是否诚实进入诊断，而非伪造无风险。
- [ ] 是否引入秘密、Token、本地绝对路径、原始 PDF、缓存或生成结果。
- [ ] 是否新增 / 更新对应测试。
- [ ] 全量回归是否通过。
- [ ] 2025 盲测是否被错误用于调试或调参。
- [ ] PR 描述是否明确已知限制与降级行为。

## 15. 1号任务优先级

### P0：当前必须完成

1. V3-3 Retriever 执行、审核、PR、合并。
2. 生成并完成 V3-4 LLMProvider Plan。
3. 推动 3/4/5号完成 V3-1 真实黄金案例和双人复核。

### P1：专业 Agent 进入后立即完成

4. 审核并集成 V3-5 / V3-6 / V3-7。
5. 补 Catalog Provider 全局 Registry / config 集成。
6. V3-8 专用 Verifier。
7. V3-9 Supervisor + enhanced_v2。

### P2：系统收口

8. 真实黄金案例批量评测与针对性修复。
9. V3-11 UI / 报告技术集成与边界审核。
10. V3-12 发布加固、独立复跑、文档冻结和 v0.3 Release。

## 16. 1号最终完成定义

只有同时满足以下条件，1号在 v0.3 的职责才算完成：

- Retriever 查询族已泛化并达到黄金案例检索门槛。
- 可替换 LLMProvider 已接入且缺密钥可降级。
- Financial / Legal / Business 三个真实 Agent 均已通过负责人集成审核。
- 专用 Verifier 能拒绝错误并把歧义送入 needs_review。
- Supervisor / enhanced_v2 实现多 Agent 协同、冲突和 partial 降级。
- Catalog Provider 可由正式 Registry / config 使用。
- 5—10 份真实黄金案例完成双人复核和批量评测。
- UI / 报告只通过 Service 边界工作。
- Mock、mvp_v1、2410.HK v0.2 回归全部稳定。
- 全量测试、项目校验、赛事数据校验、编译、diff、安全扫描和新环境复跑通过。
- README / Checklist / Roadmap / Changelog 与代码实际状态一致。
- v0.3 Tag / Release 在明确授权后发布。
