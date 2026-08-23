# 公共数据 Schema 与 v0.4 建模契约

> Status snapshot: **2026-08-23**  
> PR-D canonical dataset: **COMPLETE / FROZEN**  
> Current formal Gate: **PR-E**

代码中的 Pydantic Schema / validator 是最终权威实现；本文解释跨模块语义和当前 frozen modeling boundary。

## 1. General rules

1. 跨模块正式数据使用明确、可版本化的 Pydantic / Protocol；
2. 缺失值有显式语义，不能自动解释为 `0 / safe / negative`；
3. provenance、source version、feature version、policy/model version 可追踪；
4. identifier、document ID、Evidence ID、Gold page、target-derived value 只能做 provenance，不能进入 X；
5. 失败必须结构化记录，不能 silent drop；
6. 公共 schema 变更必须有 contract tests。

## 2. DocumentChunk

Parser 返回：

```text
list[DocumentChunk]
```

核心语义：

```text
document_id
chunk_id
page
section
text
block_type
bbox
metadata
```

`page` 对应真实 PDF 物理页；`bbox` 可选。

## 3. Evidence

Evidence 支持正式风险结论，至少保留 document / chunk / page / source / text 等 provenance，可选 bbox。

不得虚构页码、文本或来源。无足够 Evidence 的结论进入 pending / needs_review，而不是伪造 verified。

## 4. Calculation

正式数值计算必须可审计：

```text
skill_name / skill_version
inputs
formula
result
unit
evidence_ids
success / error
```

LLM 自然语言计算不能替代 deterministic Calculation。

## 5. RiskItem

Domain Agent 统一输出：

```text
list[RiskItem]
```

核心语义包含：

```text
risk_id
risk_code
category / risk_type
level / score
conclusion
evidence
calculation
agent_name
confidence
verification_status
verification_notes
metadata
```

正式 verification 状态包括：

```text
verified
pending
rejected
needs_review
```

Verifier / Supervisor 不得创造原始 Evidence。

## 6. IPOAnalysisResult and Document snapshot

Production 文档链：

```text
IPOAnalysisResult
→ V03DocumentRiskSnapshot
→ v04_document_features_v1
```

PR-A frozen：

```text
438 / 438 snapshots
438 / 438 Production Document-X
100 ordered positions
```

Document feature artifact 必须绑定 case identity、snapshot/source hash、feature manifest / order。

## 7. Market-X Core

Frozen contract：

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 adjacent missing indicators = 30 positions
```

Market-X Core 通过 PIT 规则保证目标 IPO 上市后数据不进入 X。

Market-X Extended 保持独立可选 contract，不允许静默插入 Core 历史顺序。

## 8. FiveDayOutcomeTarget

PR-C frozen contracts：

```text
policy  v04_5d_outcome_policy_v1
target  v04_5d_outcome_target_v1
```

核心字段语义：

```text
raw_return_5d
poor_performer_5d
availability / missing_reason
policy_hash
threshold_hash
case identity / split / provenance
```

正式 frozen coverage：

```text
424 available
14 unavailable
354 Development
70 Validation
```

Unavailable target 不能 zero-impute。

## 9. Canonical modeling dataset — PR-D frozen

版本：

```text
v04_canonical_modeling_dataset_v1
v04_canonical_model_matrix_v1
```

PR-D 把 Production Document X、Market-X Core、Outcome Y 通过 identity / schema / manifest / hash validation 连接成 424-row model-ready cohort。

正式 feature blocks：

```text
Market Core          30 required
Market Extended      optional, separately versioned
Production Document 100 required
Oracle Document     evaluation-only intersection only
```

Full Production matrices：

```text
M
P
PM
```

Oracle fair-intersection matrices：

```text
M
P
O
PM
OM
```

Component feature names 必须显式 prefix，feature order deterministic。

## 10. Oracle v2

Frozen contract：

```text
schema_version        expert_oracle_document_features_v2
policy_version        oracle_gold_policy_v2
feature_count         142
materialized          98
strict usable         96
Development / Val     77 / 19
evaluation_only       true
production_consumable false
```

Oracle v1 保持 immutable historical snapshot；formal PR-E ceiling 使用 Oracle v2。

## 11. PR-E result semantics

PR-E baseline 输出是 governed research/model artifact。分类模型至少记录 ROC-AUC、PR-AUC、Brier、accuracy、precision、recall、F1；回归记录 MAE、RMSE、R2，并保留 cohort、protocol、feature group、year/fold audit、coefficients/intercept 等审计信息。

Development evaluation 必须 time-aware；2024 Validation 不参与拟合。

未经 calibration 的分数只能称 `score` / model output，不能称真实概率。

## 12. Prediction / Final Supervisor boundary

现有 RuleBasedPredictor 继续只做兼容/对照。v0.4 统计模型只有在 PR-E/PR-F 输出 contract 冻结后才能进入正式产品预测视图。

Final Supervisor 必须消费受控：

```text
verified document risks
market context
model score + score semantics + calibration status
model drivers / uncertainty
```

它不能创造 Evidence、RiskItem 或市场事实。

## 13. Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

所有 target / canonical / matrix / model contracts 都必须 fail closed 地拒绝未经授权的 2025 Blind y。
