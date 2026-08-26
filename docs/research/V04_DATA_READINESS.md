# v0.4 Data Readiness — Technical Reference

本文档保留 v0.4 数据层的技术就绪事实。比赛当前 Gate 由 `../V0.4_RELEASE_ACCEPTANCE.md` 维护；最终指标定义由 `../COMPETITION_METRIC_PROTOCOL.md` 维护。冻结 manifest / completion report 中的既有 hash 与实测数字不因 Metric Protocol v1 更新而改变。

## 1. Official cohort / split

```text
Official 2020–2024 IPO cases  438
Development (2020–2023)      368 official identities before target availability filtering
Validation (2024)              70
2025 Blind                     protected
```

Metric-v1 规则：

```text
Development = Gold / diagnosis / targeted remediation
Validation  = frozen-protocol one-shot confirmation, no post-hoc tuning
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

Core 使用 listing-date 前可得数据并保留 missing semantics。Frozen Core 不因后续 Extended/Market Agent/metric 改动而重写。

## 4. Market-X Extended readiness

```text
HSI 5D/20D/volatility          438 / 438 available
HKEX turnover 20D              438 / 438 available
Production industry return       0 / 438 PIT-safe available
```

industry return blocker 是 historical company-classification PIT mapping。没有 authoritative historical mapping 时继续 unavailable；不使用未来分类、counterfactual mapping 或 zero fill。

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

Metric-v1 已在 Validation 重评前冻结：

```text
primary significant_drop_5d = (return_5d <= -0.10)
robustness cutoff = Development return_5d bottom 20%
```

Robustness cutoff 只能从 Development 计算一次。赛题没有给 5D 绝对 metric pass line，项目不人为制造“官方 xx%”。

## 6. Canonical dataset

```text
Model-ready                     424
Development                     354
Validation                       70
Explicit exclusions              14
```

Production / Market / Outcome bulk bindings 和 split rules 保持 fail closed。

## 7. Oracle v2

```text
Annotation inventory            101
Materialized                     98
Strict usable                    96
Development usable               77
Validation usable                19
Feature count                   142
```

Oracle v2 为 evaluation-only，不作为 production feature source。

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

因此真实 demo PDF 不足不再是数据 blocker。

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

这证明输入/runtime ready，不证明 metric-v1 M1/M2 达标。

尤其：`Evidence Recall@5=20%` 继续保留为历史 ranking/end-to-end diagnostic；赛题原文件没有规定 Top-K，因此它不再被直接解释为官方 Evidence `>=85%` 的当前值。

## 10. Metric-v1 Development Gold readiness

最终 M1/M2 target：

```text
20 fixed Development cases
5 primary risk families
>=2 human reviewers for Gold
```

Primary families：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

当前 10 cases 可纳入。尽量每个 family 至少 5 positive Gold Units；若真实 support 不足，使用全部可得 positive 并披露 support，禁止人为制造 positive。

### M1 Gold Risk Unit

至少：

```text
case_id
risk_family
applicable
required_attributes
accepted_evidence_groups
annotation_status
reviewer_provenance
```

Primary official-aligned Accuracy 只以 positive Gold Units 为分母，避免 true-negative-heavy accuracy。

### M2 Evidence Groups

Gold 按“支撑事实”分组；一个 Evidence Group 可以包含多个等价段落/表格/page anchors。

```text
Evidence Group Coverage Recall >=0.85 official-aligned pass
Project target >=0.88
```

Recall@1/@3/@5/@10/@20 仅为 secondary diagnostics。

## 11. Market Agent readiness

C 已完成 IPOHeatSkill、MarketRegimeSkill、structured Market interpretation、PIT/missingness provenance、AI runtime wiring、真实 provider path validation。

最终 3-case demo 若没有本地 Core materialization，Market Channel 可以诚实 unavailable；最终提交机器需要物化/验证 governed artifact，而不是提交 raw licensed data。

## 12. Model runtime readiness

Frozen PR-F cohort results存在，但 original per-case runtime bulk 不在 repo。

```text
authentic hash-bound handoff present → consume
absent / mismatch                    → unavailable
```

不得从 aggregate metrics 反推个股分数，也不得为了 M5/UI 重新训练“等价”模型。

## 13. Evidence grounding readiness

Physical page grounding 已成立。当前 parser 不生成 bbox：真实 2410 测量 706/706 chunk 有 page，0/706 有 bbox。

bbox 若补齐会改变 Evidence content/hash，应由 B 实现、A 做 provenance/version review；UI 不得推断坐标。它低于 M1/M2/M5/E1/E2 hard Gate。

## 14. Blind / validation boundary

```text
Development  2020–2023: remediation / Gold / benchmark iteration
Validation   2024: frozen evaluator confirmation / label-free workflow smoke
Blind        2025: outcome unopened until authorization
```

特别禁止：

- 根据 2024 选择 Evidence Top-K；
- 根据 2024 改 Risk Accuracy 公式；
- 根据 2024 改 5D significant-drop threshold；
- 根据 2024 score inversion / model retraining。

## 15. Current readiness verdict

数据基础设施不再是主瓶颈。比赛收口真实 blocker：

- B：metric-v1 Development Gold + real-LLM M1/M2；
- D：M5 final 1D/5D/20D/60D + frozen 5D metrics；
- E：final matrix remote synthesis + M4 explanation-quality artifact；
- C：final Market trace validation；
- A：metric-v1 final integration/release/submission freeze。

不应重新打开 broad data acquisition、industry PIT research 或大规模模型探索来替代这些直接 Gate。
