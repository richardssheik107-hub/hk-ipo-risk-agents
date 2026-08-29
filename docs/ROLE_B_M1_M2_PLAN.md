# Role-B M1/M2 Plan — 从 proven root cause 到 ALL79 Development

> 状态日期：`2026-08-29`
>
> 当前 fixed-journal：M1 `12/30 = 40.00%`，M2 `18/48 = 37.50%`
>
> 当前 fresh gated：M1 `11/30 = 36.67%`，M2 `17/48 = 35.42%`
>
> 当前主根因：`deterministic_fact_missing`

fixed-10 是快速诊断集，不是正式比赛成绩集。

## 1. 当前 Source-of-truth checkpoint

### Fixed-journal Batch005

```text
M1 = 12/30 = 40.00%
M2 = 18/48 = 37.50%
Cash M1 = 1/5
Customer M1 = 4/8
Supplier M1 = 3/9
Redemption M1 = 4/8
```

### Fresh gated Batch005

```text
M1 = 11/30 = 36.67%
M2 = 17/48 = 35.42%
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
monotonicity = PASS
```

Batch005 已关闭一个精确事实根因：PDF spaced decimal（如 `32 .7%`）、局部 period binding 与 verifier normalization。

## 2. 已排除的错误方向

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

结论：`period_candidate_generation` 不是当前 active root，不做 broad selector rewrite。

### Batch007 — Parser preservation

对原先 6 个可疑单元 / 11 governed pages 审计：

```text
non-empty extractable text = 11/11 pages
proven Parser preservation failure = 0
reclassified deterministic_fact_missing = 3
reclassified retrieval_candidate_miss = 3
```

结论：不做 broad Parser rewrite，除非有新的 proven evidence。

## 3. 当前修复优先级

```text
1. deterministic_fact_missing
2. isolated retrieval_candidate_miss
3. numeric_extraction_miss
4. genuine conflict fail-closed
5. LLM / Evidence variance
```

每个 batch 只针对 proven root 做最小通用修复，并保留回滚条件。

## 4. 当前工具链

- Existing-Gold audit / evaluator；
- v0.4.6 structured smoke；
- offline / shadow / gated same-run harness；
- immutable local LLM journal；
- Financial high-recall adapter；
- retrieval / risk waterfall；
- monotonicity report；
- persisted-result read-only Evidence auditor；
- period-candidate / parser-preservation bounded audits；
- fixed-journal zero-network replay。

## 5. 修复工作包

### B8 — Deterministic fact formation

目标：对已确认 parser 有文本、retrieval 有候选，但 deterministic structured fact 没形成的单元逐一定位：

```text
raw text
→ numeric / clause extraction
→ period / entity binding
→ typed fact
→ risk candidate
```

允许：

- 通用 alias / label normalization；
- deterministic numeric parsing；
- table/line local binding；
- exact-fact conversion；
- missingness-preserving reconciliation。

禁止：

- company/case/page 特判；
- Gold 原句硬编码；
- 用不确定数值补成 verified。

### B9 — Retrieval candidate miss

仅处理 Batch007 已隔离或后续 audit 新证明的 candidate miss。

检查：

```text
query / alias
→ candidate top20
→ rerank
→ Agent consumed
```

不要因少量 retrieval miss 对全 Retriever 做无证据大改。

### B10 — Numeric / genuine conflict

对 numeric extraction miss 或同 period 真冲突做 fail-closed 修复；没有唯一可验证事实时保持 pending / needs_review。

### B11 — LLM / Evidence stability

只在 deterministic roots 收敛后处理：

- structured validity；
- bounded retry / correction；
- Evidence selection stability；
- provider sampling variance。

不允许 retry-to-improve benchmark。

## 6. 修复验收模板

每个 batch 必须报告：

```text
hypothesis
proven affected units
before
patch scope
tests
after
M1 delta
M2 delta
per-risk regression
network call count
Gold modified = false
Validation opened = false
Blind accessed = false
accepted / reverted
```

若一个方向没有可证明净增益，立即 pivot，不扩大 patch。

## 7. 扩大 Development

不要等 fixed10 变得“完美”才扩大。

当连续修复包稳定后，开始 larger Development checkpoint，最终运行：

```text
ALL79 Development
```

正式 Gate：

```text
case_count = 79
M1 >=0.80（target >=0.85）
M2 >=0.85（target >=0.88）
real_llm_cases = 79
new_manual_annotations_added = false
existing_gold_modified = false
Validation = false
Blind input/outcome not used for optimization
```

## 8. Evidence / retrieval diagnostics

继续保留：

```text
Candidate Retrieval Recall@20
Reranked Recall@10
Recall@1 / @3 / @5 / @10 / @20
Final Existing-Gold Evidence Coverage Recall
```

诊断 waterfall：

```text
Gold Evidence
→ Parser preserved
→ candidate top20
→ Agent consumed
→ candidate risk created
→ final-positive retained
→ Evidence retained
→ page / anchor matched
→ M2 covered
```

## 9. 推荐运行入口

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py \
  --run-id <RUN_ID> \
  --modes all \
  --execute
```

若真实凭证或授权 PDF 缺失，保持 `EXECUTION_BLOCKED`；不得切换 mock 冒充真实测量。

## 10. 不可越过的边界

- 不修改 Gold / evaluator / fixed10 identity；
- 不把 Gold 输入 runtime；
- 不用 Validation 调参；
- 不使用 Blind input/outcome 优化；
- 不接受越界 Evidence；
- 不按公司、股票、case、页码硬编码；
- 不用 fallback 冒充 real LLM；
- 不为提分删除失败案例；
- 不提交 PDF、Secret、raw journal、绝对路径。

## 11. 停止条件

停止并保留最佳 commit，当：

- 连续两个 proven-root 修复包无净增益；
- fixed10 提升但 larger Development 回归；
- 需要修改 Gold/evaluator；
- 需要查看 Validation/Blind 才能选择参数；
- transport 无法稳定；
- 诊断证据不足以证明下一修复点。
