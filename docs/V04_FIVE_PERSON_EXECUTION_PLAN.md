# v0.4 五人执行计划

> Status snapshot: **2026-08-24**  
> PR-A / PR-B / PR-C / PR-D: **COMPLETE / FROZEN**  
> Oracle v2: **COMPLETE / FROZEN / EVALUATION-ONLY**  
> PR-E / PR-F: **COMPLETE / FROZEN**  
> PR-G: **A GATE REVIEW PASS / LOCAL FREEZE MATERIALIZATION PENDING**  
> PR-H: **PREPARATION UNBLOCKED**

## 1. 总原则

正式 Gate / mainline merge 严格串行：

```text
PR-A → PR-B → PR-C → PR-D → PR-E → PR-F
→ PR-G implementation/review
→ PR-G local freeze manifest
→ PR-H
→ Baseline E2E Freeze
→ CH-0..CH-6
```

允许并行的是准备性工作、QA、文档、测试夹具和不改变冻结边界的分析；准备工作不能被描述为后续 Gate 已通过。

PR-F 已得到较弱/不稳定的 2024 预测结果，但这不授权回滚 Gate 顺序、反转模型分数或继续使用 2024 调参。PR-G 实现已经合入 main，A 审阅通过；当前只差必须依赖本地真实 runtime 的 PR-G freeze manifest。PR-H preparation 可以立即开始，formal PR-H 在该 manifest 提交后开始。

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

- PR-G A Gate Review 已完成，结论记录于 `V04_PR_G_A_GATE_REVIEW.md`；
- 在本地真实 prospectus/runtime 上校验 E 生成的 PR-G draft manifest，提交最终 frozen manifest；
- 审核 PR-H governed Market-X runtime 接线，禁止把 legacy `MarketSnapshot` 冒充 PR-B lineage；
- 审核 PR-F 最小 runtime handoff 的 hash、内容边界和 no-label/no-Blind 约束；
- 维护 PR-A–PR-F / Oracle v2 frozen boundary；
- 阻止任何“看到 2024 结果后反转 score / 重调模型再当正式 Validation”的做法；
- PR-H 完成后做 v0.4.3 Baseline E2E Gate review。

## 3. B — Document / Agent

定位：Production Document Intelligence 质量、Evidence / Calculation / page provenance、Document explanation。

### 当前任务

- 支持 PR-H 的 3–5 个真实 demo case，抽样验证 `case → analysis → RiskItem → Evidence → Calculation → page/bbox → Verifier`；
- 对最终报告的 Evidence Index、页码/bbox、Calculation-to-Evidence 链进行 demo-case QA；
- 为 CH-2 维护逐风险 benchmark protocol：Precision / Recall / F1 / Evidence Recall；
- 不因为 5D AUC 低就无差别重写 Retriever / Agent / Prompt。

B 的 QA 是支持性审计，不自动重开 PR-A。Competition 阶段只有直接 benchmark 未达标的风险类别才进入 targeted enhancement。

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

Market-X Extended 已接入 governed CSMAR HSI daily close；438/438 官方 case 的 HSI 5D、20D return 与 20-session volatility 已通过 PIT readiness。

### 当前任务

- 与 A/E 一起完成 PR-H governed runtime market path；
- runtime source-of-truth 使用 `PreListingMarketFeatureSnapshot` 或其无损受控投影，不把 legacy `MarketSnapshot` 反向升级为正式 Market-X；
- HSI provenance 必须真实透传；industry benchmark / turnover 继续显式缺失，禁止 proxy/neutral zero；
- 为 CH-3 预研 point-in-time IPO heat、近期 IPO 破发/5D 表现、同行业历史 IPO context、liquidity/activity；
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

### 当前任务：支持 PR-H

- 不重新调 PR-E/PR-F；
- 为选定 3–5 demo case 从 frozen PR-F runtime 生成最小产品 handoff；
- handoff 只包含产品需要的 per-case score / top SHAP drivers / run identity，不包含 target labels、2025 Blind y、raw licensed data、secrets 或无关模型 bulk；
- handoff 必须带 `SHA256SUMS.txt`，并由 PR-G Tier-2 用 frozen `model_result_hash` fail-closed 绑定；
- 输出仍只按 `uncalibrated_model_score` 解释；
- 保留 SHAP / bootstrap uncertainty / error caveats。

### Competition preparation only

在不启动 formal CH-1 的前提下，D 可准备 1D / 20D / 60D outcome versioning 与 evaluation protocol 草案；PR-H baseline freeze 后才正式执行。多 horizon 的目的不是挑一个最漂亮结果，而是验证结构性 Document 风险与不同时间尺度之间的关系。

## 6. E — Oracle / Product Integration

定位：Oracle research sidecar、Final Supervisor、Market Agent integration、report、Streamlit / Demo。

Oracle v2 已完成并冻结。PR-G implementation 已由 E 完成并合入 main；A 已接受其 protected-interface 设计。

### 当前任务

- 配合 A 完成本地 PR-G freeze manifest materialization；
- 基于最新 main 正式推进 PR-H 的 7-stage Streamlit / report E2E；
- 接入 governed Market-X runtime path 与 PR-F local runtime handoff；
- 清理 UI 中把已冻结 PR-B / PR-F 误写为 blocking gate 的旧文案；
- 对 3–5 个真实 IPO 跑 PDF → Document → Market → Model → Final Supervisor → Report；
- Final Supervisor 继续把模型分数作为辅助 warning channel，而不是事实或概率；
- 保持 Oracle v2 与 Production 隔离；
- 未解决 conflicts 继续显示 uncertainty，CH-4 前不做假仲裁。

PR-H 的成功标准不是提升 AUC，而是把 Document + Market + Model + Evidence + uncertainty 真正跑成可演示、可审计、可复现的闭环。

## 7. 当前协作地图

| Member | Formal status now | Current useful work |
| --- | --- | --- |
| A | PR-G gate owner / PR-H integration reviewer | local freeze manifest、runtime contract、v0.4.3 Gate |
| B | PR-H supporting QA | 3–5 demo Evidence / Calculation / page-bbox QA |
| C | PR-H market runtime owner | governed Market-X runtime + PIT provenance |
| D | PR-H model runtime support | frozen per-case score/SHAP handoff |
| E | **PR-H product owner after PR-G freeze** | Streamlit + Final Report + 3–5 real-case E2E |

## 8. 当前严禁混淆的四类工作

### 已冻结主线

PR-A / PR-B / PR-C / PR-D / Oracle v2 / PR-E / PR-F 不因为结果不漂亮、成员换机器或缺本地 runtime 就变回“未完成”。

### PR-G finalization

A Gate Review 已 PASS；剩余是本地 real-run manifest 的机械冻结，不允许伪造 prospectus hash 或 final-supervision content hash。

### PR-H preparation / execution

Market-X runtime、PR-F runtime handoff、UI stage cleanup、3–5 case demo 是当前有效工作；其中 formal PR-H 状态在 PR-G frozen manifest 提交后切换。

### Competition optimization

Retriever / LLM / Prompt / Agent 大规模重构、Market Sentiment 正式扩展、1D/20D/60D 正式 outcome 都属于 PR-H 之后的 CH 阶段。不能用当前 2024 AUC 作为越级理由。

## 9. Post-PR-F competition strategy

```text
PR-G local freeze FINALIZE
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
