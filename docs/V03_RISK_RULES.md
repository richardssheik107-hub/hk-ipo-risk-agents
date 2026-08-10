# v0.3 风险目录与规则

规则版本：`v03_contract_v1`

机器可读配置：`configs/v03_risk_rules.yaml`

## 1. 唯一所有权

| 风险码 | Owner | Evidence | Calculation | v0.3 状态 |
|---|---|---:|---:|---|
| `cash_runway` | financial | 必须 | 必须 | 启用 |
| `continuous_loss` | financial | 必须 | 可选 | 启用 |
| `revenue_growth` | financial | 必须 | 必须 | 启用 |
| `customer_concentration` | financial | 必须 | 必须 | 启用 |
| `supplier_concentration` | financial | 必须 | 必须 | 启用 |
| `redemption_rights` | legal | 必须 | 不要求 | 启用 |
| `material_litigation_compliance` | legal | 必须 | 不要求 | 启用 |
| `precommercial_product` | business | 必须 | 不要求 | 启用 |
| `weak_ipo_market` | market | 必须 | 不要求 | 保留，v0.3 禁用，v0.4 再启用 |

## 2. 冻结阈值

- 现金跑道：小于 3 个月 critical；小于 6 个月 high；小于 12 个月 medium。
- 持续亏损：至少 3 个可比期间为 high；2 个可比期间为 medium。期间不可比则 needs_review。
- 收入增长：同比不高于 -20% 为 high；低于 0% 为 medium。
- 客户/供应商集中度：最大单一占比不低于 50% 或前五不低于 80% 为 high；最大单一不低于 30% 或前五不低于 60% 为 medium。
- 赎回权：仍有效或存在恢复条件时进入核验；终止和恢复条款不清时 needs_review。
- 重大诉讼合规：重大未决事项、监管处罚或许可影响未消除时进入核验；重大性或结案状态不清时 needs_review。
- 未商业化产品：核心产品尚未商业化且无产品销售收入时进入核验；产品阶段或收入归属不清时 needs_review。

### Legal v0.3候选严重性

`redemption_rights`与`material_litigation_compliance`统一使用provisional
`medium / 50`。生成的RiskItem必须标记`level_is_provisional=true`、
`score_is_rule_based=true`、`score_is_probability=false`。Legal Agent和专业Legal
Verifier均不得在v0.3自动升级为`high`或`critical`；Verifier只改变核验状态。
未来的等级提升规则必须使用新的、显式版本化severity policy。

## 3. 通用核验规则

1. `requires_evidence=true` 且 Evidence 为空，不得 verified。
2. `requires_calculation=true` 且 Calculation 为空或失败，不得 verified。
3. Calculation 的任一 `evidence_id` 不存在，不得 verified。
4. 法务和条款型风险不因缺少 Calculation 被拒绝。
5. Agent 只产生 pending/needs_review 候选；Verifier 决定最终核验状态。
6. 阈值变化必须创建新规则版本，保留旧配置用于回归，不得无版本覆盖。

## 4. 跨 Agent 协作

Business Agent 可以提供客户依赖、供应链依赖事实和 Evidence；Financial Agent 是两个 concentration 风险码的唯一生成者。Supervisor 可以组合已有风险，但组合发现不得伪造新 Evidence 或绕过 Verifier。
