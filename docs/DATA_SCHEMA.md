# 公共数据 Schema 与 v0.4 / Competition 建模契约

> Status snapshot: **2026-08-25**  
> Frozen baseline through PR-G: **COMPLETE**  
> Current Gate: **PR-H PARTIAL / BLOCKED**

代码中的 Pydantic Schema / validator 是最终权威实现；本文只解释跨模块语义、frozen baseline 和比赛阶段允许新增的 versioned contracts。

## 1. General rules

1. 跨模块正式数据必须 versioned；
2. missing 必须有显式语义，不能自动变成 `0 / safe / negative`；
3. identity / provenance / source / policy / feature/model version 可追踪；
4. document ID、Evidence ID、Gold page、target-derived value 只能作为 provenance，不能泄漏进入 X；
5. failure 必须结构化记录，不能 silent drop；
6. public schema change 必须有 contract tests；
7. frozen contract 不被 competition work 原地改写，新能力使用新 version/sidecar。

## 2. DocumentChunk / Evidence / Calculation

`DocumentChunk` 核心：

```text
document_id / chunk_id / page / section / text / block_type / bbox / metadata
```

Evidence 至少保留 document/chunk/page/source/text，可选 bbox。不得虚构页码、文本或来源。

Calculation 至少保留：

```text
skill_name / skill_version
inputs / formula / result / unit
evidence_ids
success / error
```

## 3. RiskItem

Domain Agent 统一输出 `list[RiskItem]`。核心语义：

```text
risk_id / risk_code / category
level / score / conclusion
evidence / calculation
agent_name
verification_status / notes
metadata
```

正式状态：

```text
verified / pending / rejected / needs_review
```

Verifier / Supervisor 不创造原始 Evidence。

## 4. Production Document-X — frozen

```text
IPOAnalysisResult
→ V03DocumentRiskSnapshot
→ v04_document_features_v1
```

Frozen:

```text
438 / 438
100 ordered positions
```

Competition CH-2 可创建独立 benchmark representation / compact `P-Core` version，但不能覆盖 `v04_document_features_v1`，且 feature choice 必须在不使用 2024 tuning 的前提下预先定义。

## 5. Market-X

### Core — frozen

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 adjacent missing indicators = 30 positions
438 / 438
```

### Extended — governed optional

当前可用：

```text
hsi_return_5d / hsi_return_20d / market_volatility_20d  438 / 438
market_turnover_20d_mean                                438 / 438
```

当前不可用：

```text
industry_return_5d / industry_return_20d                 0 / 438
```

Industry missing reason 必须保留 `INDUSTRY_MAPPING_PIT_BLOCKED` 或正式支持的缺失语义。

CH-3 Competition Market features 必须独立 version，并同时记录：

```text
value
availability / missing_reason
as_of / cutoff semantics
source / provenance
feature version
```

## 6. Outcome baseline — frozen

PR-C:

```text
policy  v04_5d_outcome_policy_v1
target  v04_5d_outcome_target_v1
```

```text
raw_return_5d
poor_performer_5d
availability / missing_reason
policy_hash / threshold_hash
identity / split / provenance
```

Coverage:

```text
424 available
14 unavailable
354 Development
70 Validation
```

## 7. Competition multi-horizon outcomes — planned versioned sidecar

CH-1 must **not** mutate the frozen PR-C target. New contracts should separately version:

```text
raw_return_1d
raw_return_20d
raw_return_60d
market_adjusted_return_1d / 5d / 20d / 60d
max_drawdown_20d / 60d
volatility_20d / 60d
severe_break_flag
```

Required semantics:

```text
case identity
listing/session policy
base/terminal price provenance
availability / missing_reason
horizon
split
policy_version
content hash
```

## 8. Canonical modeling dataset — frozen baseline

```text
v04_canonical_modeling_dataset_v1
v04_canonical_model_matrix_v1
```

Frozen cohort: `424 = 354 Development + 70 Validation`.

Feature blocks:

```text
Market Core          30 required
Market Extended      optional / versioned
Production Document 100 required
Oracle Document      evaluation-only intersection
```

Frozen arms: `M / P / PM` and Oracle intersection `M / P / O / PM / OM`.

Competition matrices must use a new version when adding outcome horizon, P-Core or Competition Market features. They cannot silently change frozen matrices.

## 9. Oracle v2

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

Oracle is diagnostic only; Gold cannot become Production input.

## 10. Model output semantics

Every model output consumed by product must carry at least:

```text
model/run identity
case identity
score
score_semantics
calibration_status
feature/model version
optional signed drivers / SHAP
uncertainty / caveat metadata
```

Current frozen product semantics: `uncalibrated_model_score`.

## 11. Final Supervisor input boundary

Final Supervisor may consume only governed:

```text
verified/pending document risks
Evidence / Calculation references
Market Context
model score + semantics + calibration
model drivers / uncertainty
rule signal
conflicts / trace where available
```

It may synthesize and prioritize but cannot create raw Evidence, new source market facts or a new model score.

## 12. Competition trace / conflict contract — CH-4 planned

Versioned trace should minimally support:

```text
agent_name
input_task
plan_step
tool_or_skill_call
input_evidence_ids
calculation_ids
claim
verifier_status
conflict_id
resolution_action
final_status
```

`resolved` and `unresolved` are distinct; unresolved uncertainty is not dropped.

## 13. Human review / Evidence Viewer — CH-5 planned

Reviewer sidecar must keep machine result and human intervention separate:

```text
original_claim
page / bbox / evidence_id
reviewer_decision
reviewer_note
review_timestamp / review identity
post_review_status
```

UI annotations do not mutate source PDF/Evidence identity.

## 14. Time / Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

All new target/matrix/model contracts must fail closed on unauthorized 2025 y. Competition work does not turn 2024 into a tuning set.
