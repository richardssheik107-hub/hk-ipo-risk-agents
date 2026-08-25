# 公共数据 Schema 与 Competition Runtime 契约

> Status snapshot: **2026-08-25**  
> Frozen baseline through PR-G: **COMPLETE**  
> Current Gate: **PR-H PARTIAL / BLOCKED**

代码中的 Pydantic Schema / validator 是最终权威实现；本文解释 frozen baseline 与 Competition Final Sprint 需要的跨模块 contracts。

## 1. General rules

1. 跨模块正式数据必须 versioned；
2. missing 必须有显式语义，不能自动变成 `0 / safe / negative`；
3. identity / provenance / source / policy / feature/model version 可追踪；
4. failure 必须结构化记录，不能 silent drop；
5. public schema change 必须有 contract tests；
6. frozen contract 不被 competition work 原地改写，新能力使用 versioned sidecar/runtime objects。

## 2. Core document objects

### DocumentChunk

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

### Evidence

至少保留：

```text
evidence_id
document_id
chunk_id
page
text
source
bbox optional
```

不得虚构页码、文本或来源。

### Calculation

```text
skill_name / skill_version
inputs / formula / result / unit
evidence_ids
success / error
```

### RiskItem

```text
risk_id / risk_code / category
level / score / conclusion
evidence / calculation
agent_name
verification_status
notes / metadata
```

正式状态：`verified / pending / rejected / needs_review`。

## 3. Competition AgentResult

Competition runtime 统一跨 Agent 输出：

```text
case_id
agent_name
task
status
claims / structured_facts
evidence_ids
calculation_ids
provider / model
prompt_version
uncertainties
metadata
```

LLM Agent 的 `evidence_ids` 必须属于 supplied Evidence scope。

## 4. MarketContext

Competition Market runtime 必须统一：

```text
case_id
listing_date
as_of
feature_values
availability / missing_reason
source_feature_ids
market_regime
risk_level
ipo_heat
liquidity_condition
key_drivers
uncertainties
source / provenance
policy_version
```

Frozen Market-X Core 仍为：

```text
v04_ipo_market_context_features_v1
15 raw + 15 missing indicators = 30 positions
438 / 438
```

Industry return 继续使用 explicit PIT-blocked missing semantics。

## 5. ModelSignal

Product model output 至少：

```text
case_id
status
model_id / run_id
score
score_semantics
calibration_status
signed_drivers / SHAP optional
uncertainty
model_version
source_hash / checksum optional
```

当前 frozen score semantics = `uncalibrated_model_score`。

若 frozen PR-F runtime/handoff 不可恢复：

```text
status = unavailable
score = null
```

不得 retrain/reconstruct 仅为产品填值。

## 6. Multi-horizon Outcome sidecar

Frozen PR-C 5D 不修改。Competition sidecar 新增：

```text
case_id
stock_code
listing_date
return_1d
return_5d
return_20d
return_60d
availability / missing_reason per horizon
session_policy
price provenance
policy_version
split
```

建议补：

```text
break_flag_1d
significant_drop_5d
max_drawdown_20d
max_drawdown_60d
```

## 7. Conflict

```text
conflict_id
case_id
agent_claim_ids
conflict_type
summary
severity
status
created_by
```

状态至少：

```text
open
rechecking
resolved
partially_resolved
unresolved
```

## 8. RecheckRequest

```text
recheck_id
conflict_id
target_agent
target_risk_or_fact
reason
required_evidence_topics
allowed_tools_or_skills
max_rounds
status
```

Competition runtime 默认 `max_rounds = 1`，避免无边界自主循环。

## 9. SupervisorDecision

```text
case_id
overall_risk
key_findings
conflict_ids
resolved_conflicts
unresolved_conflicts
uncertainties
recheck_requests
final_explanation
input_agent_result_ids
input_evidence_ids
input_model_signal_id
provider / model
prompt_version
```

Final Supervisor 不得创建新 Evidence 或行情事实。

## 10. TraceEvent

用于满足 Agent / Tool / Evidence traceability = 100%：

```text
trace_id
run_id
case_id
agent_name
task
step_index
input_evidence_ids
tool_or_skill
llm_provider / model
structured_output_ref
calculation_ids
verifier_status
conflict_id
recheck_id
final_status
latency_ms
created_at
```

## 11. HumanReview

机器结果与人工结果分离：

```text
review_id
case_id
target_type / target_id
original_status
reviewer_decision
reviewer_note
review_timestamp
reviewer_identity optional
post_review_status
```

允许：`accept / reject / needs_follow_up`。

## 12. Benchmark / evaluation artifacts

Submission 最少输出：

```text
risk_benchmark
  risk_code / TP / FP / FN / precision / recall / f1

evidence_benchmark
  risk_code / expected_evidence / retrieved_evidence / recall / precision / page_correctness

ai_vs_offline
  case_id / metric / offline / ai / delta
```

## 13. Prediction results table

`test_predictions.csv` 至少：

```text
case_id
stock_code
risk_score
risk_level
model_status
return_1d
return_5d
return_20d
return_60d
```

## 14. Frozen baseline contracts

以下不被 Final Sprint 原地覆盖：

```text
v04_document_features_v1
v04_ipo_market_context_features_v1
v04_5d_outcome_target_v1
v04_canonical_modeling_dataset_v1
Oracle v2 evaluation-only contracts
PR-F frozen model semantics
```

## 15. Time / Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

所有新 target/evaluation contracts 必须 fail closed on unauthorized 2025 y；2024 不变成新的 tuning set。
