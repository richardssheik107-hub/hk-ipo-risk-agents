# Codex 与团队开发规则

## 1. 当前执行模式：Submission Sprint Acceleration

统一事实源：

```text
docs/V0.4_RELEASE_ACCEPTANCE.md
docs/COMPETITION_CLOSURE_PLAN.md
```

当前工程原则：

```text
开发 / 集成可继续  !=  最终比赛 Gate 已通过
当前案例阶段完成  !=  所有可选通道都可用
前端绿色完成      !=  COMPETITION_READY
```

当前提交前真正的 Release blockers 是：

```text
B ALL79 M1/M2 threshold failure（measurement complete / frozen）
one-shot Validation（not executed; blocked by G2 under strict policy）
final CI / provenance / determinism / security / licensing / package
```

Role-D promotion、Dynamic Market/Model、产品与 capability coverage 已通过，进入回归保护。

**Human Review / 历史 M4 rubric 不再是 Release Gate。** 不要求新增真人标注，不要求 3 案 × 2 reviewer。Human Review UI、export、review projection 可以继续作为可选产品能力保留，但不得因为没有真人 review 阻塞 ordinary PR、final readiness 或 submission package。

Final-three 当前已形成稳定团队基线：E1 `3/3`、M3 `1.0 × 3`、Market / Model `3/3`、17/17 re-check、17/17 precise screenshots、7-stage `7/7 × 3`、canonical replay / fresh clone / CI 均已通过。

## 2. 开始任务前

至少阅读：

1. `docs/README.md`
2. `docs/V0.4_RELEASE_ACCEPTANCE.md`
3. `docs/COMPETITION_CLOSURE_PLAN.md`
4. 对应 lane 文档
5. `docs/COMPETITION_METRIC_PROTOCOL.md`
6. 本 `AGENTS.md`

注意：`COMPETITION_METRIC_PROTOCOL.md` 是冻结历史协议。其 M4 explanation rubric 仅保留为可选质量诊断，不代表当前 Release Acceptance 仍要求真人评审。

## 3. Ownership 是 stewardship，不是互斥锁

### A — Integration / Release
公共合同、Git/CI、E2E、最终 Gate、审计、封包。

### B — Document Intelligence
Parser / Retriever / ranking、Financial/Legal/Business extraction、LLM quality、Evidence binding、M1/M2。

### C — Market Intelligence
PIT market facts、MarketContext、Skills、同行估值、Dynamic New-IPO Market、Market trace。

### D — Outcome / Business Value
1D/5D/20D/60D、prediction table、模型/规则业务价值、frozen-model inference、strict revalidation、D→E handoff。

### E — Final Supervisor / Product
Conflict/re-check、Final Supervisor、Trace、Evidence Viewer、Screenshot、Report、UI/API、典型案例；Human Review 为 optional surface。

Ownership 用于默认维护责任和冲突协调，不禁止跨 lane 审计、修复或补齐产品链。兼容的 additive/versioned adapter、projection、test 可以快速跨 lane 合并；破坏兼容的公共 schema/signature 变更仍需 A review。

## 4. 快速合并准则

普通开发 PR 满足以下条件即可合并：

```text
主题清晰
CI green
相关 contract/regression tests green
无已知功能回归
无 fake value / fake PASS
无 Gold / Validation / Blind 泄漏
无 Secret / licensed raw data / absolute path
```

以下内容不能作为普通 PR 的前置条件，除非 PR 明确负责关闭它：

- ALL 79 Development M1/M2 达标；
- D final promotion / strict revalidation；
- Dynamic New-IPO 全链完成；
- final submission package ready。

**真人 review 数量不再是任何 PR 或 final package 的必需条件。**

## 5. 稳定 Demo 基线保护

`PR #185` 合入后的三案例 replay 是当前 `KNOWN_GOOD_TEAM_DEMO_BASELINE`。

后续高风险功能必须优先走 feature branch：

```text
feat/dynamic-new-ipo-runtime
fix/v046-role-b-...
feat/role-d-...
```

不得为了新功能破坏：

```text
Gate E1 3/3
M3 1.0 x 3
Market / Model 3/3
17/17 recheck
17/17 screenshots
7/7 x 3 stages
canonical bundle hash
fresh-clone readiness
```

## 6. Dynamic New-IPO 规则

目标分两阶段：

```text
Phase 1 — 438 historical frozen universe
Market-X artifact
→ frozen model dynamic inference
→ native SHAP
→ Final Supervisor

Phase 2 — arbitrary new IPO
PIT historical input
→ Dynamic Market-X
→ frozen model dynamic inference
→ SHAP
→ report
```

禁止通过复制 final-three handoff、case-specific JSON、公司/股票/页码特判制造“新案例支持”。

Dynamic path 必须：

- 复用 frozen feature schema / model identity；
- score 继续标为 `uncalibrated_model_score`；
- Market 严格 PIT-safe；
- missing 明确 missing，不补零或 proxy；
- SHAP 必须来自真实模型 inference；
- 新案例无必要输入时诚实 unavailable/partial。

## 7. LLM contract

LLM 可以做复杂条款、商业化语义、文本粉饰度、Market interpretation 和 Final synthesis。

LLM 不得：

- invent Evidence / market facts；
- cite out-of-scope IDs；
- 替代精确财务计算；
- 修改 frozen model score；
- 把未校准 score 称为 probability；
- 绕过 Verifier；
- 因一次失败或表达冲突无条件删除正确 deterministic candidate。

Structured output 必须 Schema validate；provider failure 必须诚实降级。Final Supervisor v3 vocabulary / scope / severity contract 是稳定基线，不得为提高 acceptance 放松 guard。

## 8. Evidence / Calculation / Verifier

- formal RiskItem 有真实 Evidence；
- exact numeric claim 有 deterministic Calculation；
- page / bbox / Evidence identity 不由 UI 修补；
- bbox 只能来自真实 parser/source geometry；
- 无法核验进入 pending / needs_review；
- screenshot 必须绑定 source PDF hash、page、bbox source 和 output hash；
- page-level bbox 与精确 snippet-level bbox 必须区分，不得夸大粒度。

## 9. Split / Gold / Blind — 硬边界

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

## 10. Role-B 规则

fixed-10 是诊断加速器，不是最终目标。

最终冻结 checkpoint：

```text
real-LLM gated: 79/79 cases
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
316 logical tasks; 310 structured+scope valid; 6 fallback; 0 transport failure

deterministic offline (selected):
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%
```

real-LLM candidate 删除 9 个正确 deterministic Risk 与 12 个正确 Evidence；
monotonicity 失败，因此未 promote。当前 submission freeze 下不再修改算法。

```text
results / call trace / waterfall provenance
→ documentation truth
→ security / clean-clone / package audit
```

禁止为提交继续修改 Parser、Retriever、Prompt、Schema、provider/model、merge 或 Verifier；
禁止公司、股票、case、页码或 Gold 原句特判。

最终 Gate：ALL79 Development M1 `>=0.80`、M2 `>=0.85`、real_llm_cases `=79`。

## 11. Role-D 规则

- `PROMOTE_V2` 已通过 A-owned PR #184 生效；历史 frozen PR-F 身份继续保留；
- V2 独立 freeze/receipt/handoff 与 strict checker 已完成；
- dynamic audit 为 540/562 inference、537 outside per-case handoff、70/70 parity、0 mismatch；
- 不得继续根据 2024 调 feature、threshold、alert fraction 或 score direction；
- dynamic inference 必须使用真实 frozen model / feature identity，不读取不存在的 per-case handoff 冒充推理。

## 12. Git / Codex

- 从最新 main 建短分支；
- 单 PR 单清晰主题，可含多个强依赖文件；
- 不 force push 共享分支；
- 不覆盖用户未提交工作；
- 不提交 PDF、licensed raw data、model bulk、cache、credential、raw journal 或 absolute path；
- CI 绿且无 material blocker 时快速合并；
- 多人并行优先 additive/versioned contract；
- 历史状态从 Git/PR 查询，当前状态以 active release docs 为准。

## 13. Required deliverables

```text
完整 current-case 7-stage UI/API/report
M1/M2 benchmark and waterfalls
1D / 5D / 20D / 60D prediction/evaluation tables
Agent / Tool / Evidence trace
Evidence screenshots
3 canonical case reports + offline replay
Dynamic New-IPO capability evidence
competition capability demos
readiness / provenance / determinism / security audits
submission ZIP + manifest
```

Human Review export 可以作为 optional artifact 保留，但**不要求真人评分、不作为 Release blocker**。

全部最终比赛状态以 `docs/V0.4_RELEASE_ACCEPTANCE.md` 为准。
