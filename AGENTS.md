# Codex 与团队开发规则

## 1. 当前执行模式

项目处于 Competition Closure，统一计划见：

```text
docs/COMPETITION_CLOSURE_PLAN.md
docs/V0.4_RELEASE_ACCEPTANCE.md
```

目标直接对应赛题：

```text
PDF 防幻觉解析与隐性风险抽取
→ 多 Agent + Skill + 冲突查证
→ 基本面 + 市场情绪
→ 1D / 5D / 20D / 60D 业务验证
→ Evidence / Trace / Human Review / Screenshot
→ runnable prototype / API / submission package
```

## 2. 开始任务前

至少阅读：

1. `docs/README.md`
2. `docs/V0.4_RELEASE_ACCEPTANCE.md`
3. `docs/COMPETITION_CLOSURE_PLAN.md`
4. 对应 lane 文档；
5. `docs/COMPETITION_METRIC_PROTOCOL.md`；
6. 本 `AGENTS.md`。

涉及 frozen data/model 时再读对应 manifest、receipt 和 contract。

## 3. Ownership

### A — Integration / Release

公共合同、Git/CI、E2E、Gate、审计、封包。

### B — Document Intelligence

Parser preservation、Retriever/ranking、Financial/Legal/Business extraction、LLM quality、Evidence binding、M1/M2。

### C — Market Intelligence

PIT market facts、MarketContext、Skills、同行估值能力、Market trace。

### D — Outcome / Business Value

1D/5D/20D/60D、prediction table、模型/规则业务价值、strict revalidation、D→E handoff。

### E — Final Supervisor / Product

Conflict/re-check、Final Supervisor、Trace、Evidence Viewer、Screenshot、Human Review、report、UI/API、典型案例。

所有权用于避免冲突，不禁止跨 lane 的审计和协作。公共接口变更仍需 A review。

## 4. 工程优先级

任务必须直接改善至少一项：

- 赛题能力覆盖；
- M1/M2/M3/M4/M5；
- real E2E；
- Evidence / Trace / PIT / provenance；
- 业务价值；
- 可复现提交；
- 人机复核与答辩展示。

不再默认禁止：

- relevant full-repo audit；
- Development-only Retriever redesign；
- provider/model/transport comparison；
- paper-style ablation；
- 一个假设下的多文件原子修复包；
- screenshot / report product work。

这些工作必须有明确假设、身份冻结、测试、消融和停止条件。

仍默认拒绝与赛题无关的基础设施堆叠，例如无必要的 Kafka、Redis、Neo4j、Kubernetes 或无限 autonomous loop。

## 5. Architecture rules

- 保持模块化单体；
- UI 只消费 governed service 输出；
- mock / unavailable / real 必须显式区分；
- protected interface 变更补 contract/regression tests；
- 新能力优先 additive / versioned，不静默破坏 frozen identity。

Protected interfaces：

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

## 6. LLM contract

LLM 可以做复杂条款、商业化语义、文本粉饰度、market interpretation 和 final synthesis。

LLM 不得：

- invent Evidence / market facts；
- cite out-of-scope IDs；
- 替代精确财务计算；
- 修改 frozen model score；
- 把未校准 score 称为 probability；
- 绕过 Verifier；
- 因一次失败或表达冲突无条件删除正确 deterministic candidate。

Structured output 必须 Schema validate；provider failure 必须诚实降级。

## 7. Evidence / Calculation / Verifier

- formal RiskItem 有真实 Evidence；
- exact numeric claim 有 deterministic Calculation；
- page / bbox / Evidence identity 不由 UI 修补；
- bbox 无唯一来源时明确 unavailable；
- 无法核验进入 pending / needs_review；
- screenshot 必须绑定 source PDF hash、page、bbox source 和 output hash。

## 8. Split / Gold / Blind

```text
2020–2023 Development
2024 Validation
2025 Blind
```

- Existing Gold immutable，`UNJUDGED` 不当 negative；
- Gold 不进入 runtime Retriever、Prompt 或 Agent；
- Development 可诊断和优化；
- Validation 冻结后 one-shot，不回头调参；
- 从本规则生效起，2025 Blind 输入与 outcome 都不得用于定位缺陷、选择规则或调参；
- 正式 Blind 推理只在冻结和授权后进行；
- Market 必须 PIT-safe，missing 不 fake-fill。

## 9. Role-B 规则

fixed-10 是诊断集，不是最终目标。不设固定迭代次数。

允许完整取证：Parser → Retrieval → LLM → Builder → Reconciliation → Verifier → Binding。

允许 Development-only 的通用 Retriever / Prompt / Schema / merge / Verifier 修复；禁止公司、股票、case、页码或 Gold 原句特判。

每个修复包必须报告：

```text
hypothesis
affected units
before / after M1/M2
ablation
regression tests
accepted or reverted
```

## 10. Role-D 规则

已有 artifact/receipt 不等于业务价值已经充分。D 必须同时报告实际效果、基准和局限。

不得使用 2024 Validation 做 post-hoc score inversion、threshold selection 或重训；新的业务价值改进只能在 Development 设计并冻结后一次性验证。

## 11. Git / Codex

- 从最新 main 建短分支；
- 单 PR 单清晰主题，可含多个相互依赖文件；
- 不 force push 共享分支；
- 不覆盖用户未提交工作；
- 不提交 PDF、licensed raw data、model bulk、cache、credential、raw journal 或 absolute path；
- 长任务产出机器 artifact 与短文档，不再新增一次性巨型 Prompt 文档；
- 历史 PR 完成情况从 Git/PR 查询，不新增 completion report。

## 12. Required deliverables

```text
M1/M2 benchmark and waterfalls
1D / 5D / 20D / 60D prediction/evaluation tables
Agent / Tool / Evidence trace
Evidence screenshots
3 case reports
M4 human reviews
runnable UI/API
readiness / provenance / determinism / security audits
submission ZIP + manifest
```

全部状态以 `docs/V0.4_RELEASE_ACCEPTANCE.md` 为准。
