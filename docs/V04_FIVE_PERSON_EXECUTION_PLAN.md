# v0.4 五人执行计划

> Status snapshot: **2026-08-23**  
> PR-A / PR-B / PR-C / PR-D: **COMPLETE / FROZEN**  
> Oracle v2: **COMPLETE / FROZEN / EVALUATION-ONLY**  
> PR-E / PR-F: **COMPLETE / FROZEN**
> Current formal Gate: **PR-G — Market Agent + Final Supervisor**

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

PR-F 已得到较弱/不稳定的 2024 预测结果，但这不授权回滚 Gate 顺序、反转模型分数或继续使用 2024 调参。当前继续完成 PR-G / PR-H；Competition Hardening 再通过直接 benchmark 决定 Document / Market 哪一侧需要增强。

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
- 维护 PR-E / PR-F frozen input / reproducibility boundary，支持 PR-G final Gate review；
- 阻止任何“看到 2024 结果后反转 score / 重调模型再当正式 Validation”的做法；
- 审核跨成员 runtime handoff 只传输已冻结、可校验的数据资产；
- 支持 B 获取最小 Evidence / analysis bulk 做 PR-G explanation QA；
- 支持 E 获取最小 PR-F frozen runtime / score / SHAP / uncertainty 资产；
- 不开始 PR-H 正式 Gate。

## 3. B — Document / Agent

定位：Production Document Intelligence 质量、Evidence / Calculation / page provenance、Document explanation。

### 当前任务

- frozen PR-A Production Document-X 下游 QA 已完成后，补 PR-G 所需的最小真实 Evidence / Explanation readiness QA；
- 抽样验证 `case → analysis → RiskItem → Evidence → Calculation → page/bbox → Verifier` 链路；
- 为 PR-G 的 Document explanation 接口准备最小受控投影，不修改冻结的 Production X；
- 为 CH-2 预先定义逐风险 benchmark protocol：Precision / Recall / F1 / Evidence Recall；
- 不因为 5D AUC 低就无差别重写 Retriever / Agent / Prompt。

B 的 QA 是支持性审计，不自动重开 PR-A。只有数据泄漏、公共 Schema 错误、不可复现或闭环阻断才申请 unfreeze。Competition 阶段只有直接 benchmark 未达标的风险类别才进入 targeted enhancement。

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

- 支持 frozen PR-E / PR-F 对 Market feature 语义解释；
- 保持 Core frozen；
- Extended authoritative-source research 可并行，但 HSI / industry benchmark / total-market turnover 缺失不得用错误 proxy 填补；
- 为 CH-3 预研 point-in-time IPO heat、近期 IPO 破发/5D 表现、同行业历史 IPO context、liquidity/activity 的正式数据定义与来源；
- 继续维护 PIT / Blind guard。

短期 1D / 5D 预测若要增强，优先从有经济含义且可 point-in-time 验证的 Market Sentiment / IPO context 中找增量，而不是先把 Document 风险强行解释成短期价格预测。

## 5. D — Quant / ML Research

定位：Outcome、canonical dataset、baseline、LightGBM、explainability、实证结论。

已完成：

```text
PR-C 5D Outcome                 COMPLETE / FROZEN
PR-D Canonical Dataset          COMPLETE / FROZEN
PR-E Baseline + Oracle          COMPLETE / FROZEN
PR-F LightGBM + Explainability  COMPLETE / FROZEN
```

PR-F frozen finding：

```text
Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM 与 M 完全预测等价；Oracle `OM-M ROC-AUC -0.0143` 且 bootstrap interval 跨零。正式解释为当前 target / sample / feature / model 条件下没有验证出稳定 Document 增量，而不是“招股书无信号”。

### 当前任务：支持 PR-G

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

D 当前必须支持 PR-G 正确消费：

- 输出只按 `uncalibrated_model_score` 解释；
- 保留 SHAP / bootstrap uncertainty / error caveats；
- 明确产品层使用哪个 frozen Production model / feature group，不允许随机切换；
- 不根据 2024 Validation 继续调参，不做 post-hoc score inversion；
- no 2025 Blind y。

### Competition preparation only

在不启动 formal CH-1 的前提下，D 可准备 1D / 20D / 60D outcome versioning 与 evaluation protocol 草案；PR-H baseline freeze 后才正式执行。多 horizon 的目的不是挑一个最漂亮结果，而是验证结构性 Document 风险与不同时间尺度之间的关系。

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
- 从最新 `main` 正式推进 PR-G Market Agent + Final Supervisor，不直接 merge 旧 preparation branch；
- 正确展示 frozen PR-E / PR-F 的 score、SHAP、calibration status 与 uncertainty；
- Final Supervisor 必须把模型分数作为辅助 warning channel，而不是事实或概率；
- 接入 Document explanation 时只引用输入 Evidence / Risk / Calculation，不创造新事实；
- PR-H 只做不越 Gate 的 contract / UI preparation。

PR-G 的成功标准不是提升 AUC，而是把 Document + Market + Model + Evidence + uncertainty 正确组合成可审计结果。

## 7. 当前协作地图

| Member | Formal status now | Current useful work |
| --- | --- | --- |
| A | integration / Gate owner | PR-G provenance、runtime handoff、freeze boundary、final review |
| B | supporting QA | Evidence / Calculation / page/bbox explanation readiness + CH-2 benchmark prep |
| C | supporting QA | Market/PIT interpretation + CH-3 authoritative sentiment/source research |
| D | modeling support | frozen model/SHAP/uncertainty semantics + multi-horizon protocol prep |
| E | **PR-G formal owner** | Market Agent + Final Supervisor integration |

## 8. 当前严禁混淆的四类工作

### 已冻结主线

PR-A / PR-B / PR-C / PR-D / Oracle v2 / PR-E / PR-F 不因为结果不漂亮、成员换机器或缺本地 runtime 就变回“未完成”。

### Supporting QA

B 的 Evidence QA、C 的 Extended research、D 的 multi-horizon protocol prep、E 的 UI skeleton 可以并行，但不改变 formal Gate。

### Current formal Gate

只有 PR-G 的正式 integration / review / freeze 会推进当前主线状态。

### Competition optimization

Retriever / LLM / Prompt / Agent 大规模重构、Market Sentiment 正式扩展、1D/20D/60D 正式 outcome 都属于 PR-H 之后的 CH 阶段。不能用当前 2024 AUC 作为越级理由。

## 9. Post-PR-F competition strategy

```text
PR-G CURRENT
→ PR-H Streamlit Full E2E + 3–5 real IPO demo
→ v0.4.3 Baseline Freeze
→ CH-0 Scope / metrics lock
→ CH-1 1D / 20D / 60D outcomes
→ CH-2 risk extraction + Evidence benchmark
→ CH-3 Market Sentiment + Competition Skills
→ CH-4 conflict resolution + traceability
→ CH-5 Evidence screenshot + human review
→ CH-6 formal evaluation + submission
```

Competition 直接硬目标：

```text
关键风险要素抽取准确率           >= 80%
关键 Evidence recall            >= 85%
Agent / Tool / Evidence trace   = 100%
```

CH-2 benchmark 未达标后才做 targeted Document enhancement；只有 error attribution 指向语义理解时才引入 LLM semantic layer。短期预测增强优先由 C/D 在 CH-3 从 point-in-time Market Sentiment / IPO context 中寻找。

## 10. Documentation rule

成员交接不再新增长期 `HANDOFF_FINAL` / `PREP_V2` 类文档。临时交接应进入 PR body、issue/comment 或本地 package README；正式事实只进入 active docs、completion report 和 frozen manifest。
