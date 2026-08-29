# Data Schema — Runtime, Evaluation and Submission Contracts

> 状态日期：`2026-08-29`

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
- `HumanReview`（optional）。

Relevant trace event 必须有 actor/action/tool，并绑定 Evidence、Calculation 或 explicit `no_evidence_reason`。远程 LLM 额外记录 provider、model、Prompt、request identity、response hash 和 latency。

`HumanReview` sidecar 继续存在以支持人机协同 UI/export，但不存在 review 不影响当前 Release Gate。

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

### Retrieval / root-cause diagnostics

```text
case_id
risk_code
gold_unit_id
candidate_count
first_gold_rank
top1 / 3 / 5 / 10 / 20
agent_consumed
candidate_generation_miss
ranking_miss
first_failure_stage
proof_level
```

当前 active roots：

```text
deterministic_fact_missing
retrieval_candidate_miss
numeric_extraction_miss
genuine_conflict_fail_closed
LLM / Evidence variance
```

Gold 只在分析完成后的 evaluator-side join 使用。

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

### Market observation

```text
value OR missing_reason
unit
source
derivation
PIT cutoff
provenance
```

历史 frozen path 使用 governed Market-X artifacts；Dynamic New-IPO path 必须使用上市日前可知的受治理历史。

### Model signal

```text
score
score_semantics=uncalibrated_model_score
model / run identity
availability / missing reason
optional signed drivers
```

Dynamic inference 额外必须绑定：

```text
feature_manifest_hash
model_hash / frozen identity
input feature vector provenance
inference method
SHAP / pred_contrib method
```

不得用预生成 per-case signal 冒充新 case inference。

### Role-D canonical artifacts

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

Outcome horizons：1D / 5D / 20D / 60D。`significant_drop_5d = return_5d <= -0.10` 是项目冻结定义，不是命题方给定阈值。

## 6. Final Supervisor / Trace contract

Final Supervisor result 必须保留：

```text
prompt_version
provider / model
request_id
raw_response_hash
latency_ms
scope check
severity floor
accepted / fallback outcome
```

当前 v3 contract：禁止越界 Risk/Evidence/Conflict、未治理数字和预测词；severity 不得低于 deterministic floor。

M3 relevant TraceEvent 必须 accounted；当前 final-three 已验证 `1.0 × 3`。

## 7. Evidence screenshot contract

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

`bbox_source` 只允许：真实 upstream bbox、exact unique quote search、unavailable。多重匹配不得画假框。

当前 canonical final-three：`17/17` precise。

## 8. Demo replay contract

Canonical bundle：`reports/v045_demo_bundle`。

至少保留：

```text
demo_manifest.json
DEMO_SCRIPT.md
per-case analysis_result
Final Supervisor artifact
conflicts / rechecks
traceability
Evidence screenshot manifests / images
case reports
batch report
recorded code/config/PDF provenance
```

Replay immutable，不重新推理，不给旧运行补缺失结果。

## 9. Final submission artifacts

Required：

```text
metric dashboard
prediction table
Agent reasoning / Trace logs
Evidence / screenshot manifests
canonical case reports
Dynamic New-IPO proof
Blind / provenance / determinism / security audits
artifact index
release note
submission ZIP / SHA-256 manifest
```

Optional：

```text
human_review_export.json
explanation_quality diagnostics
```

**M4 review artifact 不再是 required package item。** 如果 Human Review export 存在但无人评审，必须保留 `unreviewed` 语义，不能解释为批准。

## 10. Identity rules

跨模块至少保持：

```text
case_id
stock_code
listing_date
run_id
code / config / Prompt / Schema identity
source / artifact hashes
```

正式 join 不使用公司名称 fuzzy match；UI smart-match 只用于输入便利，不替代 governed identity binding。
