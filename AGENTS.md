# Codex 与团队开发规则

## 1. 当前执行模式：Submission Sprint Acceleration

项目进入提交前加速阶段。统一事实源：

```text
docs/V0.4_RELEASE_ACCEPTANCE.md
docs/COMPETITION_CLOSURE_PLAN.md
```

当前最重要的工程原则是：

```text
开发 / 集成可继续  !=  最终比赛 Gate 已通过
当前案例阶段完成  !=  所有可选通道都可用
前端绿色完成      !=  COMPETITION_READY
```

M1/M2、M4、D 模型决议、C/E final-three、one-shot Validation 等是**提交前 Release Gates**。它们不得被伪造、绕过或提前宣称 PASS，但也**不得阻塞与其无直接依赖的 UI、API、Report、Trace、Evidence、Adapter、测试或其他 lane 开发合并**。

一个 current-case 阶段只要真实执行并物化了该阶段的 governed product state，就可以在前端标记“已完成”；缺少可选 Market / Model / real-LLM channel 时，必须在该绿色阶段内部继续明确显示 `unavailable`、`partial` 或 `deterministic fallback`。

## 2. 开始任务前

至少阅读：

1. `docs/README.md`
2. `docs/V0.4_RELEASE_ACCEPTANCE.md`
3. `docs/COMPETITION_CLOSURE_PLAN.md`
4. 对应 lane 文档
5. `docs/COMPETITION_METRIC_PROTOCOL.md`
6. 本 `AGENTS.md`

涉及 frozen data/model 时再读对应 manifest、receipt 和 contract。

## 3. Ownership 是 stewardship，不是互斥锁

### A — Integration / Release
公共合同、Git/CI、E2E、最终 Gate、审计、封包。

### B — Document Intelligence
Parser preservation、Retriever/ranking、Financial/Legal/Business extraction、LLM quality、Evidence binding、M1/M2。

### C — Market Intelligence
PIT market facts、MarketContext、Skills、同行估值能力、Market trace。

### D — Outcome / Business Value
1D/5D/20D/60D、prediction table、模型/规则业务价值、strict revalidation、D→E handoff。

### E — Final Supervisor / Product
Conflict/re-check、Final Supervisor、Trace、Evidence Viewer、Screenshot、Human Review、report、UI/API、典型案例。

Ownership 用于默认维护责任和冲突协调，**不禁止跨 lane 审计、修复或补齐产品链**。提交期遇到明确依赖时，其他成员可以直接补 additive/versioned adapter、projection、test 或 presentation integration，而不需要等待 owner 完成整个 Gate。

受保护接口的**向后兼容 additive extension**可以在 contract/regression tests 完整时直接进入普通 PR 流程；破坏兼容性的签名/schema 变更仍需 A review。

## 4. 快速合并准则

普通开发 PR 不要求关闭最终比赛指标。满足以下条件即可合并：

```text
主题清晰
CI green
相关 contract/regression tests green
无已知功能回归
无 fake value / fake PASS
无 Gold / Validation / Blind 泄漏
无 Secret / licensed raw data / absolute path
```

以下内容**不能作为普通 PR 的合并前置条件**，除非该 PR 明确负责关闭它：

- ALL 79 Development M1/M2 达标
- M4 6 份真人 review 完成
- D final promotion / strict revalidation 完成
- C/E final-three 全部完成
- final submission package ready

如果一个 lane 被外部不可变输入卡住，记录 blocker 后立刻推进其他本地可完成工作；禁止整队等待。

## 5. 前端 / Demo 加速规则

目标是尽快得到完整可运行产品面，而不是等待所有研究指标收口后再接前端。

允许并鼓励：

- 所有已物化 current-case stage 立即接入 UI；
- runtime completion 与 project readiness 分离展示；
- 可选 channel 缺失时继续渲染完整页面，并显示其真实 unavailable/missing reason；
- deterministic fallback 可完成产品阶段，但必须明确“不计 real-provider acceptance”；
- Risk/Evidence/Calculation/Trace/Human Review/Report 即产即接；
- page/bbox、Market metadata、model handoff、Supervisor judgement 使用 additive adapter/projection，避免阻断其他页面；
- 为演示准备真实已运行 artifact 的 replay/static backup，但不得用 mock 冒充真实运行。

禁止：

- 为了全绿制造 Market 值、Model score、Evidence、SHAP 或 LLM success；
- 将 optional channel unavailable 改写成 available；
- 将 current-case `completed` 解释为 `COMPETITION_READY`；
- UI 自己修补 backend risk level、Evidence identity、bbox 或模型语义。

## 6. Architecture rules

- 保持模块化单体；
- UI 只消费 governed service 输出；
- mock / unavailable / real 必须显式区分；
- protected interface 变更补 contract/regression tests；
- 新能力优先 additive / versioned；
- 不为旧 Gate 文案保留无业务意义的 runtime 阻塞；
- 最终 readiness 只由 release acceptance/readiness artifact 判定。

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

## 7. LLM contract

LLM 可以做复杂条款、商业化语义、文本粉饰度、market interpretation 和 final synthesis。

LLM 不得：

- invent Evidence / market facts；
- cite out-of-scope IDs；
- 替代精确财务计算；
- 修改 frozen model score；
- 把未校准 score 称为 probability；
- 绕过 Verifier；
- 因一次失败或表达冲突无条件删除正确 deterministic candidate。

Structured output 必须 Schema validate；provider failure 必须诚实降级。真实 LLM 失败时 deterministic fallback 可以保障页面和报告继续跑通，但必须保留 provider diagnostics，并且不计 real-provider acceptance。

## 8. Evidence / Calculation / Verifier

- formal RiskItem 有真实 Evidence；
- exact numeric claim 有 deterministic Calculation；
- page / bbox / Evidence identity 不由 UI 修补；
- bbox 只能来自真实 parser/source geometry；
- 无法核验进入 pending / needs_review；
- screenshot 必须绑定 source PDF hash、page、bbox source 和 output hash；
- page-level bbox 与精确 snippet-level bbox 必须区分，不得夸大粒度。

## 9. Split / Gold / Blind — 仍是硬边界

```text
2020–2023 Development
2024 Validation
2025 Blind
```

- Existing Gold immutable，`UNJUDGED` 不当 negative；
- Gold 不进入 runtime Retriever、Prompt 或 Agent；
- Development 可诊断和优化；
- Validation 冻结后 one-shot，不回头调参；
- 2025 Blind 输入/outcome 不用于缺陷定位、选择规则或调参；
- 正式 Blind 推理只在冻结和授权后进行；
- Market 必须 PIT-safe，missing 不 fake-fill。

这些边界不能因为提交期加速而放松。

## 10. Role-B 规则

fixed-10 是诊断加速器，不是最终目标。不设固定迭代次数。

允许完整取证与通用改造：Parser → Retrieval → LLM → Builder → Reconciliation → Verifier → Binding。

允许 Development-only 的 Parser、Retriever、Prompt、Schema、provider/model/transport、merge、Verifier、cache/replay 改进；禁止公司、股票、case、页码或 Gold 原句特判。

每个修复包报告 hypothesis、affected units、before/after、ablation、regression tests、accepted/reverted。一个方向失败后立即 pivot，不等待人类选择下一 root。

B 的最终 M1/M2 Gate 不阻止其他 lane 和前端继续集成。

## 11. Role-D 规则

已有 artifact/receipt 不等于业务价值充分。D 必须同时报告实际效果、基准和局限。

不得使用 2024 Validation 做 post-hoc score inversion、threshold selection 或重训；新的业务价值改进只能在 Development 设计并冻结后一次性验证。

D final model/handoff 未完成时，前端 Model channel 可以诚实 unavailable；这不阻止 Document/Market/Rule/Supervisor/Report 页面完成。

## 12. Git / Codex

- 从最新 main 建短分支；
- 单 PR 单清晰主题，可含多个相互依赖文件；
- 不 force push 共享分支；
- 不覆盖用户未提交工作；
- 不提交 PDF、licensed raw data、model bulk、cache、credential、raw journal 或 absolute path；
- CI 绿且无 material blocker 时快速合并，随后立即同步 main；
- 多人并行时优先 additive/versioned contract，减少 rebase 冲突；
- 历史 PR 完成情况从 Git/PR 查询，不再制造“等待前一 Gate 才能开始”的文档锁。

## 13. Required deliverables

```text
完整 current-case 7-stage UI/API/report
M1/M2 benchmark and waterfalls
1D / 5D / 20D / 60D prediction/evaluation tables
Agent / Tool / Evidence trace
Evidence screenshots
3 case reports
M4 human reviews
readiness / provenance / determinism / security audits
submission ZIP + manifest
```

全部最终比赛状态仍以 `docs/V0.4_RELEASE_ACCEPTANCE.md` 为准；任何 UI 绿色阶段都不得替代其中的 Release Gate。
