# Data Schema — Current Contracts

本文件只描述当前代码中存在的 contract。Pydantic/Protocol 源码仍是最终权威；文档不得定义代码中不存在的公共字段。

## 1. Core document contracts

### Evidence

Evidence 是所有正式文档结论的来源锚点，核心语义包括：

- `evidence_id`
- `document_id`
- `chunk_id`
- `page`
- `section`
- `text`
- `source_type`
- `relevance_score`
- optional `bbox`

约束：

- Evidence 必须来自本次真实文档/受治理 source；
- page identity 不在 UI 修补；
- bbox 缺失就保持缺失；
- LLM 只能引用输入 Evidence ID 子集。

### Calculation

精确数值计算的 deterministic provenance object。Financial 风险需要数值推导时，应引用 Calculation，而不是把 LLM 文本当计算依据。

### RiskItem

正式风险结论。其风险码必须属于注册表/对应 owner 的 versioned extension；RiskItem 与 Evidence/Calculation 的关系由 Verifier 和治理测试约束。

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

跨 lane 的最小 Agent handoff：

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

它只引用业务对象 ID，不重新定义 RiskItem/Evidence 内容。

### CompetitionConflict

```text
conflict_id
case_id
run_id
involved_agents[]   # 至少两个不同 agent
risk_ids[]
claim_ids[]
summary
evidence_ids[]
status
resolution_note
created_at
```

`status` 枚举：

```text
detected
rechecking
resolved
partially_resolved
unresolved
```

不存在旧文档曾描述的 `left_agent/right_agent` 公共 contract；当前实现以 `involved_agents[]` 为准。

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

`max_attempts` 当前 schema 强制：

```text
1 <= max_attempts <= 1
```

即每个 conflict 只能有一次 controlled re-check。

`status`：

```text
pending
running
completed
failed
```

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

`event_type` 当前枚举：

```text
parser
retriever
agent
skill
llm
verifier
market
model
conflict
recheck
supervisor
human_review
```

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

`decision`：

```text
accept
reject
needs_follow_up
```

HumanReview 是 sidecar，不修改机器生成的 RiskItem / Evidence / analysis result。

### CompetitionRuntimeSidecar

```text
identity
agent_results[]
conflicts[]
rechecks[]
trace_events[]
human_reviews[]
```

## 3. Final Supervisor schema boundary

当前 competition sidecar **没有一个名为 `SupervisorDecision` 的公共 Pydantic model**。

现有 E 路径在既有 `FinalSupervisionResult`/typed internal bundle 上做 LLM synthesis，并将 versioned structured synthesis 投影到既有 metadata surface；公共 frozen contract 没有为了 competition sprint 被强行替换。

因此下游不要自行假设 `SupervisorDecision` 字段。如果未来要公开新 contract，必须由 A 做 additive/versioned schema review 后再更新本文档。

## 4. Market schema boundary

Market 运行时消费 governed `MarketContext`/structured observations，不允许把 legacy mock numbers 冒充 PR-B lineage。

核心语义：

- available observation 必须有真实 value/provenance；
- unavailable observation 必须有明确 missing reason；
- Market LLM interpretation 是定性结构化解释，不拥有数值事实；
- namespaced market references 可以进入 Trace，但不能伪装成 prospectus Evidence。

## 5. Model signal boundary

Model signal 必须保留：

```text
score
score_semantics = uncalibrated_model_score
calibration_status
model / run identity
optional signed drivers
availability / missing reason
```

公共 model view 故意不把 uncalibrated score 叫 probability。

如 authentic frozen PR-F handoff 不存在，消费者必须使用 unavailable 状态，而不是生成替代 score。

## 6. Outcome boundary

已有 market/outcome foundation 定义 1D/5D/20D/60D horizon 与 chronological split/blind rules。

比赛 final package 需要把这些 schema 物化成可复现结果 artifact；这属于 D 当前未关闭的交付，不应通过文档宣称已完成。

## 7. Identity rules

跨模块至少保持：

```text
case_id
stock_code
listing_date
run_id
```

LLM 相关 trace 进一步保留：

```text
provider_name
model_name
prompt_version
request_id
raw_response_hash
latency_ms
```

任何 cross-lane join 必须优先使用稳定 identity/hash，不用公司名称 fuzzy join 作为正式身份绑定。

## 8. Change policy

- frozen core schema 不原地破坏；
- competition 新字段优先 additive/versioned sidecar；
- rename/delete/type-breaking 必须有 A review 和迁移说明；
- UI 不得定义后端事实 schema；
- 文档发现与源码不一致时，以源码为准并修本文档。
