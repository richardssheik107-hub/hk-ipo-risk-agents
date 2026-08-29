# Person 1 — M1 / M2 Document Intelligence Owner

> 状态日期：2026-08-29  
> 建议分支：`codex/role-b-m1-m2`  
> 主优先级：**P0**  
> 对应比赛核心：招股书风险抽取准确率、Evidence 覆盖率

## 1. 唯一主目标

这个岗位只对一件事负责：把正式 Development 文档智能指标推到比赛门槛以上，并留下可复现、可审计的证据。

```text
ALL79 Development
M1 Existing-Gold Risk Accuracy >= 0.80
M2 Existing-Gold Evidence Coverage Recall >= 0.85
real_llm_cases = 79/79
```

内部目标可以更高：

```text
M1 target >= 0.85
M2 target >= 0.88
```

fixed10 / fixed-journal 只用于诊断，不能替代 ALL79 正式结果。

## 2. 当前起点

当前正式诊断 checkpoint：

```text
fixed-journal M1 = 12/30 = 40.00%
fixed-journal M2 = 18/48 = 37.50%

fresh gated M1 = 11/30 = 36.67%
fresh gated M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
```

当前已经被证据缩小的 root-cause 顺序：

```text
deterministic_fact_missing
→ retrieval_candidate_miss
→ numeric_extraction_miss
→ genuine_conflict_fail_closed
→ LLM / Evidence variance
```

已排除为当前主要根因：

```text
broad Parser preservation
period candidate generation / selector
```

除非出现新的 proven evidence，不要重新对 Parser 或 period selector 做大规模重写。

### 历史 GLM-5.3 失败实验

仓库已归档一条历史负结果：

```text
source PR = #186
semantic_calls = 30
structured_contract_valid = 2/30
M1 = FAIL
M2 = FAIL
```

这只说明当时的 provider/model/config/runtime 组合没有满足结构化输出 contract，不代表模型永久不可用；但不要重复使用已经证明失败的旧 harness 当作当前主路线。

## 3. 负责范围

本岗位可以修改：

- Document retrieval；
- Financial / Legal / Business 风险抽取；
- deterministic fact formation；
- table / numeric extraction；
- Evidence candidate formation 与 consumption；
- Risk builder / reconciliation；
- specialized verifier；
- 与 M1/M2 直接相关的 Prompt / Schema；
- Role-B diagnostic、waterfall、root-cause tooling；
- Existing-Gold evaluator 的 bug fix（不得改变 metric 定义）；
- benchmark runner、batch runner、diagnostic artifacts。

本岗位**不负责**：

- Streamlit 前端视觉设计；
- Dynamic Market-X；
- Frozen Model / SHAP runtime；
- 最终提交 ZIP；
- 为了页面好看改变风险语义。

## 4. 不可破坏的治理边界

必须一直保持：

```text
Existing Gold immutable
Gold never enters runtime
UNJUDGED != negative
Validation untouched during optimization
2025 Blind untouched
no company/page hardcoding
no evaluator-specific runtime branching
no manual label patching
```

禁止通过：

- 给某家公司写 case-specific rule；
- 给某个 Gold page 加特殊匹配；
- 修改 Gold；
- 修改分母；
- 把 UNJUDGED 当 negative；
- 看 Validation 后再调参；

来提高 M1/M2。

## 5. 工作方法

每轮只接受 evidence-driven 小批次优化。

### Step A — 冻结当前基线

每个优化 batch 开始前记录：

```text
BASE_SHA
runtime config hash
Prompt versions
Retriever version
Verifier version
fixed-journal M1/M2
fresh-gated M1/M2
structured-valid count
fallback / transport / scope counts
```

### Step B — 建立 unit-level failure ledger

至少按以下类型分类每个失败 Risk/Evidence Unit：

```text
deterministic_fact_missing
retrieval_candidate_miss
ranking_miss
numeric_extraction_miss
reconciliation_fail
verifier_reject
true_conflict_fail_closed
llm_abstain
llm_response_variance
agent_consumption_miss
other_proven
```

每个结论必须有 proof artifact。无法证明就写 `UNAVAILABLE / INFERRED`，不要猜。

### Step C — 优先解决 deterministic fact formation

重点检查：

- 财务表格中的期间、单位、币种、同比关系；
- customer / supplier concentration 的百分比与 period binding；
- cash runway 的 deterministic input；
- redemption-rights 条款的 deterministic trigger；
- continuous loss / revenue growth 的 multi-period fact；
- spaced decimals、PDF 数字断裂、表头和 label-local binding；
- builder 为什么没有把正确 fact 形成 candidate Risk。

原则：如果 Evidence 已进入 candidate set，但 Risk 没形成，优先修 deterministic formation，而不是继续扩大 retrieval。

### Step D — 再解决 retrieval candidate miss

只有在 unit-level audit 明确证明 gold-supporting content 没进入 candidate set 时，才调整 retrieval。

优先：

```text
domain query formulation
structured-table candidate generation
risk-specific terms
candidate diversity
bounded top-K expansion
```

禁止无证据地无限扩大 K 或全局召回，因为会增加 Agent consumption 噪声和成本。

### Step E — Numeric / reconciliation / verifier

要求：

- 数字 normalization 不改变实际值；
- period 不跨列错误绑定；
- 冲突时 fail-closed；
- verifier 不能因为格式差异拒绝本来正确的 fact；
- 不能为了 recall 放松 Evidence scope。

### Step F — LLM variance 最后处理

先排除 deterministic/retrieval 问题，再处理：

```text
structured output stability
abstention
Evidence ID consumption
response variance
```

不得用大 Prompt 重写掩盖 deterministic bug。

## 6. 每个 batch 的验收条件

任何 batch 只有满足以下条件才能保留：

```text
fixed-journal M1/M2 不出现无解释回归
fresh run 至少保持同方向
structured validity 不下降
transport/scope failures 不增加
Existing Gold hash 不变
Validation/Blind 未访问
full relevant tests PASS
```

如果某优化只在 fixed-journal 提升、fresh 明显回归，要标记为 `REJECTED / UNSTABLE`。

## 7. 扩样顺序

不要长期停留在 fixed10。

推荐顺序：

```text
fixed10 diagnostic
→ targeted larger Development slice
→ stratified Development slice
→ ALL79 Development
```

进入 ALL79 前，先保证：

- 结构化输出稳定；
- runtime cost 可控；
- 没有 case-specific logic；
- root-cause ledger 已覆盖主要失败类型。

## 8. 正式 ALL79 输出

最终至少生成：

```text
existing_gold_evaluable_manifest.json
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
retrieval diagnostics
root-cause / failure ledger
runtime identity / hashes
```

最终 summary 必须明确：

```text
split = Development
evaluated_case_count = 79
real_llm_cases = 79
M1
M2
new_manual_annotations_added = false
existing_gold_modified = false
validation_accessed = false
blind_accessed = false
```

## 9. 对其他四人的接口

### 给 Frontend Owner

输出稳定的：

- RiskItem；
- Evidence；
- Calculation；
- Verifier status；
- conflict/recheck 所需字段。

不要让前端依赖内部 debug 字段。

### 给 Market-X Owner

提供可靠 issuer / listing identity 和必要 Document-derived metadata，但不要改 Market 计算。

### 给 Dynamic Model Owner

若 frozen model 需要 Document feature：提供 versioned、schema-bound Document feature vector；不要让 Model owner从 Gold 重建 feature。

### 给 Release Owner

提供最终冻结 SHA、Prompt/Schema/Config identity、ALL79 metrics 与 artifact manifest。

## 10. 完成定义

本岗位只有在下面全部真实成立时才算 DONE：

```text
ALL79 Development completed
M1 >= 0.80
M2 >= 0.85
real_llm_cases = 79/79
Existing Gold unchanged
Validation untouched
Blind untouched
no hardcoding
formal artifacts complete
relevant tests PASS
code/config/prompt identity frozen
```

在此之前，不要把精力分散到 UI、打包或动态模型上。