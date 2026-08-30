# Project Specification — Competition Scope

> 状态日期：`2026-08-30`

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
| M1/M2 Document Intelligence | ALL79 已完成；M1/M2 未达门槛并冻结 | FAIL / FROZEN |
| Final Frontend / Product | Demo/Historical/Fresh 三种模式与 channel truth 已验收 | PASS |
| Dynamic Market-X | 562 个受治理案例 strict audit 已通过 | PASS |
| Dynamic Model / Prediction / SHAP | 满足 feature contract 的案例真实 frozen-model inference + SHAP | PASS |
| Final Integration / Submission | 最终审计 / clean clone / secure bundle；Validation 被 G2 阻塞 | OPEN / P0 |

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

## 4. Role-B 最终冻结测量

```text
real-LLM gated: 79/79 cases
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
316 tasks; 310 structured+scope valid; 6 fallback; 0 transport failure

deterministic offline (selected):
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%
```

real-LLM candidate 删除 9 个正确 deterministic Risk 和 12 个正确 Evidence，
monotonicity 失败，因此不 promote。ALL79 已完成但未达 M1 80% / M2 85%；
submission freeze 下不再迭代算法。

正式目标：

```text
ALL79 Development
M1 >=0.80
M2 >=0.85
real_llm_cases =79/79
```

## 5. Dynamic Market-X

Dynamic Market-X 已通过 562 个受治理案例的 strict audit：438 frozen + 124 dynamic PIT，0 integrity violation；覆盖外或合法历史不足时诚实降级。

已实现链路：

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

final-three frozen Model `3/3 available` 是稳定产品基线；泛化 runtime 已通过严格审计，
达到 540/562 inference、537 outside per-case handoff、70/70 parity、0 mismatch。

已实现链路：

```text
governed feature vector
+ final frozen model artifact/hash
→ runtime inference
→ uncalibrated_model_score
→ frozen alert/classification policy
→ native SHAP / signed drivers
→ ModelSignal
```

`PROMOTE_V2` 已通过 A-owned PR #184 生效。V2 使用独立 versioned freeze / receipt / handoff，
不覆盖历史 PR-F 身份；禁止根据 2024 Validation 继续调参。

## 7. Final Frontend

最终前端验收已通过，并同时支持：

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
