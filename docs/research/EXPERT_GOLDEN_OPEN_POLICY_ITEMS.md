# Expert Golden Open Policy Items

这些条目属于研究决策，不得由 Codex、GPT annotator 或生产 Agent 擅自冻结。

## OPEN-01 — Zero-revenue concentration

当最新期间 revenue 为 0，或 total purchases denominator 无法可靠定义时，客户/
供应商集中度应采用最近非零可比期间、标记当前期不可测量、进入 needs_review，
还是采用其他正式政策？

状态：`UNRESOLVED`

## OPEN-02 — precommercial_product severity

当前规则只冻结了“核心产品未商业化且无产品销售收入”构成候选，但没有冻结
low/medium/high/critical severity。GPT 可以判断 semantic applicability，但必须
报告 severity policy ambiguity，不得因“高度依赖核心产品”自行升级为 high。

状态：`UNRESOLVED`

## OPEN-03 — Expert facts 与 policy-derived labels 分层

Expert Golden 是否应正式拆成 `Expert Fact Layer` 与
`Policy-derived Risk Label Layer`，以避免 GPT 执行确定性政策？

状态：`DESIGN_DECISION_PENDING`

## 决策纪律

任何条目只有在团队形成书面决定、版本化规则并补充回归测试后才能关闭。Protocol
v1.1 必须显式报告这些歧义，而不是补造阈值、会计规则或 severity policy。
