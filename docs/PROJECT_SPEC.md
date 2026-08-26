# Project Specification — v0.4.5 Competition Runtime

## 1. Product objective

从真实港股 IPO 招股书与受治理的上市前市场数据出发，产出可解释、可复核、可追溯的风险分析，并用上市后多周期结果验证预警价值。

系统不是“让一个大模型读完整 PDF 后自由写报告”，而是受约束的 Agentic AI 工作流：

```text
PDF → Evidence → specialized analysis → verification
+ governed market context
+ optional authentic frozen model signal
→ conflict / re-check / final supervision
→ trace / human review / report
```

## 2. Non-negotiable invariants

### Evidence

- 正式风险必须引用本次运行真实 Evidence；
- LLM 不得引用输入作用域外的 Evidence ID；
- Evidence identity / page / bbox 不在 UI 层修补；
- 未检索到证据不能伪造“无风险”。

### Calculation

- 精确财务数值、比率、runway 等由 deterministic Python 计算；
- LLM 只能解释 Calculation，不应成为权威计算来源。

### Market / PIT

- 市场事实只能来自 listing date 之前可得的 governed source；
- 缺失值保持 null + missing reason；
- 禁止用 listing-day/future rows、静态未来分类、zero/proxy 伪装 PIT。

### Model

- frozen PR-F 分数语义为 `uncalibrated_model_score`；
- 不得称 probability；
- authentic per-case runtime/handoff 缺失时明确 unavailable；
- 不允许为了前端完整而重训、重构或翻转分数。

### Split / Blind

```text
2020–2023  Development
2024       Validation
2025       Blind
```

2024 不能被反复调参；2025 outcome 在正式授权前不得访问。

## 3. Formal risk scope

冻结 formal baseline 仍是 8 个 risk codes：

Financial：

- `cash_runway`
- `continuous_loss`
- `revenue_growth`
- `customer_concentration`
- `supplier_concentration`

Legal：

- `redemption_rights`
- `material_litigation_compliance`

Business：

- `precommercial_product`

比赛示例中的 related-party transaction、disclosure tone 等只能作为 versioned sidecar/additive extension，不得静默改变 frozen baseline feature/risk identity。

## 4. Current runtime components

### Document

- PyMuPDF / table-aware parser path；
- keyword/bounded retrieval；
- Financial deterministic-first extraction；
- Legal structured LLM extraction；
- Business hybrid deterministic + structured LLM extraction；
- specialized Verifier；
- deterministic Document Supervisor。

### Market

- frozen PR-B Market-X Core；
- optional governed Extended；
- IPOHeatSkill；
- MarketRegimeSkill；
- bounded Market LLM interpretation。

### Competition supervision

- deterministic conflict detection；
- one bounded targeted re-check；
- Verifier challenge；
- LLM Final Supervisor；
- deterministic fail-closed fallback；
- Agent / Tool / Evidence trace；
- Human Review sidecar。

### Product

五个 Streamlit workspaces：

- Risk Command Center；
- Evidence & AI Analysis；
- Market & Model；
- Agent Collaboration Trace；
- Human Review & Final Report。

## 5. Measured current state

### E2E engineering

3 个真实 2024 PDF 已完成 catalog-bound offline matrix：2410.HK / 2460.HK / 1318.HK，3/3 integrity verified、0 structured workflow errors、traceability 1.0。

### Document quality

10-case governed offline Development benchmark 当前为：Risk P/R/F1 = 0%，Evidence Recall@5 = 20%。这不是 real-LLM benchmark，因此 Document quality Gate 仍 open。

### Market

Market Agent 已实现并接入 AI runtime；真实 provider Market interpretation 已在两只真实 IPO 上验证。industry return 无可靠 PIT mapping 时继续 unavailable。

### Evaluation

multi-horizon foundation 已存在，但 final 1D/5D/20D/60D competition artifacts 仍需 D 关闭。

## 6. Completion definition

系统只有在以下全部实测闭合后才能标记 `COMPETITION_READY`：

- fixed Development real-LLM Document benchmark；
- Risk / Evidence 指标材料；
- 1D/5D/20D/60D final outputs；
- final matrix real-provider Final Supervisor；
- final CI / blind / provenance / determinism；
- reproducible runbook；
- submission package。

详细状态见 `V0.4_RELEASE_ACCEPTANCE.md`。
