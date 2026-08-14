# v0.3 Real LLM Baseline Evaluation

## 1. Executive Summary

本报告记录 `real_llm_baseline_v1`：在冻结 Retriever、Prompt、Risk Policy、Verifier、
Supervisor 与 Golden 的条件下，对相同 14 个正式真实案例运行 offline 与 Coding Plan
Responses API 两个 Arm。

Coding Plan 通过新增的 `openai_responses` 适配器完成了 Responses function calling、JSON
decode 和 Pydantic validation。完整 batch 中 52 次逻辑调用有 43 次成功、9 次失败。

真实 LLM 没有提高 Risk Recall：两臂均为 7.69%。Precision 从 50% 提高到 100%，
Verified Precision 从 50% 提高到 100%，F1 从 13.33% 小幅提高到 14.29%。提升来自
消除一个 Business false positive，而不是增加 true positive。Legal 产生一条新的 pending
候选，但没有成为 verified true positive。

结论：LLM semantic extraction 当前没有带来 Risk Recall 增量。主要瓶颈是 mixed：整体
Evidence Recall@3 仅 18.75%，显示 Retriever 是主要覆盖瓶颈；同时 Legal 的结构化输出
存在 Pydantic validation、missing function call 和 timeout，且候选仍未通过最终核验，说明
LLM extraction/runtime 也是显著次级瓶颈。

## 2. Experimental Design

- 代码基线：`main@ea99e2e034c9d730b632caddc266c3ee619efb45`
- Phase：`v0.3-post-release-real-llm-baseline`
- Arm A：`configs/v03_offline.yaml`，实验 runner 强制 `llm_provider=unavailable`
- Arm B：`configs/v03_ai_responses.yaml`，实验 runner 强制
  `llm_provider=openai_responses`
- 两臂共同使用 PyMuPDF Parser、Keyword Retriever、相同 Query Families、三类 Agent、
  Specialized Verifier、V03 Supervisor、RuleBasedPredictor、正式 Golden 与 evaluator。
- 处理顺序：synthetic smoke → 2410.HK gate → 14-case batch。

## 3. Frozen Components

```text
PUBLIC_SCHEMA_CHANGED = false
PUBLIC_PROTOCOL_CHANGED = false
RETRIEVER_CHANGED = false
RISK_POLICY_CHANGED = false
VERIFIER_CHANGED = false
SUPERVISOR_CHANGED = false
BUSINESS_PROMPT_TUNING = false
GOLDEN_CHANGED = false
```

## 4. Provider Architecture

保留两条独立实现：

```text
openai_compatible -> Chat Completions + json_object
openai_responses  -> Responses API + forced function call
```

Agent 继续调用冻结协议：

```python
generate_structured(
    *, task_name, prompt_version, evidence, response_model
) -> BaseModel
```

Responses 路径为：

```text
Evidence
-> client.responses.create
-> submit_structured_result function call
-> arguments JSON decode
-> response_model.model_validate
-> BaseModel
```

没有 function call 时 fail-closed；不接受自由文本作为结构化成功。

## 5. Smoke and Single-Case Gate

Responses synthetic smoke：

```text
REAL_LLM_SMOKE = PASS
responses_api = PASS
function_call_received = PASS
json_decode = PASS
pydantic_validation = PASS
latency_ms = 6,087
token_usage = 291 input / 101 output / 392 total
```

2410.HK gate：

- workflow：completed
- Agent/Verifier/Supervisor：completed
- report sections：10
- Responses calls：4 success / 0 failed / 0 retry
- tokens：39,815
- mean logical-call latency：33,670 ms
- offline 与 AI 风险结果相同。

## 6. Dataset and Blind Protection

- 正式真实案例：14
- 正式真实 Golden rows：34
- Financial：23 rows
- Legal：8 rows
- Business：3 rows
- 13 个 2020–2023 development cases
- 2410.HK development exception

```text
2025_BLIND_ACCESSED = false
2025_BLIND_USED_FOR_TUNING = false
```

选择器拒绝 `source_year=2025` 与 `dataset_split=blind_test`，两臂均未传入 blind token。

## 7. Cross-domain Results

| Metric | Offline | Real LLM | Delta |
|---|---:|---:|---:|
| Precision | 50.00% | 100.00% | +50.00 pp |
| Recall | 7.69% | 7.69% | 0.00 pp |
| F1 | 13.33% | 14.29% | +0.95 pp |
| Verified Precision | 50.00% | 100.00% | +50.00 pp |
| Evidence Recall@1 | 12.50% | 6.25% | -6.25 pp |
| Evidence Recall@3 | 18.75% | 18.75% | 0.00 pp |
| Evidence Recall@5 | 18.75% | 18.75% | 0.00 pp |

Expected verified = 13；两臂 true positive 都只有 1。AI 的 predicted verified 从 2 降为
1，因此 Precision 提升并非召回新风险。

## 8. Financial

| Metric | Offline | Real LLM |
|---|---:|---:|
| Precision | 100.00% | 100.00% |
| Recall | 10.00% | 10.00% |
| F1 | 18.18% | 18.18% |
| Evidence Recall@3 | 18.18% | 18.18% |

Financial Agent 不调用 LLM，因此完全相同符合实验设计。

## 9. Legal

| Metric | Offline | Real LLM |
|---|---:|---:|
| Risk Recall | 0.00% | 0.00% |
| Evidence Recall@1 | 0.00% | 0.00% |
| Evidence Recall@3 | 0.00% | 33.33% |
| Evidence Recall@5 | 0.00% | 33.33% |

2517.HK 的 `redemption_rights` 从 `not_produced` 变为 `pending`，Evidence pages 包含
80/81/82/152，但没有进入 verified，因此没有 Recall 增益。

Legal 是运行稳定性最弱的域：14 个案例中 9 个 Legal analyze log 为 failed。失败调用：

- Pydantic validation：4
- Timeout：3（2 litigation、1 shareholder rights）
- Structured function call missing：2

失败均被工作流转为 partial/结构化降级，没有未捕获异常。

## 10. Business

| Metric | Offline | Real LLM |
|---|---:|---:|
| Risk Recall | 0.00% | 0.00% |
| Evidence Recall@3 | 50.00% | 0.00% |

1167.HK 的 `precommercial_product` 从 offline `verified` 变为 AI `not_produced`；该 Golden
期望为 `needs_review`，所以 offline verified 是 false positive。AI 消除它提高了整体
Precision，但同时未产生符合 Golden 状态的候选。这不是正向 Recall 改善。

## 11. Risk Transitions

按正式 Golden row 统计：

```text
not_produced -> not_produced : 29
verified -> verified         : 2
verified -> not_produced     : 2
not_produced -> pending      : 1
```

1167.HK 在 manifest 中有两个 Business evidence rows，因此 transition 按 row 计为两次。

## 12. Failure Taxonomy and Bottleneck

当前 classification：

```text
PRIMARY_BOTTLENECK = mixed
RETRIEVER = primary coverage bottleneck
LLM_EXTRACTION_RUNTIME = material secondary bottleneck
VERIFIER = downstream bottleneck for the new Legal pending candidate
SKILL = no new failure signal
```

证据：

1. 16 条 applicable Golden 中 Evidence Recall@3 只有 3/16；多数风险在 Agent 前已缺少
   gold-page Evidence。
2. LLM 没有增加 true positive，Risk Recall delta 为 0。
3. 9/52 LLM calls 失败，集中在 Legal。
4. Legal 新候选只到 pending，没有成为 verified。
5. Business AI reconciliation 消除了 false positive，但也丢失原候选。

## 13. LLM Runtime Statistics

```text
number_of_calls = 52
successful_calls = 43
failed_calls = 9
retry_count = 6
mean_latency_ms = 38,185
median_latency_ms = 24,056
p95_latency_ms = 109,610
prompt_tokens = 251,048
completion_tokens = 107,196
total_tokens = 358,244
TOKEN_USAGE = AVAILABLE
COST_ESTIMATE = NOT_AVAILABLE
reason = provider pricing not declared
```

## 14. Answers to the Baseline Questions

1. Risk Recall 是否显著提高：否，delta = 0。
2. Precision/Verified Precision：均从 50% 提高到 100%，但来自减少一个 false positive。
3. 收益最大域：没有域获得 Risk Recall；Legal 获得一条 pending candidate 和 Evidence
   Recall@3 增量，但仍未 verified。
4. Offline miss → real LLM hit：没有 verified hit；2517.HK 是 miss → pending。
5. Gold Evidence 进入但仍未识别：主要见 Legal/Business failure artifacts，具体逐行记录在
   `failure_analysis.csv` 与 `legal_failure_analysis.csv`。
6. Candidate 被 Verifier 拒绝/待审：2517.HK 进入 pending/needs-review 路径。
7. 主要瓶颈：mixed，以 Retriever coverage 为主，LLM extraction/runtime 与 downstream
   verification 为次。

## 15. Artifacts

本地忽略目录：`reports/v03_real_llm_responses_baseline/`

- `offline/analysis_results.jsonl`
- `real_llm/analysis_results.jsonl`
- `comparison/case_comparison.csv`
- `comparison/risk_comparison.csv`
- `comparison/risk_transition.csv`
- `comparison/agent_comparison.csv`
- `comparison/llm_calls.csv`
- `comparison/evaluation_comparison.json`
- `comparison/failure_analysis.csv`
- `comparison/legal_failure_analysis.csv`

## 16. Security

```text
API_KEY_IN_DIFF = false
AUTH_HEADER_IN_DIFF = false
RAW_EXTERNAL_RESPONSE_SAVED = false
LOCAL_SECRET_FILE_COMMITTED = false
2025_BLIND_ACCESSED = false
```

## 17. Recommendation

不要直接调 Prompt、Retriever 或 Verifier。下一阶段建议拆成两个独立冻结实验：

1. Retriever coverage experiment：只验证为何 13/16 applicable rows 在 Top-3 缺失；
2. Legal Responses reliability audit：只分析 4 个 Pydantic failure、3 个 timeout、2 个
   missing function call 以及 2517.HK pending 的 downstream decision。

每个实验都应使用新 Plan 和独立验证集；不得根据本轮 Golden 结果直接调参。本报告生成后
停止，不开始 v0.4。
