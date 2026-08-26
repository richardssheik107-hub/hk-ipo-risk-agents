# Data Schema — Current Contracts

本文件描述当前代码中的 runtime contract，并补充 Metric Protocol v1 的**evaluation artifact boundary**。Pydantic/Protocol 源码仍是 runtime 最终权威；Metric Protocol 不得被误解为偷偷改公共 runtime schema。

## 1. Core document contracts

### Evidence

核心语义：

```text
evidence_id
document_id
chunk_id
page
section
text
source_type
relevance_score
optional bbox
```

约束：

- Evidence 必须来自本次真实文档/受治理 source；
- page identity 不在 UI 修补；
- bbox 缺失就保持缺失；
- LLM 只能引用输入 Evidence ID 子集。

Metric-v1 的 Evidence Group 是**evaluation Gold object**，不是 runtime `Evidence` 替代物。一个 Gold Evidence Group 可以接受多个等价 runtime Evidence/page/table anchor。

### Calculation

精确数值计算的 deterministic provenance object。Financial 风险需要数值推导时，应引用 Calculation，而不是把 LLM 文本当计算依据。

### RiskItem

正式风险结论。风险码必须属于注册表/owner 的 versioned extension；RiskItem 与 Evidence/Calculation 的关系由 Verifier 和治理测试约束。

Metric-v1 的 `cash_burn_pressure` 是 competition evaluation family，可映射既有 `cash_runway`/cash-burn Calculation；这不是 runtime rename。

`related_party_transaction` 如新增，必须 additive/versioned sidecar，不静默修改 frozen baseline registry。

## 2. Competition runtime sidecar

代码位置：`src/ipo_risk/schemas/competition_runtime.py`

当前版本：

```text
competition_runtime_v1
```

所有 competition sidecar model 使用 `extra="forbid"`，未知跨 lane 字段默认 fail closed。

### CompetitionRuntimeIdentity

```text
schema_version
case_id
stock_code
listing_date
run_id
provider_name
model_name
prompt_version
provenance
```

### AgentResultEnvelope

```text
case_id
run_id
agent_name
status
risk_ids[]
evidence_ids[]
calculation_ids[]
provider_name
model_name
prompt_version
warnings[]
metadata
```

### CompetitionConflict

```text
conflict_id
case_id
run_id
involved_agents[]
risk_ids[]
claim_ids[]
summary
evidence_ids[]
status
resolution_note
created_at
```

`status`：detected / rechecking / resolved / partially_resolved / unresolved。

### RecheckRequest

```text
recheck_id
conflict_id
case_id
run_id
requested_by
targets[]
reason
evidence_ids[]
max_attempts
status
created_at
```

`max_attempts=1`。

### TraceEvent

```text
event_id
case_id
run_id
event_type
status
agent_name
action
tool_or_skill
provider_name
model_name
prompt_version
evidence_ids[]
calculation_ids[]
conflict_id
recheck_id
latency_ms
request_id
raw_response_hash
occurred_at
details
```

M3 evaluation 只统计真实 trace。relevant event 必须有 Evidence/Calculation 或 explicit `no_evidence_reason`；remote LLM event 需要 provider/model/prompt/request/hash/latency。

### HumanReview

```text
review_id
case_id
run_id
target_id
original_machine_status
decision
post_review_status
reviewer_id
reviewer_note
evidence_id
page
bbox
reviewed_at
```

HumanReview 是 sidecar，不修改机器生成 RiskItem/Evidence。

## 3. Final Supervisor boundary

公共 competition sidecar 没有为了比赛 metric 强行替换成新 `SupervisorDecision` schema。现有 FinalSupervisionResult / internal bundle 继续作为 runtime truth；metric-v1 只消费其已记录 output/trace。

## 4. Market boundary

- available observation 必须有真实 value/provenance；
- unavailable observation 有明确 missing reason；
- Market LLM 只做定性解释，不拥有数值事实；
- namespaced market references 可以进 Trace，但不伪装成 prospectus Evidence。

## 5. Model signal boundary

```text
score
score_semantics = uncalibrated_model_score
calibration_status
model / run identity
optional signed drivers
availability / missing reason
```

缺 authentic PR-F handoff 时必须 unavailable，不生成替代 score。

## 6. Outcome boundary

已有 foundation 定义 1D/5D/20D/60D horizon。Metric-v1 预先冻结 evaluation label：

```text
significant_drop_5d = (return_5d <= -0.10)
```

这属于 evaluation definition，不改变原始 `return_5d` 数据。

Robustness bottom-20% cutoff 只能从 Development 计算一次并冻结。

## 7. Metric-v1 evaluation artifact boundary

Machine-readable protocol：

```text
configs/v045_competition_metric_protocol.json
protocol_version = v045_competition_metric_protocol_v1
```

这些字段属于 final evaluation handoff，并非公共 runtime Pydantic schema。B/D/E 实现落地后必须由 owner + A 做 code/schema review。

### Role B summary target shape

```text
metric_protocol_version
risk_extraction.official_aligned_accuracy
risk_extraction.precision
risk_extraction.positive_recall
risk_extraction.macro_f1
risk_extraction.per_risk

evidence_coverage.group_coverage_recall
evidence_coverage.gold_group_count
evidence_coverage.covered_group_count
retrieval_diagnostics.recall_at_1
retrieval_diagnostics.recall_at_3
retrieval_diagnostics.recall_at_5
retrieval_diagnostics.recall_at_10
retrieval_diagnostics.recall_at_20
```

Legacy `risk_target_at_least_80_percent` / `evidence_target_at_least_85_percent` bool 如果仍存在，只能作为旧 evaluator compatibility 字段，不能单独证明 metric-v1 PASS。

### Role D evaluation summary target shape

```text
metric_protocol_version
significant_drop_5d_definition
five_day_metrics.precision
five_day_metrics.recall
five_day_metrics.f1
five_day_metrics.pr_auc
five_day_metrics.roc_auc
five_day_metrics.top_10pct_hit_rate
five_day_metrics.top_20pct_hit_rate
five_day_metrics.base_prevalence
blind_2025_y_accessed
```

### Role E explanation-quality target shape

```text
metric_protocol_version
human_reviewer_count
mean_score
minimum_case_score
per_case_scores
```

`explanation_quality.json` 是 evaluation artifact，不改 HumanReview runtime sidecar。

## 8. Identity rules

跨模块至少保持：

```text
case_id
stock_code
listing_date
run_id
```

LLM trace 进一步保留 provider_name / model_name / prompt_version / request_id / raw_response_hash / latency_ms。

任何 cross-lane join 优先稳定 identity/hash，不用公司名称 fuzzy join 作为正式绑定。

## 9. Change policy

- frozen core schema 不原地破坏；
- competition 新字段优先 additive/versioned；
- metric protocol 改动必须在 Validation 重评前完成并 version bump；
- Validation 结果打开后不得原地改 v1 口径；
- UI 不定义后端事实 schema；
- 文档与源码不一致时 runtime 以源码为准，metric evaluation 以 frozen protocol + evaluator version 为准，并修正文档。
