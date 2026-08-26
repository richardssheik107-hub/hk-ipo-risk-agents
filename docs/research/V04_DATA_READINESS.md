# v0.4 Data Readiness — Technical Reference

本文档保留 v0.4 数据层的技术就绪事实；比赛当前 Gate 由 `../V0.4_RELEASE_ACCEPTANCE.md` 维护。冻结 manifest / completion report 中的既有 hash 与实测数字不因本文件更新而改变。

## 1. Official cohort

```text
Official 2020–2024 IPO cases  438
Development (2020–2023)      368 official identities before target availability filtering
Validation (2024)              70
2025 Blind                     protected
```

## 2. Production Document-X

```text
Production artifacts           438 / 438
Feature positions              100
```

Document production materialization 已完成；比赛阶段的主要问题不是“有没有 Document-X”，而是 Legal/Business/RiskItem 的语义抽取质量。

## 3. Market-X Core

```text
Core cases                     438 / 438
Core positions                  30
Raw features                    15
Missing indicators              15
```

Core 使用 listing-date 前可得数据并保留 missing semantics。Frozen Core 不因后续 Extended/Market Agent 改动而重写。

## 4. Market-X Extended readiness

当前受治理数据结论：

```text
HSI 5D/20D/volatility          438 / 438 available
HKEX turnover 20D              438 / 438 available
Production industry return       0 / 438 PIT-safe available
```

industry return 的 blocker 是 historical company-classification PIT mapping，不是价格序列本身。没有 authoritative historical mapping 时继续 unavailable；不使用静态未来分类、counterfactual mapping 或 zero fill 进入 production。

Market Intelligence 已能在 Core-only 输入上合法降级。

## 5. Outcome readiness

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

已有 outcome foundation 定义 1D / 5D / 20D / 60D horizon。**最终 competition multi-horizon artifact 仍未物化完成**；这是 D 当前交付 Gate，而不是数据 schema blocker。

## 6. Canonical dataset

Frozen PR-D：

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

Oracle v2 为 evaluation-only；不得作为 production feature source。

## 8. Real prospectus runtime readiness

当前比赛 runner 已通过 frozen catalog 安全解析并验证：

```text
2410.HK    706 physical pages
2460.HK    579 physical pages
1318.HK    617 physical pages
```

三份：

```text
SHA-256 verified      3 / 3
byte size verified    3 / 3
page count verified   3 / 3
offline E2E completed 3 / 3
workflow errors       0
outcome labels read   false
```

因此“真实 demo PDF 不足”不再是当前数据 blocker。

## 9. Role-B benchmark input readiness

10 个 allowlisted 2020–2023 Development PDF 已通过 governed streaming run：

```text
found        10 / 10
SHA          10 / 10
page         10 / 10
analyzed     10 / 10
```

但 quality benchmark 为：

```text
Risk P/R/F1          0 / 0 / 0
Evidence Recall@5    20%
Real LLM cases       0
```

所以 Document 数据输入是 ready 的，**Document semantic quality 不是 ready 的**。B 需要在同一固定 benchmark 上测 real-LLM path。

## 10. Market Agent runtime readiness

C 已完成：

- IPOHeatSkill；
- MarketRegimeSkill；
- structured Market interpretation；
- PIT/missingness provenance；
- AI runtime wiring；
- 两只真实 IPO 的 real-provider Market LLM validation。

最终 3-case demo workspace 若没有本地 `reports/v04_pr_b/core_features` 等 ignored runtime materialization，Market Channel 可以诚实 unavailable；A/C 应在最终 demo 机器上物化/验证，而不是提交 raw licensed data。

## 11. Model runtime readiness

Frozen PR-F cohort results存在，但 original per-case runtime bulk 不在 repo。

当前规则：

```text
authentic hash-bound handoff present → consume
absent / mismatch                  → unavailable
```

不允许从 frozen aggregate metrics 反推个股分数，也不允许重新训练一个“等价”模型来关闭历史 PR-H。

## 12. Evidence grounding readiness

Physical page grounding 已成立。当前 parser 不生成 bbox：真实 2410 测量 706/706 chunk 有 page，0/706 有 bbox。

bbox 若补齐会改变 Evidence content/hash，应由 B 实现、A 做 provenance/version review；UI 不得推断坐标。

## 13. Blind / validation boundary

```text
Development  2020–2023: allowed for remediation / benchmark iteration
Validation   2024: fixed evaluation and label-free workflow smoke, not tuning
Blind        2025: outcome unopened until formal authorization
```

所有 final evaluation/output scripts 应继续保持这一边界。

## 14. Current readiness verdict

数据基础设施已不再是主瓶颈。比赛收口的真实 blocker 是：

- B：real-LLM Document quality evidence；
- D：final multi-horizon results；
- E：final matrix remote synthesis；
- A：最终 integration/release/submission freeze。

不应重新打开 broad data acquisition、industry PIT research 或大规模模型探索来替代这些直接 Gate。
