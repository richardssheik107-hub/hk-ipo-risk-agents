# Competition Closure Plan — Frontend-First Parallel Submission Sprint

> 状态日期：`2026-08-29`
>
> 版本锚点：以本文件所在提交为准
>
> 当前结论：**NOT COMPETITION_READY**

指标口径仍以 `COMPETITION_METRIC_PROTOCOL.md` 为准；最终 Release Gate 仍以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## 0. 提交前加速模式

从现在起项目采用两层状态，不再让最终比赛 Gate 锁死研发和前端：

```text
Current-case Runtime / Product Completion
    = 这个案例的页面、API、报告、Trace 是否真实跑通并可展示

Competition Release Readiness
    = M1/M2/M3/M4/M5、final-three、Validation、审计、封包是否全部真实通过
```

### 0.1 前端绿色的定义

一个 current-case stage 真实执行并物化了该阶段的 governed product state，即可在 7-stage UI 显示 **已完成 / 绿色**。

例如：

- Market-X 本次运行没有可用值：Market stage 仍可“已完成”，但内部必须显示 `Market channel = unavailable/partial` 和真实 missing reason；
- authentic PR-F handoff 缺失：Prediction/Explainability 页面仍可“已完成”，但 `Model channel` / `Model drivers` 必须显示 unavailable；
- real LLM Final Supervisor 失败并使用 deterministic fallback：Supervisor stage 可以“已完成”，但必须明确 fallback，且绝不计入 real-provider accepted；
- current-case report sections 已物化：Final Report 直接绿色，不等待整个项目 `COMPETITION_READY`。

因此：

```text
绿色 = 当前案例产品阶段真实完成
绿色 != 所有可选通道均 available
绿色 != 比赛最终 Gate PASS
```

### 0.2 Final Gates 只阻止最终提交宣称

以下硬 Gate 仍必须真实关闭，但不再阻止无直接依赖的普通开发/合并：

- B ALL 79 Development M1/M2；
- D model promotion / strict revalidation / final-three；
- C/E final-three runtime；
- M4 6 份真人评审；
- one-shot Validation；
- final audits / secure bundle。

缺其中任何一项都不能标记 `COMPETITION_READY`，但 UI、API、Report、Trace、Evidence、adapter、projection、capability demo 等工作继续并行推进。

## 1. 最新合入状态

当前 main 已经把“先看到完整产品”需要的关键基础连续补齐：

### Frontend runtime completion — merged PR #168

- runtime completion 与 project readiness 分离；
- `hybrid_bm25` / recall parser 正确显示为 real runtime component；
- authentic `market_intelligence` / `model_prediction` 投影进入 UI payload；
- materialized current-case report 不再等待旧 PR-H Gate 才可显示完成。

### Evidence bbox — merged PR #169

- PyMuPDF 现在提供真实 PDF 坐标 bbox；
- 当前粒度为 `page_text_union`，不伪造 snippet-level 坐标；
- Evidence Viewer 可以直接消费真实 bbox；
- 下一步是精确 quote/snippet 定位与 screenshot export，而不是“等待 parser 完全没有 bbox”。

### Market strict metadata — merged PR #170

- 已知 MarketObservation 即使 `value=None`，也保留稳定 unit / derivation metadata；
- 不补零、不填 proxy、不伪造 unavailable observation；
- 代码合同已落地，仍需 final-three 当前运行验证完整 3/3。

### E / M3 当前事实

- current-main 三案例 real-provider 最近一次测得 accepted `3/3`；
- M3 三案均 `1.0`；
- 历史也出现过 2/3，说明 LLM acceptance 有抽样波动，因此 Release Gate 仍保留稳定性要求；
- deterministic fallback 保障产品链继续展示，但不冒充 real-provider success。

## 2. 当前赛题闭环

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial / Legal / Business
→ Verifier / Document Supervisor
→ Market-X / Market Intelligence
→ optional authentic model signal
→ Conflict / bounded re-check
→ LLM Final Supervisor or explicit deterministic fallback
→ Trace / Human Review
→ Final Report / UI / API
→ M1–M5 / Validation / final package
```

当前策略不是“等上游全部毕业后再接下一层”，而是**每一层有真实输出就立刻接产品面，缺失通道显式降级**。

## 3. 并行工作轨

### Track P0 — Product / Frontend Full Green

目标：尽快让一个真实 current-case 在前端看到完整 7-stage 产品链。

执行：

1. 当前案例完成的 stage 全部绿色；
2. optional Market/Model/LLM channel 缺失在卡片内部显式显示；
3. Risk/Evidence/Calculation/Trace/Human Review/Report 全部暴露；
4. bbox/screenshot 使用真实 geometry；
5. report、Markdown/JSON download、API/UI 路径全部可操作；
6. 准备真实已运行 artifact 的 replay/static demo backup；
7. 不用 fake 数据填满页面。

这个 Track 不等待 B M1/M2、M4 或 D final model 完成。

### Track B — Document Intelligence Quality

持续自治优化：

- Parser preservation；
- Retriever / ranking / context；
- deterministic extraction / fact conversion；
- LLM structured quality / variance；
- Builder / reconciliation / Verifier；
- final Evidence binding。

fixed-10 是快速诊断工具；达到稳定提升后尽快扩到 larger Development checkpoint，最终必须 ALL 79 Development：

```text
M1 >= 0.80（target >= 0.85）
M2 >= 0.85（target >= 0.88）
real_llm_cases = 79
Validation = false
Blind input/outcome not used for optimization
```

B 未达标不阻止前端、Market、D、E 和产品能力继续合并。

### Track C — Market / Comparable Context

并行完成：

- final-three strict observation runtime `3/3`；
- Market observation availability / missing reason / unit / derivation 完整；
- PIT-safe comparable IPO / valuation capability；
- Market trace；
- unavailable 数据不补零、不造 proxy。

PR #170 已关闭 metadata contract 代码缺口，下一步直接做 final-three 实测和产品展示。

### Track D — Outcome / Business Value

并行完成：

1. A 对 frozen PR-F / v2 candidate 做 promote/retain 决议；
2. current-main strict revalidation；
3. resume / fresh-directory determinism；
4. final-three label-free handoff；
5. prediction table；
6. 业务价值、alert 工作量与局限诚实解释。

D 没有正式 per-case handoff 时，前端 Model channel 显示 unavailable；不阻止其余 6 个产品阶段跑通。

### Track E — Supervisor / Review / Cases

并行完成：

- current final-three real-provider acceptance 稳定性；
- conflict / recheck / severity floor；
- M3 保持 1.0；
- Human Review UI / API；
- 三个 case report；
- M4 评审材料。

M4 真正的两名独立真人 × 3 案仍是 Release Gate；代码和评审界面不等待真人提交才能完成。

### Track Capability — 赛题能力展示

不等待最终定量 Gate，尽快补齐真实、可审计案例：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation；
- Evidence screenshot；
- single/batch report；
- API/UI 人机复核。

无 Existing Gold 的能力标记为 `qualitative demonstration`，不混入 M1/M2。

## 4. 快速协作与合并政策

普通 PR 的合并条件：

```text
CI green
相关 contract/regression tests green
主题清晰
无已知功能回归
无 fake PASS / fake value
无 Gold/Validation/Blind 泄漏
无 Secret/licensed raw data/local absolute path
```

普通 PR **不需要**等待：

```text
M1/M2 final pass
M4 human review
D final model
C/E final-three
submission package
```

Ownership 是 stewardship 而不是锁。兼容的 additive adapter/projection/test 可以跨 lane 快速补齐；破坏兼容的公共接口变更才需要更高等级协调。

若某 lane 被授权 PDF、EOD、frozen runtime 或真人 reviewer 卡住：记录 blocker，立即切换其他可做工作，不整队等待。

## 5. 仍不可放松的硬边界

提交期加速不改变：

- Existing Gold immutable；
- `UNJUDGED != negative`；
- Gold 不进入 runtime Retriever/Prompt/Agent；
- Validation 只能 freeze 后 one-shot；
- 2025 Blind 不用于优化；
- 无 company/stock/case/page/Gold-text 特判；
- LLM 不得 invent Evidence / market fact；
- exact financial claim 由 deterministic Calculation 支撑；
- Market PIT-safe；
- fallback 不冒充 real-provider accepted；
- UI 不伪造 bbox、model score、SHAP、Market 数值；
- Secret/PDF/raw EOD/absolute path 不进 Git/bundle。

## 6. Final Release Gate

只有以下全部真实完成，才允许：

```text
M1 >= 80%
+ M2 >= 85%
+ M3 = 100%
+ M4 PASS
+ D model decision / strict revalidation / final-three PASS
+ Market final-three strict runtime PASS
+ Final Supervisor final-three accepted/stability evidence
+ Evidence screenshots / reports / API/UI ready
+ one-shot Validation completed under freeze
+ latest-main CI
+ Blind / provenance / determinism / security audits
+ secure package PASS
= COMPETITION_READY
```

在此之前，项目可以拥有完整绿色 current-case 产品链，但 Release 状态必须继续显示 **NOT COMPETITION_READY**。
