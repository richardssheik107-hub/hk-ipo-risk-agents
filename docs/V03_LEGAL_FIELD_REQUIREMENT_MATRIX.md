# LEGAL_FIELD_REQUIREMENT_MATRIX

状态：`APPROVED / FROZEN FOR v0.3`

本矩阵适用于已批准的内部Legal候选字段。字段获得契约批准不改变以下分类，也不表示
每个字段在所有决策路径上都必须出现。候选字段`counterparty_or_authority`在标准化
observation层对应`counterparty_or_regulator`，候选层名称保持不变。

分类定义：

- `MUST_HAVE_FOR_DECISION`：缺失时冻结规则无法判断，进入`needs_review`；
- `REVIEW_SIGNAL`：不是所有路径都强制，但缺失、冲突或特定事项类型下会触发复核；
- `OPTIONAL_SUPPORTING_FACT`：存在时必须准确且可追溯，缺失本身不阻塞冻结规则。

| 字段 | 分类 | 决策说明 |
|---|---|---|
| `subject` | REVIEW_SIGNAL | 多事项或主体无法识别时需要复核；不是严重性阈值 |
| `counterparty_or_regulator` | REVIEW_SIGNAL | 监管/案件对象无法识别时需要复核；不是独立风险触发器 |
| `event_date` | OPTIONAL_SUPPORTING_FACT | 支持历史判断；缺失本身不阻塞明确重大未决事项 |
| `amount` | OPTIONAL_SUPPORTING_FACT | 若披露必须准确提取；未披露不得虚构，也不自动needs_review |
| `currency` | REVIEW_SIGNAL | 仅在amount存在时必须与金额配套并准确 |
| `amount_unit` | REVIEW_SIGNAL | 仅在amount存在且原文有单位时校验；缺金额时不要求 |
| `management_materiality` | MUST_HAVE_FOR_DECISION | 冻结规则明确要求重大性不清进入needs_review |
| `potential_impact` | REVIEW_SIGNAL | 可支持经营影响；明确material时缺失不单独阻塞，和“不重大”结论冲突时复核 |
| `license_impact` | MUST_HAVE_FOR_DECISION（仅许可事项） | 必须判断许可影响是否消除 |
| `current_status` | MUST_HAVE_FOR_DECISION | 必须区分pending/ongoing与resolved/remediated |
| `is_pending` | REVIEW_SIGNAL | 可由标准current_status推导；与状态冲突时复核 |
| `is_resolved` | REVIEW_SIGNAL | 可由标准current_status推导；与状态冲突时复核 |
| `is_remediated` | MUST_HAVE_FOR_DECISION（处罚/合规的已解决路径） | 已结案不等于已整改；未决状态明确时可直接进入核验 |

冻结决策核心保持：重大未决事项、未消除的监管处罚、未消除的许可影响进入Verifier；重大性、结案状态、必要的整改状态或许可影响不清时`needs_review`。金额和发生日期不是自建门槛。
