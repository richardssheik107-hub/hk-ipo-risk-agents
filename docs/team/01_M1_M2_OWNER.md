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

内部目标：M1 `>=0.85`、M2 `>=0.88`。fixed10 / fixed-journal 只用于诊断，不能替代 ALL79 正式结果。

## 2. 当前起点 — Batch009

最新**可比 fixed-journal gated** checkpoint：

```text
Batch005  M1 12/30   M2 18/48
Batch008  M1 13/30   M2 20/48
Batch009  M1 14/30   M2 21/48
```

当前 Batch009：

```text
fixed-journal gated M1 = 14/30 = 46.67%
fixed-journal gated M2 = 21/48 = 43.75%
offline M1 = 9/30
offline M2 = 15/48
```

Batch008/009 没有新的 remote provider 调用，所以最后一个真实 fresh checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30 = 36.67%
fresh gated M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
```

**不要把 `14/30, 21/48` 写成 fresh-provider 结果。**

## 3. 已接受 / 已拒绝的最新工作

### Batch008 — ACCEPTED

接受 legacy Chinese cash-statement / explicit Notes-column deterministic exact-fact 修复：中文年份/日期、显式 Notes header、繁简体经营现金流 wording，并保持列数不匹配 fail-closed。

效果：gated `M1 +1`、`M2 +2`，只影响 cash runway。

### Batch009 — PARTIAL_ACCEPT

接受 generalized Legal redemption/restoration lifecycle recognition，并保留 Builder-declared uncertainty，不把不确定状态硬转成 positive。

效果：redemption-rights M1 `4/8 -> 5/8`，额外恢复 1 个 Evidence unit；总 gated 到 `14/30, 21/48`。

拒绝 direct ranked concentration-table extraction：canonical fixed-journal M1/M2 无提升，supplier existence F1 `0.875 -> 0.80`，候选已完整回滚。**禁止直接恢复。**

### 历史 GLM-5.3 失败实验

PR #187 已归档：

```text
semantic_calls = 30
structured_contract_valid = 2/30
M1 = FAIL
M2 = FAIL
offline outperformance = NOT_PROVEN
```

只代表当时 provider/model/config/runtime 组合失败；不代表模型永久不可用，但旧 harness 不应作为当前主路线。

## 4. 当前 root-cause 优先级

Batch006/007 已排除 broad period selector 和 broad Parser preservation；Batch008 已关闭一个 legacy cash deterministic sub-root。

Batch009 后：

```text
1. retrieval candidate generation / ranking
2. exact page / anchor Evidence binding
3. remaining deterministic / numeric extraction
4. genuine conflict fail-closed
5. fixed-vs-fresh LLM / Evidence variance
```

已知证据：

- `forensic_011` retrieval candidate generation 是最大 proven first-failure layer：6 M1 / 16 M2 units；
- 一个 redemption Evidence page 位于 rank 18，超出 Legal Agent bounded 10-item consumption；优先改 transaction/lifecycle co-occurrence ranking，不粗暴扩大上限；
- Legal risk recovery 后仍有 exact page/anchor binding miss，M2 必须独立处理；
- numeric extraction 和 fresh Evidence variance 仍开放。

## 5. 负责范围

可以修改：

- Document retrieval / rerank；
- Financial / Legal / Business 风险抽取；
- deterministic fact formation；
- table / numeric extraction；
- Evidence candidate formation / consumption / binding；
- Risk builder / reconciliation；
- specialized verifier；
- 与 M1/M2 直接相关的 Prompt / Schema；
- Role-B diagnostics / waterfall / root-cause tooling；
- Existing-Gold evaluator 的真实 bug fix（不得改变 metric 定义）。

不负责：前端视觉、Dynamic Market-X、Frozen Model/SHAP、最终 submission ZIP。

## 6. 不可破坏边界

```text
Existing Gold immutable
Gold never enters runtime
UNJUDGED != negative
Validation untouched during optimization
2025 Blind untouched
no company/stock/case/page/Gold hardcoding
no evaluator-specific runtime branching
no manual label patching
```

不得通过修改 Gold、分母、Validation 后调参、case-specific rule 来提分。

## 7. 下一轮执行

### Step A — Retrieval candidate / ranking

只针对 proven miss：

```text
risk-specific query/alias
transaction+lifecycle co-occurrence
candidate diversity
rerank
candidate top20
Agent bounded consumption
```

### Step B — Exact Evidence binding

对 Risk 已正确恢复但 M2 缺失的单元：

```text
candidate
-> Evidence ID
-> exact page
-> exact anchor/quote
-> verifier retain
-> M2 covered
```

不允许制造 page/bbox 或放松 Evidence scope。

### Step C — Remaining deterministic / numeric / conflict

只修新证据证明的通用 root；事实不唯一时继续 pending / needs_review。

### Step D — Fresh-provider checkpoint

在上面 roots 收敛后执行新的真实 fresh checkpoint，验证 fixed-journal gain 是否能跨 provider run 保持。

不得 retry-to-improve benchmark。

## 8. 每个 batch 的验收

```text
hypothesis
proven affected units
before
patch scope
targeted/full tests
after
fixed-journal M1/M2 delta
per-risk regression
fresh-provider status
network call count
Gold modified = false
Validation opened = false
Blind accessed = false
accepted / reverted
```

无净增益、fresh 明显反向、structured validity 下降或出现重要回归 => REJECT / REVERT。

## 9. 扩样顺序

```text
fixed10 diagnostic
-> targeted larger Development slice
-> stratified Development slice
-> ALL79 Development
```

正式输出至少包括：

```text
existing_gold_evaluable_manifest.json
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
retrieval diagnostics
root-cause ledger
runtime/config/prompt hashes
```

## 10. 与其他人的接口

- Frontend Owner：稳定 RiskItem / Evidence / Calculation / Verifier / conflict-recheck 字段；
- Market-X Owner：可靠 issuer/listing identity 与必要 Document metadata；
- Dynamic Model Owner：若模型需要 Document feature，提供 versioned schema-bound feature vector，不从 Gold 重建；
- Release Owner：最终冻结 SHA、Prompt/Schema/Config identity、ALL79 metrics、artifact manifest。

## 11. DONE

只有以下全部成立才算完成：

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

当前状态仍是 ACTIVE / P0；Batch009 是新的 accepted diagnostic checkpoint，不是正式 Gate PASS。
