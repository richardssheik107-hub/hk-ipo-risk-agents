# Project Specification — Competition Scope

> 状态日期：`2026-08-29`

## 1. 产品目标

从港股 IPO 招股书、上市前受治理市场数据和冻结模型信号出发，输出方向性风险预警、财务/法务/业务/市场归因、原 PDF Evidence、Agent Trace、上市后多周期验证和可运行原型。

系统是受约束的 Agentic AI 工作流：

```text
PDF → governed Evidence → specialized analysis → verification
+ governed Market Context / Skills
+ governed model signal
→ conflict / re-check / Final Supervisor
→ Trace / Report / UI / API
→ optional Human Review
→ M1 / M2 / M3 / M5 + release audits
```

Human Review 是可选人机协同 surface，不要求人工标注，不是 final Release Gate。

## 2. 赛题能力范围

### 文档风险

当前正式主链覆盖：

- cash runway / cash-burn pressure；
- continuous loss；
- revenue growth；
- customer / supplier concentration；
- redemption rights；
- material litigation / compliance；
- precommercial product。

比赛展示还需补齐或强化：

- core pipeline progress；
- text embellishment；
- related-party transaction；
- comparable IPO valuation。

无 Existing Gold 的新增能力作为 versioned capability / qualitative demonstration，不混入 M1/M2 分母。

### 多智能体与产品

Financial、Legal、Business、Market、Final Supervisor、Skills、conflict/re-check、Evidence Viewer、Trace、single/batch report、Screenshot、API/Streamlit 与 submission artifacts。

Human Review UI/export 保留为 optional capability。

### Dynamic New-IPO

当前 final-three 已完整跑通，但不能把这三家公司当系统能力边界。

目标：

```text
Phase 1: 438 historical frozen universe
Market-X → frozen-model inference → SHAP → Supervisor

Phase 2: arbitrary new IPO
PIT market history → Dynamic Market-X → frozen-model inference → SHAP → Supervisor / report
```

## 3. 不可破坏原则

- 正式风险引用真实 Evidence；LLM 不能越 scope；page/bbox 不由 UI 猜；
- 财务数值、比率、runway 和 outcome 由 deterministic Python 计算；
- Market 只使用 PIT-safe facts，missing 不补零或 proxy；
- frozen score 只能称 `uncalibrated_model_score`；
- dynamic model output 必须来自真实 frozen model inference，不能复制 per-case handoff 冒充；
- Existing Gold immutable，Gold 不进 runtime，`UNJUDGED` 不当 negative；
- Validation freeze 后 one-shot；Blind 输入/outcome 不用于优化；
- 不提交 Secret、授权 PDF、raw EOD、raw journal、本地绝对路径。

## 4. 指标

当前 Release 必需指标：

```text
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
M3 Traceability =1.0
M5 1D / 5D / 20D / 60D；5D 重点
```

冻结 Metric-v2 文件中的 M4 explanation rubric 保留为 optional quality diagnostic；**不要求真人评分，不作为 Release Gate**。

Recall@K 是诊断，不是官方额外门槛。

## 5. 当前 runtime 与诊断

### Document / Role-B

当前 checkpoint：

```text
fixed-journal M1 = 12/30 = 40.00%
fixed-journal M2 = 18/48 = 37.50%
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
```

当前 proven root：`deterministic_fact_missing`，其次是 `retrieval_candidate_miss`。period-candidate 和 broad Parser-preservation 已被 bounded audit 排除为当前主根因。

### Market / Model / Supervision

```text
Market final-three = 3/3
Frozen Model final-three = 3/3
Final Supervisor E1 = 3/3
first-attempt accepted = 3/3
corrections / fallback = 0
M3 = 1.0 x 3
recheck = 17/17
Evidence screenshot = 17/17 precise
seven-stage = 21/21
```

### Team-ready replay

```text
canonical bundle = reports/v045_demo_bundle
cases = 3
files = 66
hash verify = PASS
fresh clone = PASS
Streamlit smoke = PASS
```

## 6. D model tracks

- frozen PR-F：正式 receipt / product identity；
- v2 candidate：Development-selected、2024 one-shot evaluated、未晋升。

v2 candidate：

```text
Recall 52.17%
F1 42.11%
PR-AUC 38.12%
ROC-AUC 48.75%
```

若晋升 v2，必须创建新的 freeze / decision / artifact / handoff，不能覆盖 frozen PR-F 身份，也不能再按 2024 调参。

## 7. 当前主要限制

- B M1/M2 仍明显低于 ALL79 正式门槛；
- D promote/retain 未决；
- final-three 之外的 frozen model dynamic inference 尚未成为产品 runtime；
- arbitrary new IPO 缺 Dynamic PIT Market-X / governed external history path；
- pipeline、粉饰、关联交易、同行估值仍需完整可审计展示；
- one-shot Validation 和最终 secure package 尚未完成。

Final Supervisor、M3、final-three Market/Model、recheck、Evidence screenshots、canonical replay 已不再是当前主要 blocker。

## 8. 完成定义

完整条件见 `V0.4_RELEASE_ACCEPTANCE.md` 和 `COMPETITION_CLOSURE_PLAN.md`。

```text
ALL79 M1/M2
+ M3 100%
+ D formal model decision
+ Dynamic New-IPO / product generalization
+ capability coverage
+ one-shot Validation
+ CI / provenance / determinism / security
+ secure package
```

全部真实通过后才能宣称 `COMPETITION_READY`。
