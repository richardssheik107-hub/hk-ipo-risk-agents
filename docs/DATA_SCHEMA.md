# Data Schema — Current Contracts

本文件描述当前代码中的 runtime contract，并补充 Metric Protocol v2 的**evaluation artifact boundary**。Pydantic/Protocol 源码仍是 runtime 最终权威；Metric Protocol 不得被误解为偷偷改公共 runtime schema。

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

Metric-v2 的 Existing-Gold Evidence Unit 是**evaluation object**，不是 runtime `Evidence` 替代物。它只能来自比赛收尾前已经存在的 Expert Annotation / valid audit overlay；不新增人工 Evidence，也不人工重做 semantic group。

### Calculation

精确数值计算的 deterministic provenance object。Financial 风险需要数值推导时，应引用 Calculation，而不是把 LLM 文本当计算依据。

### RiskItem

正式风险结论。风险码必须属于注册表/owner 的 versioned extension；RiskItem 与 Evidence/Calculation 的关系由 Verifier 和治理测试约束。

Competition-priority `cash_burn_pressure` 仍可作为 evaluation mapping 到既有 `cash_runway`/cash-burn Calculation，但只有 Existing Gold 有明确可评价事实时才进入 M1。

`related_party_transaction` 若 runtime 需要支持，仍必须 additive/versioned sidecar；但 Metric-v2 不为其新增人工 Gold。Existing Gold support=0 时仅报告 `NOT_EVALUABLE_FROM_EXISTING_GOLD`。

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

公共 competition sidecar 没有为了比赛 metric 强行替换成新 `SupervisorDecision` schema。现有 FinalSupervisionResult / internal bundle 继续作为 runtime truth；Metric-v2 只消费其已记录 output/trace。

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

已有 foundation 定义 1D/5D/20D/60D horizon。项目预先定义：

```text
significant_drop_5d = (return_5d <= -0.10)
```

这属于 evaluation definition，不改变原始 `return_5d` 数据。赛题没有给绝对 5D pass threshold。

## 7. Metric-v2 Existing-Gold evaluation artifact boundary

Machine-readable protocol：

```text
configs/v045_competition_metric_protocol.json
protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
```

这些字段属于 final evaluation handoff，不是公共 runtime Pydantic schema。

### Existing-Gold evaluable manifest

Role B/A 必须先生成只读：

```text
existing_gold_evaluable_manifest.json
```

目标字段：

```text
metric_protocol_version
existing_gold_source
source_manifest_or_hash
case_id
split
risk_support
Evidence_support
UNJUDGED_counts
NOT_EVALUABLE_families
new_manual_annotations_added=false
existing_gold_modified=false
```

`UNJUDGED` 不等于 negative。

### Role B summary target shape

```text
metric_protocol_version
existing_gold_source
existing_gold_source_hash_or_manifest

risk_extraction.evaluable_positive_count
risk_extraction.correct_positive_count
risk_extraction.official_aligned_accuracy
risk_extraction.per_risk
risk_extraction.precision_status
risk_extraction.macro_f1_status

evidence_coverage.evaluable_existing_gold_count
evidence_coverage.covered_existing_gold_count
evidence_coverage.coverage_recall
retrieval_diagnostics.recall_at_1
retrieval_diagnostics.recall_at_3
retrieval_diagnostics.recall_at_5
retrieval_diagnostics.recall_at_10
retrieval_diagnostics.recall_at_20

new_manual_annotations_added=false
existing_gold_modified=false
blind_2025_outcome_accessed=false
```

`Precision` / `Macro F1` 只有 Existing Gold 本身提供足够 exhaustive positive/negative judgments 时才可以有数值；否则 status 必须 `NOT_AVAILABLE_FROM_EXISTING_GOLD`。

Legacy `risk_target_at_least_80_percent` / `evidence_target_at_least_85_percent` bool 若仍存在，只是 compatibility 字段，不能单独证明 Metric-v2 PASS。

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

沿用当前 E/A final explanation-quality artifact；本次 Existing-Gold-only M1/M2 政策不新增其人工 Gold 任务。

## 8. Identity rules

跨模块至少保持：

```text
case_id
stock_code
listing_date
run_id
```

Existing-Gold evaluator 另外必须保留 source annotation identity/hash，防止比赛收尾阶段悄悄替换标准答案。

LLM trace 进一步保留 provider_name / model_name / prompt_version / request_id / raw_response_hash / latency_ms。

任何 cross-lane join 优先稳定 identity/hash，不用公司名称 fuzzy join 作为正式绑定。
