# Oracle Document Modeling Pipeline

> Status: **ORACLE v1 HISTORICAL / ORACLE v2 COMPLETE / FROZEN / EVALUATION-ONLY**  
> Documentation review: **2026-08-23**

Oracle 是评测上限 / 错误归因旁路，永远不是 Production runtime。

## 1. Two Oracle generations

### Oracle v1 — immutable historical snapshot

PR-A 冻结的 Oracle v1：

```text
materialized        60
current eligible    55
Development         55
Validation           0
```

它保留历史审计意义，但不再作为 formal PR-E 当前 Oracle ceiling。

### Oracle v2 — current formal research ceiling

```text
Reviewed Expert Gold
+ valid audit overlays
→ authoritative Production identity reconciliation
→ expert_oracle_document_features_v2
→ frozen Oracle v2 features
```

Frozen result：

```text
annotation inventory       101
valid annotations          100
materialized                98
strict usable               96
Development usable          77
Validation usable           19
feature count              142
identity unresolved          0
evaluation_only            true
production_consumable      false
2025 Blind y accessed      false
```

## 2. Isolation rules

Oracle v2：

- 不读取 PDF；
- 不调用 Production Retriever / Agents / Verifier / Supervisor；
- 不调用 Production `v04_document_features_v1` builder；
- 不把 Gold page / Evidence ID / free-text manual answer 放进 Production X；
- 不进入产品 runtime；
- 不读取 2025 Blind y。

Production identity 对 `case_id / document_id / stock code / cohort year / listing date / split` 具有最终权威；annotation metadata 不能重定义 official cohort。

## 3. Audit precedence

Oracle v2 以 current pass1 为 base，只在 audit overlay 的 source hash 与当前 annotation 匹配时应用对应风险修订。stale overlay 记录为 `stale_not_applied`，不能静默恢复旧 annotation。

跨平台换行差异通过规范化处理，provenance 决策必须 deterministic。

## 4. Frozen v2 anchors

```text
schema_version        expert_oracle_document_features_v2
policy_version        oracle_gold_policy_v2
artifact set          e73dd7f478fd4c421f6794cfa0c7808403cfb5d57dd0678eae1146aaeeff09d6
strict usable set     486a0c7d3977deacb5e3247e184064e96a684dbfdf8ef951b9df6cd32ce4da0f
feature manifest      99eeb0366a50b11b94f6e92820b6f1ef8535d5979ca6266d2af4f78618b40c11
freeze manifest       ddb175f48b7e8134c90c674e44d6173337dc2ea10e9eece103f70ae902e80294
```

完整冻结事实见：

- `docs/V04_ORACLE_REFRESH_GOVERNANCE.md`
- `docs/V04_ORACLE_V2_COMPLETION_REPORT.md`
- `reports/frozen/v04_oracle_v2_manifest.json`

## 5. PR-E integration

formal PR-E 不直接把 98 个 Oracle features 当作和 full Production 一样的 cohort。它先与 frozen PR-D Production matrices 对齐成严格公平 intersection：

```text
96 strict usable
77 Development
19 Validation
```

然后在相同 case set / split / target / preprocessing / model family 上比较：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

## 6. Diagnostic meaning

```text
Production Increment     = PM - M
Document Signal Ceiling  = OM - M
Pipeline Gap              = OM - PM
```

解释：

```text
OM ≈ M
→ 招股书风险信号在当前 target / sample 下可能较弱；优先检查 target、sample、regime 和 statistical power。

OM >> M 且 PM ≈ M
→ 文档信号存在，但 Production Document Pipeline 丢失信息；未来才有理由重启 Retriever / LLM / Agent / Verifier 研究。

PM > M 且 PM ≈ OM
→ Production 已捕获大部分可提取文档信号；优先推进 model / explainability / productization。
```

小样本 non-significance 不能被解释成“没有信号”。Oracle 2024 Validation 只有 19 个 usable case，formal report 必须保留 uncertainty / power caveat。

## 7. Time governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

Development 使用 time-aware evaluation；2024 不参与 feature / model / threshold tuning；2025 y 正式开放前禁止读取。

## 8. Annotation quantity policy

100-case Expert Annotation 目标已实质达到。当前不自动扩到 150 / 200。未来是否扩样由 PR-E power / uncertainty 结果或比赛正式指标决定，而不是因为“样本越多越好”无边界扩张。
