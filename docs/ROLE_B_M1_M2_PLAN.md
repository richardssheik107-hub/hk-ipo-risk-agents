# Role-B M1/M2 Plan — 从 Batch009 accepted checkpoint 到 ALL79 Development

> 状态日期：`2026-08-29`
>
> 最新可比 fixed-journal gated：M1 `14/30 = 46.67%`，M2 `21/48 = 43.75%`
>
> 最新真实 fresh gated（Batch005，尚未在 Batch008/009 后重跑）：M1 `11/30 = 36.67%`，M2 `17/48 = 35.42%`
>
> 正式 Gate：ALL79 Development M1 `>=0.80`、M2 `>=0.85`

fixed10 / fixed-journal 只用于诊断，不是正式比赛成绩。

## 1. 当前 Source-of-truth checkpoint

### Batch008 — accepted deterministic cash fix

通用修复 legacy 港股财务报表中的：

- 中文年份/日期；
- 显式 Notes 列；
- 繁简体经营现金流行；
- 仅在 `period_count + 1` 且有 Notes header 时移除 Notes reference。

可比 fixed-journal：

```text
offline M1 8/30 -> 9/30
offline M2 13/48 -> 15/48
gated   M1 12/30 -> 13/30
gated   M2 18/48 -> 20/48
```

只影响 cash runway；其他风险族 benchmark-unit 级稳定。

### Batch009 — partial accept

接受：通用 Legal redemption/restoration lifecycle recognition，并保留 Builder 已声明的不确定性。

拒绝：direct ranked concentration-table extraction。该候选虽然能读真实表格，但 canonical fixed-journal 没提升 M1/M2，并把 supplier existence F1 从 `0.875` 降到 `0.80`，因此完整回滚；生产代码中不得恢复该候选。

最新可比 fixed-journal：

```text
offline M1 = 9/30
offline M2 = 15/48
gated   M1 = 14/30
gated   M2 = 21/48
```

Batch009 让 redemption-rights M1 从 `4/8 -> 5/8`，并恢复 1 个 Evidence unit。

### Fresh checkpoint

Batch008/009 均为 immutable local journal、zero-network 测量，没有执行新的 real-provider fresh checkpoint。因此当前最后一个真实 fresh gated 仍保留 Batch005 的事实：

```text
M1 = 11/30 = 36.67%
M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
```

不能把 fixed-journal gated `14/30, 21/48` 写成 fresh-provider 结果。

## 2. 已排除 / 已关闭的方向

### Batch006 — period candidate generation

22 个 Financial positive units 审计：

```text
correct = 8
parser_text_missing = 6
deterministic_fact_missing = 6
numeric_extraction_miss = 1
conflict_fail_closed = 1
period_candidate_missing = 0
proven selector bugs = 0
```

结论：不做 broad period selector rewrite。

### Batch007 — Parser preservation

对 6 个可疑单元 / 11 governed pages 审计：

```text
non-empty extractable text = 11/11 pages
proven Parser preservation failure = 0
reclassified deterministic_fact_missing = 3
reclassified retrieval_candidate_miss = 3
```

结论：不做 broad Parser rewrite。

### Batch008 — legacy cash deterministic sub-root

该子根因已接受并关闭。不要再次大范围重写 cash parser，除非新证据证明不同 failure mode。

### Batch009 — ranked concentration-table candidate

已测量并拒绝。不得因为“表格可读”就重新启用；后续若再研究，必须先证明表格是 governed risk fact，并有更强 candidate-context gating。

### 历史 GLM-5.3 harness

PR #187 已归档历史负结果：`30` semantic calls 中 structured contract valid `2/30`，M1/M2 均 FAIL。它只描述当时 provider/model/config/runtime 组合，不代表模型永久不可用；但旧失败 harness 不应作为当前优化主路线。

## 3. 当前剩余 funnel / 修复优先级

Batch009 后，优先级调整为：

```text
1. retrieval candidate generation / ranking
2. exact page / anchor Evidence binding
3. remaining deterministic / numeric extraction gaps
4. genuine conflict fail-closed
5. fixed-vs-fresh LLM / Evidence variance
```

已知具体证据：

- `forensic_011` 中 retrieval candidate generation 仍是最大 proven first-failure layer：6 个 M1、16 个 M2 units；
- 一个 redemption Evidence page 位于 rank 18，超出 Legal Agent bounded 10-item consumption window；应优化 transaction/lifecycle co-occurrence ranking，而不是粗暴扩大消费上限；
- Legal status recovery 后仍存在 exact page/anchor Evidence-binding miss，M2 需要独立解决；
- numeric extraction 与 fresh-provider Evidence variance 仍开放。

## 4. 下一轮工作包

### B10 — Retrieval candidate / ranking

只有 unit-level audit 明确证明 supporting content 未进入候选或排名过低时才修改。

优先检查：

```text
risk-specific query / alias
transaction + lifecycle co-occurrence
candidate diversity
rerank features
candidate top20
Agent bounded consumption
```

禁止无证据地全局扩大 K。

### B11 — Exact Evidence binding

对“Risk 已恢复但 M2 仍缺失”的单元单独处理：

```text
correct candidate
-> correct Evidence ID
-> exact page
-> exact anchor / quote
-> verifier retain
-> final M2 covered
```

不得为了 Evidence recall 放松 scope 或制造 bbox。

### B12 — Remaining deterministic / numeric / conflict

仅处理新审计证明的 deterministic or numeric root。没有唯一可验证事实时保持 pending / needs_review。

### B13 — Fresh-provider stability

在 deterministic / retrieval roots 收敛后再执行真实 fresh checkpoint：

- structured output stability；
- abstention；
- Evidence ID consumption；
- provider sampling variance。

禁止 retry-to-improve benchmark。

## 5. 每个 batch 的验收模板

必须报告：

```text
hypothesis
proven affected units
before
patch scope
targeted tests
after
fixed-journal M1 delta
fixed-journal M2 delta
per-risk regression
fresh-provider status
network call count
Gold modified = false
Validation opened = false
Blind accessed = false
accepted / reverted
```

若无可证明净增益或出现重要回归，立即 revert / pivot。

## 6. 扩大 Development

不要长期停留在 fixed10。

推荐：

```text
fixed10 diagnostic
-> targeted larger Development slice
-> stratified Development slice
-> ALL79 Development
```

正式 Gate：

```text
case_count = 79
M1 >= 0.80 (target >= 0.85)
M2 >= 0.85 (target >= 0.88)
real_llm_cases = 79
new_manual_annotations_added = false
existing_gold_modified = false
Validation = false
Blind input/outcome not used for optimization
```

## 7. Evidence / retrieval diagnostics

继续保留：

```text
Candidate Retrieval Recall@20
Reranked Recall@10
Recall@1 / @3 / @5 / @10 / @20
Agent consumed
Final Existing-Gold Evidence Coverage Recall
```

waterfall：

```text
Gold Evidence
-> Parser preserved
-> candidate top20
-> reranked
-> Agent consumed
-> candidate risk created
-> final-positive retained
-> Evidence retained
-> page / anchor matched
-> M2 covered
```

## 8. 不可越过的边界

- Existing Gold immutable；
- Gold 不进入 runtime；
- `UNJUDGED != negative`；
- Validation freeze 后 one-shot；
- Blind 不用于优化；
- 不按 issuer / stock / case / page / Gold phrase 硬编码；
- 不把 fallback 冒充 real LLM；
- 不为了提分修改 evaluator/分母；
- 不提交 PDF、Secret、raw journal、绝对路径。

## 9. 当前停止点与下一步

```text
BEST_ACCEPTED_DIAGNOSTIC = Batch009
fixed-journal gated M1 = 14/30
fixed-journal gated M2 = 21/48
fresh checkpoint after Batch009 = NOT_RUN
ALL79 = OPEN
```

下一轮从 retrieval/ranking + exact Evidence binding 开始，而不是重启 Parser、period selector、ranked-table 或旧 GLM harness。
