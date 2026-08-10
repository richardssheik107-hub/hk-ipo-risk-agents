# v0.3 开发契约

状态：`frozen`

契约版本：`v03_contract_v1`

适用版本：`v0.3.0-multi-agent-risk-analysis`

本文件是 v0.3 编码、评审和验收的共同边界。任何公共字段删除、改名、语义变化，或风险所有权变化，必须先更新本文件、契约测试和版本号，经技术负责人审核后才能实施。

## 1. 不变公共链路

```text
IPOProfile + DocumentChunk + MarketSnapshot?
→ RiskAgent.analyze(...)
→ list[RiskItem]
→ RiskVerifier.verify(...)
→ VerificationResult
→ RiskSupervisor.supervise(...)
→ SupervisionResult
→ Predictor / Report / Repository / UI
```

`RiskAgent.analyze()` 的返回类型保持 `list[RiskItem]`。Agent 未生成风险时返回空列表，不得用 `None`、任意字典或异常字符串代替。

## 2. 角色输入、输出与权限

| 角色 | 输入 | 输出 | 唯一风险所有权 | 禁止事项 |
|---|---|---|---|---|
| Financial Agent | `IPOProfile`、`list[DocumentChunk]`、可选 `MarketSnapshot` | `list[RiskItem]`；内部候选模型见 `financial_models.py` | `cash_runway`、`continuous_loss`、`revenue_growth`、`customer_concentration`、`supplier_concentration` | 不调用 LLM 做精确计算；不生成法务/业务风险码 |
| Legal Agent | 同上 | `list[RiskItem]`；内部候选模型见 `legal_models.py` | `redemption_rights`、`material_litigation_compliance` | 不判断财务集中度；不将一般性条款直接升级为重大风险 |
| Business Agent | 同上 | `list[RiskItem]`；内部候选模型见 `business_models.py` | `precommercial_product` | 可提供客户/供应商依赖事实，但不得生成两个 concentration 风险码 |
| Market Agent | 同上 | v0.3 返回空风险列表并记录 `not_applicable`/`skipped` | 无；`weak_ipo_market` 延后至 v0.4 | 不使用 Mock 情绪数据制造正式风险 |
| Verifier | 候选 `RiskItem` 与 `evidence_by_code` | `VerificationResult` | 无 | 无证据不得 verified；需要 Calculation 的风险缺失/失败时不得 verified |
| Supervisor | Verifier 已分类风险 | `SupervisionResult` | 无 | 不新增没有来源风险；不丢失冲突与去重记录 |
| Predictor | Supervisor 输出的可用风险 | `PredictionResult` 或降级为空 | 无 | 不把规则分冒充真实概率 |
| ReportGenerator | `ReportContext` | `list[ReportSection]` | 无 | 不重新执行 Agent、Verifier、Predictor |
| Streamlit | `IPOAnalysisRequest` | 展示 `IPOAnalysisResult` | 无 | 只能调用 `IPOAnalysisService` |

## 3. Agent 结果契约

每个 `RiskItem` 必须满足：

- `risk_code` 属于注册表，且由唯一 owner 生成；
- `category`、`risk_type`、`level`、`score`、`conclusion`、`agent_name` 语义明确；
- 正式风险携带真实 `Evidence`，页码和原文可核对；
- 需要精确数值判断的风险携带成功的 `Calculation`，其 `evidence_ids` 均存在；
- 初始 `verification_status` 为 `pending` 或 `needs_review`，Agent 不自证为 verified；
- 不适用、未找到证据、抽取失败和冲突不伪装为风险。

### 3.1 Legal 内部候选契约

`v03_contract_v1` 的公共接口和公共 Schema 保持不变。以下模型是 Legal Agent 内部、
带默认值且向后兼容的冻结候选契约，不作为新的跨模块公共返回类型。

`ShareholderRightCandidate` 字段：

```text
right_type
holder
trigger_or_termination
survives_listing
is_effective
termination_event
termination_timing
restoration_clause
restoration_condition
impact_on_public_shareholders
uncertainty_reason
evidence_ids
```

`LitigationComplianceCandidate` 字段：

```text
matter_type
subject
counterparty_or_authority
current_status
event_date
amount
currency
amount_unit
is_pending
is_resolved
is_remediated
management_materiality
potential_impact
license_impact
materiality_stated
uncertainty_reason
evidence_ids
```

审批这些 additive fields 不表示每条决策路径都必须提供全部字段。字段继续按
`MUST_HAVE_FOR_DECISION`、`REVIEW_SIGNAL` 和 `OPTIONAL_SUPPORTING_FACT` 分类。
候选层字段名保持 `counterparty_or_authority`；抽取后的标准化 observation 层可使用
`counterparty_or_regulator`，两者不得通过重命名候选字段来混同。

### 3.2 Legal v0.3 severity policy

`redemption_rights` 与 `material_litigation_compliance` 的 v0.3 候选等级统一冻结为
`medium / 50`。每条生成的 Legal 风险必须记录：

```text
level_is_provisional = true
score_is_rule_based = true
score_is_probability = false
```

Legal Agent 不自动升级为 `high` 或 `critical`；专业 Legal Verifier 只改变核验状态，
不升级 level 或 score。因此已核验风险仍可保持 provisional `medium / 50`。未来若需
Legal 高等级映射，必须建立独立、显式版本化的 severity policy。

## 4. 诊断与异常契约

`RiskAgent` 公共返回保持不变。需要解释“为什么没有产生风险”的真实组件实现 `DiagnosticSource.last_diagnostics`，返回 `list[ComponentDiagnostic]`。允许的诊断码：

```text
risk_generated
not_applicable
evidence_not_found
extraction_failed
conflicting_values
unsupported_layout
needs_review
component_failure
```

工作流负责把诊断映射为 `AgentLog`，组件异常映射为结构化 `AnalysisError`。可恢复异常产生 `partial` 结果并保留已有数据，不得静默吞掉，也不得把整条服务调用直接击穿。

## 5. Supervisor 兼容扩展

`SupervisionResult` 保留 `verified_risks` 和 `summary`，新增字段均有默认值：

- `duplicate_groups`：同一风险码的来源、保留项和合并原因；
- `conflicts`：风险、结论或证据冲突；
- `composite_findings`：只引用现有风险的组合发现；
- `metadata`：版本等非业务扩展。

旧调用方无需传入新字段。Supervisor 失败时保留 Verifier 输出。

## 6. enhanced_v2 工作流约束

节点顺序保持现有服务边界。`enhanced_v2` 继续保留 Market 节点；v0.3 未接入真实市场数据时，该节点明确记录 unavailable/skipped，不生成 `weak_ipo_market`。Predictor 和 ReportGenerator 仍分别只在工作流中执行一次。

## 7. 文件所有权与并行开发

| 负责人 | 允许主要修改 | 必须协商的共享文件 |
|---|---|---|
| 1 技术负责人 | core、workflow、service、契约测试、文档 | schemas、registry、state、container |
| 2 数据/标注 | 金标准清单、标注指南、评测脚本 | Evidence/标注字段契约 |
| 3 财务 | financial agent/models/skills/tests | 风险注册表、公共 Schema |
| 4 法务 | legal agent/models/prompts/tests | 风险注册表、LLMProvider |
| 5 业务/产品 | business agent/models/prompts/UI tests | 风险注册表、LLMProvider、UI |

禁止多人同时修改 `schemas/__init__.py`、`domain/risk_codes.py`、`core/container.py` 和 `workflows/state.py`。共享变更由技术负责人先合并，其他分支再同步。

## 8. Definition of Done

- 实现统一公共接口和本文唯一风险所有权；
- 真实风险有可核对 Evidence，所需 Calculation 可追溯；
- 无风险输出有结构化诊断；异常可降级；
- 新组件由配置和注册表选择，保留 Mock/disabled 回归；
- 增加单元、Agent 契约、工作流/服务集成和黄金案例测试；
- `pytest -q`、`validate_project.py`、`compileall`、`git diff --check` 全部通过；
- 不提交 API Key、本地绝对路径、原始招股书或生成结果。
