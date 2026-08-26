# Competition Data Overview

本文件记录比赛数据范围、split、metric-v1 Gold/Validation/Blind 边界、主要 materialization 状态与数据治理规则。当前 Gate 见 `V0.4_RELEASE_ACCEPTANCE.md`；指标口径见 `COMPETITION_METRIC_PROTOCOL.md`。

## 1. Official universe

正式 2020–2024 IPO universe：

```text
438 cases
```

chronological split：

```text
2020–2023  Development
2024       Validation
2025       Blind（feature-only / outcome 未授权前不可访问）
```

## 2. Metric-v1 data governance

Protocol：

```text
v045_competition_metric_protocol_v1
```

规则：

- Development 可做 Gold annotation、error taxonomy、Prompt/code targeted remediation；
- Validation 只做冻结 protocol 的一次性确认，不根据 2024 结果回头改 metric / threshold / model；
- 2025 Blind y 未授权前不得访问；
- metric allowlist、Gold schema、Risk family mapping、Evidence Group rules、5D threshold 必须在 Validation 重评前冻结。

### Development metric-v1 target

```text
20 fixed Development cases
5 primary risk families
```

当前旧 10-case governed benchmark 可以纳入，但不足部分需要在 prediction freeze 前补齐并冻结 allowlist。

Primary families：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

尽量保证每个 family 至少 5 positive Gold Units；若真实数据不足，使用全部可得 positive 并披露 support，不人为制造 positive。

Gold 至少由 2 名人类 reviewer 做独立/交叉复核。

## 3. Document data

Production Document-X：

```text
438 / 438
100 positions
```

比赛真实案例当前已验证：

```text
ipo_2024_02410 / 2410.HK / 706 pages
ipo_2024_02460 / 2460.HK / 579 pages
ipo_2024_01318 / 1318.HK / 617 pages
```

三份均通过 frozen catalog 的 filename / SHA-256 / byte size / physical-page verification，并完成 offline competition E2E。

Role B 旧 10-case 2020–2023 Development benchmark input validation：

```text
10/10 found
10/10 SHA
10/10 page
10/10 analyzed
```

这证明输入治理与 parser/runtime 能运行，不证明 M1/M2 达标。

## 4. Gold Risk Unit data

M1 Gold Risk Unit 至少包含：

```text
case_id
risk_family
applicable
required_attributes
accepted_evidence_groups[]
annotation_status
reviewer_provenance
```

`applicable=true` 进入 official-aligned Risk Accuracy 分母；`applicable=false` 用于 false-positive/precision 统计，但不允许大量 negative 直接刷高 Primary Accuracy。

数值属性使用 deterministic exact/tolerance rule；枚举使用 canonical value；条款语义使用预先写明的 canonical semantic criteria。

## 5. Evidence Group data

M2 不再把 Top-5 当 official primary denominator。

Human Gold 以“支撑事实”建立 Evidence Group：

```text
risk unit
→ evidence fact group A
→ evidence fact group B
→ ...
```

一个 group 可以包含多个等价 paragraph / table / page anchor。系统命中其中一个被预先接受的等价证据，即覆盖该 group。

Primary：

```text
Evidence Group Coverage Recall
= covered Gold groups / all Gold groups
```

Recall@1/@3/@5/@10/@20 仅作为检索/排序 diagnostics。

当前旧 10-case offline `Evidence Recall@5=20%` 保留原始事实，但不能被直接解释为官方 `>=85%` 的 M2 当前值。

## 6. Market-X

Frozen PR-B Core：

```text
438 / 438
30 positions = 15 raw + 15 missing indicators
PIT governed
```

Extended readiness：

```text
HSI features                438 / 438
HKEX turnover 20D           438 / 438
production industry return    0 / 438
```

industry return 缺失原因是没有历史时点有效的 authoritative company→industry mapping。禁止未来 classification、静态映射或 zero-fill 伪装 PIT。

## 7. Outcome data / M5

Frozen PR-C 5D governed outcome：

```text
official cases          438
available               424
unavailable              14
Development available   354
Validation available     70
```

missing reasons：

```text
missing_base_price    12
no_eligible_session    2
```

已有 foundation 定义 1D / 5D / 20D / 60D 语义，但 final competition materialization 仍由 D 收口。

Metric-v1 已在 Validation 重评前冻结：

```text
significant_drop_5d = (return_5d <= -0.10)
```

Robustness：Development return_5d bottom 20% cutoff，只从 2020–2023 Development 计算一次并冻结。

D 不允许根据 2024 Validation 结果重新选 threshold、score inversion 或重训 frozen PR-F。

## 8. Canonical modeling data

Frozen canonical dataset：

```text
424 model-ready
354 Development
70 Validation
```

Oracle v2 evaluation-only：

```text
98 materialized
96 strict usable
77 Development
19 Validation
142 features
```

Oracle 仅用于 evaluation/diagnosis，不进入 production runtime。

## 9. Model artifacts

Frozen PR-E/PR-F 研究结果保持历史事实。Competition runtime 只有在 authentic frozen PR-F per-case runtime 或 hash-bound sanitized handoff 可用时展示 model score/driver。

若不存在：

```text
Model Channel = unavailable
```

不得从 cohort result 重建 per-case prediction，不得为了 UI 或 M5 结果重训替代。

## 10. 2024 Validation

2024 可以用于：

- fixed workflow smoke；
- Evidence/Trace/Product validation；
- 不读取 outcome 的文档/市场/Agent 链路验证；
- Development metric-v1 闭合后的一次性 frozen evaluator confirmation。

不得用于：

- 看完 2024 outcome 后调 prompt/threshold/model；
- 根据 2024 选择 Evidence K；
- 根据 2024 改 Risk Accuracy 公式；
- 根据 2024 改 significant-drop 5D threshold；
- score inversion / model retraining。

## 11. 2025 Blind

- 可以准备 feature-only inputs；
- 未授权前不得读 outcome/target；
- schema/builder/validator 应 fail closed；
- formal artifact 保留 `blind_2025_accessed=false` 或等价声明。

## 12. Data → role ownership

- B：Prospectus / metric-v1 Gold Risk Units / Evidence Groups / Document benchmark；
- C：PIT market features / MarketContext；
- D：Outcome / 5D definition materialization / model/evaluation；
- E：final case analysis/trace/review + explanation-quality artifact；
- A：metric protocol governance、catalog identity、cross-lane provenance、final submission audit。

## 13. Current data-related blockers

1. B metric-v1 Development Gold + real-LLM predictions + M1/M2 metrics；
2. D final 1D/5D/20D/60D + frozen 5D metrics；
3. final matrix local Market Core validation；
4. real-provider Final Supervisor final matrix trace；
5. E explanation-quality human review artifact；
6. optional Evidence bbox upstream coordinates。

不把 broad historical industry research 或 full new data acquisition 列为当前 blocker。
