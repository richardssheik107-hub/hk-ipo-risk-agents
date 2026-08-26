# v0.4 Data Readiness — Technical Reference

本文档保留 v0.4 数据层的技术就绪事实。比赛当前 Gate 由 `../V0.4_RELEASE_ACCEPTANCE.md` 维护；最终指标定义由 `../COMPETITION_METRIC_PROTOCOL.md` 维护。冻结 manifest / completion report 中的既有 hash 与实测数字不因比赛收尾策略更新而改变。

## 1. Official cohort / split

```text
Official 2020–2024 IPO cases  438
Development (2020–2023)      368 official identities before target availability filtering
Validation (2024)              70
2025 Blind                     protected
```

Metric-v2：

```text
Development = Existing-Gold diagnosis / code+LLM remediation
Validation  = frozen one-shot confirmation, no post-hoc tuning
Blind       = outcome inaccessible until formal authorization
```

## 2. Production Document-X

```text
Production artifacts           438 / 438
Feature positions              100
```

Document production materialization 已完成；比赛主要问题是 Risk/Evidence semantic quality，不是“有没有 Document-X”。

## 3. Market-X Core

```text
Core cases                     438 / 438
Core positions                  30
Raw features                    15
Missing indicators              15
```

Core 使用 listing-date 前可得数据并保留 missing semantics。

## 4. Market-X Extended readiness

```text
HSI 5D/20D/volatility          438 / 438 available
HKEX turnover 20D              438 / 438 available
Production industry return       0 / 438 PIT-safe available
```

industry return blocker 是 historical company-classification PIT mapping。没有 authoritative historical mapping 时继续 unavailable；不使用未来分类或 zero fill。

## 5. Outcome readiness / M5

Frozen PR-C 5D：

```text
Official                        438
Available                       424
Unavailable                      14
Development available           354
Validation available             70
missing_base_price               12
no_eligible_session               2
```

已有 outcome foundation 定义 1D / 5D / 20D / 60D horizon；final competition materialization 仍未完成。

项目预定义：

```text
primary significant_drop_5d = (return_5d <= -0.10)
robustness cutoff = Development return_5d bottom 20%
```

赛题没有给 5D 绝对 metric pass line。

## 6. Canonical dataset

```text
Model-ready                     424
Development                     354
Validation                       70
Explicit exclusions              14
```

Production / Market / Outcome bulk bindings 和 split rules 保持 fail closed。

## 7. Existing Expert Gold / Oracle v2

现有人工标注 inventory：

```text
Annotation inventory            101
Valid annotations               100
Official materialized            98
Strict usable                     96
Development usable                77
Validation usable                  19
Feature count                    142
```

重要区别：`96 strict usable / 77 / 19` 是原 Oracle/model evaluation 的 outcome-compatible 口径；M1/M2 Document benchmark 不机械套用该分母。

Metric-v2 的 M1/M2 从 `98 official materialized` Existing Gold 出发，通过**只读代码**判断哪些 risk / Evidence unit 实际可评价。

从现在开始：

```text
new manual annotation = forbidden
existing Gold modification = forbidden
UNJUDGED != negative
manual Evidence semantic regrouping = forbidden
```

Oracle v2 仍是 evaluation-only，不进入 production runtime。

## 8. Real prospectus runtime readiness

当前比赛 runner 已验证：

```text
2410.HK    706 physical pages
2460.HK    579 physical pages
1318.HK    617 physical pages
```

```text
SHA-256 verified      3 / 3
byte size verified    3 / 3
page count verified   3 / 3
offline E2E completed 3 / 3
workflow errors       0
outcome labels read   false
```

## 9. Role-B legacy benchmark input readiness

旧 10 个 allowlisted 2020–2023 Development PDF：

```text
found        10 / 10
SHA          10 / 10
page         10 / 10
analyzed     10 / 10
```

旧 offline diagnostic：

```text
Risk P/R/F1          0 / 0 / 0
Evidence Recall@5    20%
Real LLM cases       0
```

这证明 input/runtime ready，不证明 metric-v2 M1/M2 达标。`Recall@5=20%` 继续只作为 legacy diagnostic。

## 10. Metric-v2 Existing-Gold readiness

不再建立新的 20-case Gold target，也不再要求补齐 5 个 primary family。

正式步骤：

```text
Existing Gold frozen
→ read-only coverage audit
→ evaluable manifest + source hash
→ optional small fixed Dev debug subset
→ real-LLM Development run
→ evaluator + failure taxonomy
→ Development-only code/Prompt optimization
→ Full Existing Development Gold benchmark
→ freeze
→ Existing Validation Gold one-shot
```

Competition-priority risk mapping：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但只有 Existing Gold 有 support 才评价；support=0 时 `NOT_EVALUABLE_FROM_EXISTING_GOLD`，不补标。

M1：

```text
Existing-Gold Risk Accuracy >=0.80 official
Project target >=0.85
```

M2：

```text
Existing-Gold Evidence Coverage Recall >=0.85 official
Project target >=0.88
```

Recall@1/@3/@5/@10/@20 仅为 diagnostics。

## 11. Market Agent readiness

C 已完成 IPOHeatSkill、MarketRegimeSkill、structured Market interpretation、PIT/missingness provenance、AI runtime wiring、真实 provider path validation。

最终 3-case demo 若没有本地 Core materialization，Market Channel 可以诚实 unavailable；不得提交 raw licensed data。

## 12. Model runtime readiness

Frozen PR-F cohort results存在，但 original per-case runtime bulk 不在 repo。

```text
authentic hash-bound handoff present → consume
absent / mismatch                    → unavailable
```

不得从 aggregate metrics 反推个股分数，也不得重新训练“等价”模型。

## 13. Evidence grounding readiness

Physical page grounding 已成立。当前 parser 不生成 bbox：真实 2410 测量 706/706 chunk 有 page，0/706 有 bbox。

bbox 为 P2，不得优先于 M1/M2/M5/E1。

## 14. Blind / validation boundary

```text
Development  2020–2023: Existing-Gold remediation / benchmark iteration
Validation   2024: frozen evaluator one-shot confirmation / label-free smoke
Blind        2025: outcome unopened until authorization
```

特别禁止：

- 根据 2024 选择 Evidence Top-K；
- 根据 2024 改 M1/M2 公式；
- 根据 2024 改 5D threshold；
- 根据 2024 score inversion / model retraining；
- 根据 2024 failure 回头补 Gold。

## 15. Current readiness verdict

数据基础设施不再是主瓶颈。比赛收口真实 blocker：

- A/B：Existing-Gold coverage/evaluator + real-LLM M1/M2 optimization；
- D：M5 final 1D/5D/20D/60D；
- E：final matrix remote synthesis；
- C：final Market trace validation；
- A：metric-v2 final integration/release/submission freeze。

明确不重新打开新的 M1/M2 annotation、broad data acquisition、industry PIT research 或大规模模型探索。
