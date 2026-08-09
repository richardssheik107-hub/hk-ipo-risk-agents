# v0.3 Legal Candidate Contract Delta

冻结基准：`docs/V03_DEVELOPMENT_CONTRACT.md`及main原始`src/ipo_risk/agents/legal_models.py`。

当前分支保留带默认值的法律候选扩展以支持已实现规则，但这些扩展尚未获得公共契约批准。

## ShareholderRightCandidate

冻结字段为`right_type`、`holder`、`trigger_or_termination`、`survives_listing`、`evidence_ids`。

| 新增字段 | 需要原因／使用规则 | 可从冻结字段确定性推导 | 删除损失 | 兼容性 | 需成员1批准 |
|---|---|---|---|---|---|
| `is_effective` | 区分历史权利与当前权利；Builder检查当前有效性 | 否；`survives_listing`不等于当前状态 | 无法可靠判断当前是否有效 | 默认`None`，旧payload不变 | 是 |
| `termination_event` | 识别listing、listing application等终止事件 | 仅部分可从自由文本推断 | 丢失标准化事件 | 默认空串 | 是 |
| `termination_timing` | 区分上市前、上市时、上市后 | 仅部分可从自由文本推断 | 无法执行冻结时点规则 | 默认空串 | 是 |
| `restoration_clause` | 冻结规则要求识别可恢复权利 | 否 | 无法区分明确无恢复与未披露 | 默认`None` | 是 |
| `restoration_condition` | 判断恢复触发条件是否明确 | 仅可从自由文本非稳健推导 | 明确恢复和模糊恢复无法区分 | 默认空串 | 是 |
| `impact_on_public_shareholders` | 为Verifier提供潜在法律影响说明 | 否 | 丢失辅助解释，不影响基本时点判断 | 默认空串 | 是 |
| `uncertainty_reason` | LLM只报告事实缺口，不下风险结论 | 否 | 难以把复杂歧义安全送入needs_review | 默认空串 | 是 |

## LitigationComplianceCandidate

冻结字段为`matter_type`、`counterparty_or_authority`、`current_status`、`potential_impact`、`materiality_stated`、`evidence_ids`。

| 新增字段 | 需要原因／使用规则 | 可从冻结字段确定性推导 | 删除损失 | 兼容性 | 需成员1批准 |
|---|---|---|---|---|---|
| `subject` | 标识案件或合规事项主体 | 否 | 多事项时无法稳定归并 | 默认空串 | 是 |
| `event_date` | 保存发生时间和历史性支持事实 | 否 | 丢失时间追溯；不是冻结决策硬条件 | 默认`None` | 是 |
| `amount` | 保存已披露金额 | 否 | 丢失量化支持；金额不是冻结硬条件 | 默认`None` | 是 |
| `currency` | 金额存在时防止币种误读 | 否 | 金额不可安全解释 | 默认空串 | 是 |
| `amount_unit` | 防止元/千/百万单位错误 | 否 | 金额不可安全解释 | 默认空串 | 是 |
| `is_pending` | 规范化未决状态并检查冲突 | 部分可由`current_status`推导 | 降低状态一致性检查能力 | 默认`None` | 是 |
| `is_resolved` | 规范化结案状态并检查冲突 | 部分可由`current_status`推导 | 降低历史事项识别能力 | 默认`None` | 是 |
| `is_remediated` | 监管处罚/合规事项整改判断 | 否；resolved不等于remediated | 无法执行整改影响是否消除规则 | 默认`None` | 是 |
| `management_materiality` | 区分明确重大、明确不重大和未披露 | `materiality_stated`只说明是否有声明，不含结论 | 无法执行重大性规则 | 默认空串 | 是 |
| `license_impact` | 判断核心牌照影响是否消除 | 否 | 无法执行许可影响规则 | 默认空串 | 是 |
| `uncertainty_reason` | 将事实歧义安全送入needs_review | 否 | 丢失人工复核原因 | 默认空串 | 是 |

两个模型还设置`extra="forbid"`，旧的合法Mock payload仍可使用，但未知字段从忽略变为拒绝，属于验证行为收紧，也需要成员1确认。

## MEMBER_1_CONTRACT_CHANGE_REQUIRED

当前Legal规则无法仅依靠冻结候选字段完整表达termination timing、restoration condition、remediation和license impact。建议成员1批准上述带默认值扩展及`extra="forbid"`行为；批准前不得称`legal_models.py`已成为新的正式冻结契约。
