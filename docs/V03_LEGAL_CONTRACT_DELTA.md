# v0.3 Legal Candidate Contract Delta

状态：`RESOLVED / APPROVED`

冻结基准：`docs/V03_DEVELOPMENT_CONTRACT.md`及main原始`src/ipo_risk/agents/legal_models.py`。

以下带默认值的法律候选扩展已经由Member-1与Planner批准为v0.3内部候选契约。
该审批是additive且向后兼容的，不改变`v03_contract_v1`公共接口，也不表示所有字段
在每条决策路径上均为必填。

## ShareholderRightCandidate

冻结字段为`right_type`、`holder`、`trigger_or_termination`、`survives_listing`、`evidence_ids`。

| 新增字段 | 需要原因／使用规则 | 可从冻结字段确定性推导 | 删除损失 | 兼容性 | 审批状态 |
|---|---|---|---|---|---|
| `is_effective` | 区分历史权利与当前权利；Builder检查当前有效性 | 否；`survives_listing`不等于当前状态 | 无法可靠判断当前是否有效 | 默认`None`，旧payload不变 | APPROVED |
| `termination_event` | 识别listing、listing application等终止事件 | 仅部分可从自由文本推断 | 丢失标准化事件 | 默认空串 | APPROVED |
| `termination_timing` | 区分上市前、上市时、上市后 | 仅部分可从自由文本推断 | 无法执行冻结时点规则 | 默认空串 | APPROVED |
| `restoration_clause` | 冻结规则要求识别可恢复权利 | 否 | 无法区分明确无恢复与未披露 | 默认`None` | APPROVED |
| `restoration_condition` | 判断恢复触发条件是否明确 | 仅可从自由文本非稳健推导 | 明确恢复和模糊恢复无法区分 | 默认空串 | APPROVED |
| `impact_on_public_shareholders` | 为Verifier提供潜在法律影响说明 | 否 | 丢失辅助解释，不影响基本时点判断 | 默认空串 | APPROVED |
| `uncertainty_reason` | LLM只报告事实缺口，不下风险结论 | 否 | 难以把复杂歧义安全送入needs_review | 默认空串 | APPROVED |

## LitigationComplianceCandidate

冻结字段为`matter_type`、`counterparty_or_authority`、`current_status`、`potential_impact`、`materiality_stated`、`evidence_ids`。

| 新增字段 | 需要原因／使用规则 | 可从冻结字段确定性推导 | 删除损失 | 兼容性 | 审批状态 |
|---|---|---|---|---|---|
| `subject` | 标识案件或合规事项主体 | 否 | 多事项时无法稳定归并 | 默认空串 | APPROVED |
| `event_date` | 保存发生时间和历史性支持事实 | 否 | 丢失时间追溯；不是冻结决策硬条件 | 默认`None` | APPROVED |
| `amount` | 保存已披露金额 | 否 | 丢失量化支持；金额不是冻结硬条件 | 默认`None` | APPROVED |
| `currency` | 金额存在时防止币种误读 | 否 | 金额不可安全解释 | 默认空串 | APPROVED |
| `amount_unit` | 防止元/千/百万单位错误 | 否 | 金额不可安全解释 | 默认空串 | APPROVED |
| `is_pending` | 规范化未决状态并检查冲突 | 部分可由`current_status`推导 | 降低状态一致性检查能力 | 默认`None` | APPROVED |
| `is_resolved` | 规范化结案状态并检查冲突 | 部分可由`current_status`推导 | 降低历史事项识别能力 | 默认`None` | APPROVED |
| `is_remediated` | 监管处罚/合规事项整改判断 | 否；resolved不等于remediated | 无法执行整改影响是否消除规则 | 默认`None` | APPROVED |
| `management_materiality` | 区分明确重大、明确不重大和未披露 | `materiality_stated`只说明是否有声明，不含结论 | 无法执行重大性规则 | 默认空串 | APPROVED |
| `license_impact` | 判断核心牌照影响是否消除 | 否 | 无法执行许可影响规则 | 默认空串 | APPROVED |
| `uncertainty_reason` | 将事实歧义安全送入needs_review | 否 | 丢失人工复核原因 | 默认空串 | APPROVED |

## Validation behavior delta: RESOLVED / REMOVED

本轮已移除两个Candidate上的`ConfigDict(extra="forbid")`，恢复Pydantic默认的额外字段兼容行为。原冻结最小payload、当前扩展payload和Mock Provider均继续使用同一模型校验。Contract delta不再包含validation behavior change。

## Resolution

Member-1与Planner已批准上述字段为冻结的v0.3内部Legal候选契约。字段要求分类仍以
`V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md`为准；审批字段不等于把每个字段提升为
`MUST_HAVE_FOR_DECISION`。候选层继续使用`counterparty_or_authority`，标准化
observation层继续使用`counterparty_or_regulator`。
