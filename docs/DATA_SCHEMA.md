# Data Schema — Runtime, Evaluation and Submission Contracts

源码中的 Pydantic / Protocol 是 runtime 最终权威。本文件描述当前跨 lane artifact 形状，不允许用文档字段绕过代码校验。

## 1. Core runtime

### Evidence

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
metadata
```

约束：Evidence 来自本次真实 source；page/bbox 不在 UI 猜测；LLM 只引用 allowed ID。

### Calculation

```text
skill_name / version
inputs
formula
result
unit
evidence_ids
success / error
```

精确财务与 outcome 计算必须可重放。

### RiskItem

```text
risk_id / risk_code
category / level / score
conclusion
Evidence[]
optional Calculation
agent / confidence
verification status / notes
metadata
```

Formal risk 必须通过 owner、Evidence 与 Verifier contract。

## 2. Competition runtime sidecars

保留：

- `CompetitionRuntimeIdentity`；
- `AgentResultEnvelope`；
- `CompetitionConflict`；
- `RecheckRequest`；
- `TraceEvent`；
- `HumanReview`。

Relevant trace event 必须有 actor/action/tool，并绑定 Evidence、Calculation 或 explicit `no_evidence_reason`。远程 LLM 额外记录 provider、model、Prompt、request identity、response hash 和 latency。

## 3. Role-B v0.4.6 diagnostic artifacts

### Baseline manifest

```text
code_fingerprint
subset_hash
gold_manifest_hash
metric_protocol_version
provider / model / transport
prompt_hashes
schema_set_hash
runtime_config_hash
modes
validation_opened=false
blind_outcome_accessed=false
```

### LLM journal identity

```text
case_id
dataset_split
task_name
provider / model / transport
prompt_version / prompt_hash
response_schema_hash
ordered_allowed_evidence_ids
evidence_content_hash
runtime_config_hash
```

Journal 不持久化 API Key、Base URL、完整 Prompt、完整 raw response 或本机路径。

### Retrieval waterfall

```text
case_id
risk_code
gold_unit_id
candidate_count
first_gold_page_rank
first_gold_rank
top1 / 3 / 5 / 10 / 20
agent_consumed
candidate_generation_miss
ranking_miss
```

Gold 只在分析完成后的 evaluator-side join 使用。

### Risk pipeline waterfall

目标字段：

```text
deterministic_candidate_present
llm_request_attempted / success
llm_structured_valid / scope_valid
llm_candidate_present / abstained
extraction_status
builder_status
normalization_success
reconciliation_success
candidate_after_reconciliation
verifier_outcome
final bucket / Evidence IDs
first_failure_stage
proof_level
```

缺 trace 必须写 `NOT_AVAILABLE`，不得猜测。

### Root-cause matrix

每个 Risk/Evidence Unit 记录 earliest proven failure、secondary observations、proof artifact、`PROVEN|INFERRED|UNAVAILABLE`。

## 4. Existing-Gold evaluation

Runtime `Evidence` / `RiskItem` 与 Existing-Gold Unit 是不同对象。

M1 summary：

```text
evaluable_positive_count
correct_positive_count
official_aligned_accuracy
per_risk
status / level / calculation / evidence diagnostics
```

M2 summary：

```text
evaluable_existing_gold_count
covered_existing_gold_count
coverage_recall
Recall@1 / 3 / 5 / 10 / 20
```

Existing Gold immutable；`UNJUDGED` 不等于 negative。

## 5. Market / Model / Outcome

Market observation：value 或 missing reason、unit、source、derivation、PIT cutoff、provenance。

Model signal：

```text
score
score_semantics=uncalibrated_model_score
model / run identity
availability / missing reason
optional signed drivers
```

Role-D canonical directory 恰好四文件：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

Outcome horizons：1D / 5D / 20D / 60D。`significant_drop_5d = return_5d <= -0.10` 是项目冻结定义，不是命题方给定阈值。

## 6. Evidence screenshot contract

每条截图 manifest 至少记录：

```text
case_id / stock_code
risk_id / evidence_id
source_pdf_sha256
physical_page_1based
internal_page_index_0based
quote_sha256
bbox
bbox_source
match_count
screenshot_relative_path
screenshot_sha256
exact_highlight_available
unavailable_reason
exporter_version
```

`bbox_source` 只允许：upstream parser bbox、exact unique quote search、unavailable。多重匹配不得画假框。

## 7. Final submission artifacts

至少包括：

```text
metric dashboard
prediction table
Agent reasoning logs
Evidence / screenshot manifests
3 case reports
M4 review artifact
Blind / provenance / determinism / security audits
artifact index
release note
submission ZIP / SHA-256 manifest
```

所有路径使用相对路径；bundle 不含 Secret、PDF、raw EOD、raw journal、本机路径或未授权模型。

## 8. Identity rules

跨模块至少保持：

```text
case_id
stock_code
listing_date
run_id
code / config / Prompt / Schema identity
source / artifact hashes
```

正式 join 不使用公司名称 fuzzy match。
