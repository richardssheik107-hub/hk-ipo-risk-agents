# Project Specification — Competition Scope

> 状态日期：`2026-08-29`

## 1. 产品目标

从港股 IPO 招股书、上市前受治理市场数据和冻结模型信号出发，输出方向性风险预警、财务/法务/业务/市场归因、原 PDF Evidence、Agent Trace、模型/SHAP 信号、上市后多周期验证和可运行原型。

系统主链：

```text
PDF
→ governed Evidence
→ Financial / Legal / Business analysis
→ verification / document supervision
+ governed MarketContext
+ governed ModelSignal
→ conflict / targeted re-check
→ Final Supervisor
→ Trace / Report / UI / API
```

Human Review 是 optional 产品 surface，不是当前 final Release Gate。

## 2. 当前五项主任务

| 主任务 | 完成目标 | 优先级 |
|---|---|---|
| M1/M2 Document Intelligence | ALL79 M1 `>=80%`、M2 `>=85%` | P0 |
| Final Frontend / Product | Demo/Historical/Fresh 三种模式真实、清晰、答辩可用 | P0/P1 |
| Dynamic Market-X | 任意合法新 IPO 得到真实 PIT Market-X 或诚实降级 | P0 |
| Dynamic Model / Prediction / SHAP | 满足 feature contract 的案例真实 frozen-model inference + SHAP | P0 |
| Final Integration / Submission | Freeze / Validation / audits / fresh clone / secure bundle | P1 → final P0 |

完整执行细节见 `COMPETITION_CLOSURE_PLAN.md` 和 `team/README.md`。

## 3. 文档风险范围

当前正式主链覆盖：

- cash runway / cash-burn pressure；
- continuous loss；
- revenue growth；
- customer / supplier concentration；
- redemption rights；
- material litigation / compliance；
- precommercial product。

比赛展示还需要真实可审计 proof：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation。

无 Existing Gold 的新增能力作为 `QUALITATIVE DEMONSTRATION`，不混入 M1/M2 分母。

## 4. Role-B 当前执行方式

PR #189 后最新正式 fixed-journal gated：

```text
Batch009 M1 = 14/30 = 46.67%
Batch009 M2 = 21/48 = 43.75%
Batch009 offline = 9/30, 15/48
```

最后一个真实 fresh-provider checkpoint 仍是 Batch005 `11/30,17/48`。fixed-journal gain 与 fresh-provider evidence 必须严格区分。

已接受 Batch008 cash-statement compatibility 和 Batch009 Legal lifecycle recognition；direct ranked concentration-table candidate 已因无 M1/M2 gain 且 supplier existence F1 回归而完整回滚。

当前优先级：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflict fail-closed
→ fixed-vs-fresh LLM / Evidence variance
```

Role-B 可同时修复多个经过 Development evidence 证明的兼容 root，通过 independent commit + bundle benchmark + partial revert 控制回归。有 meaningful gain 后尽快扩样。

正式目标：

```text
ALL79 Development
M1 >=0.80
M2 >=0.85
real_llm_cases =79/79
```

## 5. Dynamic Market-X

final-three `3/3` 与 438 historical artifacts 已证明 historical governed path 可用，但任意新 IPO 仍需要 dynamic runtime。

目标：

```text
identity
→ validated cache / historical artifact
or governed dynamic PIT source
→ strict Market-X builder
→ provenance / schema / hash validation
→ MarketContext
```

有合法数据时真实计算；合法历史不足时明确 `PARTIAL / UNAVAILABLE`。不能用 post-listing target、Blind outcome、zero-fill、final-three copy 或 unsourced proxy。

## 6. Dynamic Model / SHAP

当前 final-three frozen Model `3/3 available` 是稳定产品基线，但主要来自 receipt-bound per-case handoff。

最终目标：

```text
governed feature vector
+ final frozen model artifact/hash
→ runtime inference
→ uncalibrated_model_score
→ frozen alert/classification policy
→ native SHAP / signed drivers
→ ModelSignal
```

必须完成 frozen PR-F vs v2 candidate 的正式 promote/retain 决议。任何 promotion 都创建新的 versioned freeze / receipt，不允许覆盖历史身份或根据 2024 Validation 继续调参。

## 7. Final Frontend

最终前端必须同时支持：

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

重点展示 Risk/Evidence、Market、Model/SHAP、Conflict/Recheck、Final Supervisor、Report/Trace，而不是大段内部 JSON。

所有 `AVAILABLE / PARTIAL / UNAVAILABLE` 来自真实 runtime contract。UI 不自行计算、补值或伪造 channel state。

发行人可通过 official catalog-backed search 自动匹配公司名、股票代码和上市日期；正式 downstream identity join 仍依赖 governed identity。

## 8. 当前稳定基线

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Frozen Model final-three = 3/3
recheck = 17/17
Evidence screenshot = 17/17 precise
seven-stage = 21/21
canonical replay = 66 files
fresh clone / Streamlit smoke / team-ready checks = PASS
```

这些能力后续原则上只做回归保护。

## 9. 不可破坏原则

- 正式风险引用真实 Evidence；LLM 不能越 scope；page/bbox 不由 UI 猜；
- exact 数值、期间、比例、runway 和 outcome 由 deterministic Python 计算；
- Market 只使用 PIT-safe facts，missing 不补零；
- frozen score 只能称 `uncalibrated_model_score`；
- dynamic model output 必须来自真实 frozen model inference；
- Existing Gold immutable，Gold 不进 runtime，`UNJUDGED != negative`；
- Validation freeze 后 one-shot；Blind 不用于优化；
- 不提交 Secret、授权 PDF、raw EOD、raw journal、本地绝对路径。

## 10. 指标与完成定义

Release 必需：

```text
M1 Existing-Gold Risk Accuracy >=0.80 on ALL79 Development
M2 Existing-Gold Evidence Coverage Recall >=0.85 on ALL79 Development
M3 Traceability =1.0
M5 1D / 5D / 20D / 60D recorded honestly
```

完整完成条件：

```text
ALL79 M1/M2
+ M3 100%
+ Dynamic Market-X
+ formal D model decision + Dynamic Model / SHAP
+ final frontend
+ capability proof
+ one-shot Validation
+ CI / provenance / determinism / security / licensing
+ fresh clone
+ secure package
```

全部真实通过后才能宣称 `COMPETITION_READY`。
