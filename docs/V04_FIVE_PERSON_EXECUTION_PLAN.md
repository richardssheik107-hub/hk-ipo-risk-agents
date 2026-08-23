# v0.4 五人执行计划

> Status snapshot: **2026-08-23**  
> PR-A / PR-B / PR-C / PR-D: **COMPLETE / FROZEN**  
> Oracle v2: **COMPLETE / FROZEN / EVALUATION-ONLY**  
> PR-E: **COMPLETE / FROZEN**
> Current formal Gate: **PR-F — LightGBM + Explainability**

## 1. 总原则

正式 Gate / mainline merge 严格串行：

```text
PR-A → PR-B → PR-C → PR-D → PR-E → PR-F → PR-G → PR-H
                                              ↓
                                    Baseline E2E Freeze
                                              ↓
                                        CH-0..CH-6
```

允许并行的是准备性工作、QA、文档、测试夹具和不改变冻结边界的分析；准备工作不能被描述为后续 Gate 已开始或已通过。

## 2. A — Tech Lead / Pipeline

定位：系统集成、运行编排、provenance、coverage、reproducibility、CI、Gate review。

长期职责：

```text
canonical orchestration
run manifest / provenance
coverage / reproducibility
cross-module contract checks
CI / integration
formal Gate review
```

A 不重新实现 Parser / Retriever / Agent，不替 D 决定 target/model policy，不用 ungoverned proxy 填数据，也不打开 2025 Blind y。

### 当前任务

- 维护 PR-A-D / Oracle v2 frozen boundary；
- 维护 PR-E frozen input / reproducibility boundary，支持 PR-F final Gate review；
- 审核跨成员 runtime handoff 只传输已冻结、可校验的数据资产；
- 不开始 PR-G / PR-H 正式 Gate。

## 3. B — Document / Agent

定位：Production Document Intelligence 质量、Evidence / Calculation / page provenance、Document explanation。

### 当前任务

- 对 frozen PR-A Production Document-X 做下游 QA；
- 验证 missing / state / value semantics、Gold/Oracle leakage guard；
- 在需要时抽样验证 `case → analysis → RiskItem → Evidence → Calculation → page/bbox` 链路；
- 为 PR-G 的 Document explanation 接口准备最小受控投影。

B 的 QA 是支持性审计，不自动重开 PR-A。只有数据泄漏、公共 Schema 错误、不可复现或闭环阻断才申请 unfreeze。

## 4. C — Market Data / PIT

定位：Pre-IPO Market X、数据源、point-in-time 和 2025 Blind 边界。

PR-B Core 已完成并冻结：

```text
438 / 438 materialized
30 positions
0 failed
0 silent drops
PIT audit PASS
```

### 当前任务

- 支持 PR-E / PR-F 对 Market feature 语义解释；
- 保持 Core frozen；
- Extended authoritative-source research 可并行，但 HSI / industry benchmark / total-market turnover 缺失不得用错误 proxy 填补；
- 继续维护 PIT / Blind guard。

## 5. D — Quant / ML Research

定位：Outcome、canonical dataset、baseline、LightGBM、explainability、实证结论。

已完成：

```text
PR-C 5D Outcome                 COMPLETE / FROZEN
PR-D Canonical Dataset          COMPLETE / FROZEN
```

### 当前唯一正式任务：PR-F

Production full cohort：

```text
354 Development
70 Validation
M / P / PM
```

Oracle v2 fair intersection：

```text
96 strict usable
77 Development
19 Validation
M / P / O / PM / OM
```

PR-E 已冻结 Logistic / Linear / Ridge baseline、forward chaining 与 PM-M / OM-M / OM-PM。PR-F 必须：

- 在冻结 cohort / split / target / preprocessing policy 上运行 LightGBM；
- 输出 SHAP / importance、calibration assessment、ablation 与 error analysis；
- 保持 untouched 2024 Validation 与 uncertainty / power caveat；
- no 2025 Blind y。

PR-F 完成并冻结前，不正式进入 PR-G。

## 6. E — Oracle / Product Integration

定位：Oracle research sidecar、Final Supervisor、Market Agent integration、report、Streamlit / Demo。

Oracle v2 已完成并冻结：

```text
98 materialized
96 strict usable
77 Dev / 19 Val
142 features
evaluation_only = true
production_consumable = false
```

### 当前任务

- 保持 Oracle v2 与 Production 隔离；
- 支持 frozen PR-E Oracle diagnostic 与 PR-F explainability 解释；
- PR-G / PR-H 只做不越 Gate 的 contract / UI preparation；
- 不把旧 preparation branch 当作正式主线直接 merge。

## 7. 当前协作地图

| Member | Formal status now | Current useful work |
| --- | --- | --- |
| A | integration / Gate owner | PR-E freeze boundary + PR-F reproducibility/final review |
| B | supporting QA | frozen Document-X + Evidence provenance QA |
| C | supporting QA | Market/PIT interpretation + Extended research |
| D | **PR-F formal owner** | run and freeze LightGBM + explainability |
| E | supporting integration | Oracle interpretation + PR-G/H preparation |

## 8. 当前严禁混淆的三类工作

### 已冻结主线

PR-A / PR-B / PR-C / PR-D / Oracle v2 不因为成员换机器或缺本地 runtime 就变回“未完成”。缺文件是 environment / handoff blocker，不等于 formal Gate 回退。

### Supporting QA

B 的 Document QA、C 的 Extended research、E 的 UI skeleton 可以并行，但不改变 formal Gate。

### Current formal Gate

只有 PR-F 的正式 measured run / review / freeze 会推进当前主线状态。

## 9. PR-E 后续

```text
PR-E COMPLETE / FROZEN
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + 3–5 real IPO demo
→ v0.4.3 Baseline Freeze
→ CH-0..CH-6 Competition Hardening
```

## 10. Documentation rule

成员交接不再新增长期 `HANDOFF_FINAL` / `PREP_V2` 类文档。临时交接应进入 PR body、issue/comment 或本地 package README；正式事实只进入 active docs、completion report 和 frozen manifest。
