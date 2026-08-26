# Competition Data Overview

本文件记录比赛数据范围、split、主要 materialization 状态与数据治理边界。当前 Gate 见 `V0.4_RELEASE_ACCEPTANCE.md`。

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

## 2. Document data

Production Document-X：

```text
438 / 438
100 positions
```

比赛真实案例当前已验证 3 份 2024 招股书：

```text
ipo_2024_02410 / 2410.HK / 706 pages
ipo_2024_02460 / 2460.HK / 579 pages
ipo_2024_01318 / 1318.HK / 617 pages
```

三份均通过 frozen catalog 的 filename / SHA-256 / byte size / physical-page verification，并完成 offline competition E2E。

此外 Role B 已对 10 个 2020–2023 Development PDF 完成 governed streaming benchmark input validation：10/10 found、10/10 SHA、10/10 page、10/10 analyzed。

这证明输入治理与 parser/runtime 能运行，不证明 Document 风险质量达标。

## 3. Market-X

Frozen PR-B Core：

```text
438 / 438
30 positions = 15 raw + 15 missing indicators
PIT governed
```

Extended readiness：

```text
HSI features              438 / 438
HKEX turnover 20D         438 / 438
production industry return 0 / 438
```

industry return 为 0/438 的原因是缺乏历史时点有效的 authoritative company→industry mapping。禁止使用未来 classification、静态映射或 zero-fill 伪装生产 PIT feature。

Market Intelligence 可以在 Core-only 模式下部分运行；Extended source 缺失时必须保留 missing reason。

## 4. Outcome data

Frozen PR-C 5D governed outcome：

```text
official cases       438
available            424
unavailable           14
Development available 354
Validation available   70
```

missing reasons：

```text
missing_base_price    12
no_eligible_session    2
```

项目更早的 market foundation 已定义 1D / 5D / 20D / 60D 生成语义，但最终比赛多周期 materialization/result package 仍由 D 收口；不要把“schema/engine 存在”写成“final artifact 已完成”。

## 5. Canonical modeling data

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

## 6. Model artifacts

Frozen PR-E/PR-F 研究结果保持历史事实。当前 competition runtime 只有在 authentic frozen PR-F per-case runtime 或 hash-bound sanitized handoff 可用时才展示 model score/driver。

若本地 handoff 不存在：

```text
Model Channel = unavailable
```

不得根据 cohort result 重建 per-case prediction，也不得为了 UI 完整重训模型。

## 7. Real case use of 2024 Validation

2024 案例可用于：

- fixed workflow smoke；
- Evidence/Trace/Product validation；
- 在不读取 outcome label 的情况下验证文档/市场/Agent 链路。

不得用于：

- 根据真实 2024 outcome 反复调 prompt/threshold/model；
- 看完 2024 y 后决定 score inversion；
- 把 Validation 变成开发集。

PR #133 的 2460/1318 运行明确没有读取任何年份 outcome label，因此属于固定分析链验证，不是 outcome tuning。

## 8. 2025 Blind

当前正式规则：

- 可以准备 2025 feature-only inputs；
- 未授权前不得读 2025 outcome/target；
- schema/builder/validator 应 fail closed 防止 Blind y 进入 Development/Validation；
- 每个 formal artifact/report 应保留 `blind_2025_accessed=false` 或等价可审计声明。

## 9. Data → role ownership

- B：Prospectus / Evidence / Document benchmark；
- C：PIT market features / MarketContext；
- D：Outcome / model / evaluation outputs；
- E：最终案例 analysis/trace/review artifacts；
- A：catalog identity、cross-lane provenance、final submission audit。

## 10. Current data-related blockers

真正影响最终比赛提交的数据/产物缺口：

1. B fixed Development benchmark 的 real-LLM predictions + metrics；
2. D final 1D/5D/20D/60D result package；
3. final matrix 的 local Market Core materialization/validation（若最终 demo 要展示 Market 通道）；
4. real-provider Final Supervisor final matrix trace；
5. optional Evidence bbox upstream coordinates。

不把 historical industry mapping 研究或 broad new data acquisition 列为当前 blocker。
