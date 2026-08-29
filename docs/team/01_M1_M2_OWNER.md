# Person 1 — M1 / M2 Document Intelligence Owner

> 状态日期：`2026-08-29`  
> 主优先级：**P0**  
> Execution mode：**AUTONOMOUS MULTI-ROOT WIDE SPRINT / GOAL MODE**

## 1. 唯一主目标

持续、自主地把正式 Development 文档智能指标推到赛题门槛，不等待每个小 batch 的 owner 继续指令。

```text
ALL79 Development
M1 Existing-Gold Risk Accuracy >=0.80
M2 Existing-Gold Evidence Coverage Recall >=0.85
real_llm_cases =79/79
```

冲刺目标：M1 `>=0.85`、M2 `>=0.88`。fixed10 / fixed-journal 只用于快速诊断，不能替代 ALL79 正式结果。

## 2. 当前正式起点 — Batch009

PR #189 已把 Batch008/009 accepted production fixes 与 bounded measurement artifacts 合入 main。

最新可比 fixed-journal gated：

```text
Batch005  M1 12/30   M2 18/48
Batch008  M1 13/30   M2 20/48
Batch009  M1 14/30   M2 21/48
```

当前 Batch009：

```text
fixed-journal gated M1 = 14/30 =46.67%
fixed-journal gated M2 = 21/48 =43.75%
offline M1 = 9/30
offline M2 = 15/48
```

Batch008/009 没有新的 remote provider 调用，所以最后一个真实 fresh checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30 =36.67%
fresh gated M2 = 17/48 =35.42%
structured valid = 38/40
fallback = 2
transport failures = 0
scope rejections = 0
```

**不要把 `14/30,21/48` 写成 fresh-provider 结果。**

## 3. 已接受 / 已拒绝

### Batch008 — ACCEPTED

legacy Chinese cash-statement / explicit Notes-column deterministic exact-fact compatibility：中文年份/日期、显式 Notes header、繁简体 operating-cash-flow wording，并保持列数不匹配 fail-closed。

效果：gated `M1 +1`、`M2 +2`，只影响 cash runway。

### Batch009 — PARTIAL_ACCEPT

接受 generalized Legal redemption/restoration lifecycle recognition，并保留 Builder-declared uncertainty，不把不确定状态硬转成 positive。

效果：redemption-rights M1 `4/8 → 5/8`，总 gated 到 `14/30,21/48`。

拒绝 direct ranked concentration-table extraction：canonical M1/M2 无提升，supplier existence F1 `0.875 → 0.80`，候选已完整回滚。**禁止直接恢复该实现。** 若未来重新打开 ranked-table root，必须有新的 failure evidence、不同的通用假设和独立 regression proof。

### 历史 GLM-5.3 失败实验

旧 harness 的 structured contract 曾失败，不作为当前主路线。历史负结果只说明当时 provider/model/config/runtime 组合失败，不代表模型永久不可用。

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

已知 evidence：

- `forensic_011` retrieval candidate generation 是最大 proven first-failure layer：6 M1 / 16 M2 units；
- 一个 redemption Evidence page 位于 rank 18，超出 Legal Agent bounded 10-item consumption；优先优化 transaction/lifecycle co-occurrence ranking，不粗暴无界扩大 K；
- Legal risk recovery 后仍存在 exact page/anchor binding 问题，M2 必须独立处理；
- remaining numeric extraction 和 fresh Evidence variance 仍开放。

## 5. 工作模式：多根因并行，不再一个 root 一轮

不要使用：

```text
one root → tiny patch → full benchmark → stop → wait owner
```

改为：

```text
OBSERVE ALL FAILURES
→ COMPLETE FUNNEL DIAGNOSIS
→ GROUP MULTIPLE PROVEN ROOTS
→ IMPLEMENT COMPATIBLE SUBFIXES
→ TARGETED TESTS / CONTROLS
→ FIXED-JOURNAL BUNDLE BENCHMARK
→ UNIT-LEVEL DIFF
→ PARTIAL REVERT ONLY BAD SUBFIX
→ PRESERVE BEST CHECKPOINT
→ SCALE DEVELOPMENT DIAGNOSTICS
→ FRESH CHECKPOINT WHEN JUSTIFIED
→ AUTO-CONTINUE
```

允许同一 sprint 同时处理 retrieval/ranking、exact binding、remaining numeric/deterministic、Legal variants、LLM stability 等经过 evidence 证明且互相兼容的问题。

每个 root 尽量独立 commit，便于 partial revert。一个子项失败不能拖掉同 bundle 已经证明有效的其他收益。

## 6. Retrieval / ranking P0

只针对 proven miss 做完整 funnel：

```text
PDF text
→ chunk
→ query
→ candidate generation
→ rank
→ top-K / dedup
→ Agent consumption
→ Evidence
→ fact
→ Risk
→ final Evidence binding
```

允许：risk-specific query/alias、transaction+lifecycle co-occurrence、bilingual variants、section priors、table-aware retrieval、multi-query/query fusion、hybrid weights、rerank、bounded Top-K、diversity/dedup/context assembly。

如果正确 Evidence 常落在 K+1/K+2/K+3，先解释 ranking 原因，再决定是否有限扩大 K；不能把无限加 K 当主策略。

## 7. Exact Evidence binding P0

正确 Risk 已形成但 M2 未覆盖的单位沿：

```text
candidate
→ Evidence ID
→ page
→ exact anchor/quote
→ structured fact
→ Risk/reconciliation
→ Verifier retain
→ final binding
→ M2
```

逐层查断点。禁止制造 page/bbox、放松 Evidence scope 或按 Gold page 特判。

## 8. Remaining deterministic / numeric / conflicts

继续处理有新 proof 的通用 grammar / binding 问题：period、Notes/reference、spaced decimal、percentage、negative、unit/currency、flattened/multiline table、繁简体/英文标签等。

事实不唯一或同 period 真冲突时继续 `pending / needs_review`，不能为了 recall 强行 verified。

direct ranked-table rejected implementation 不得原样恢复。

## 9. LLM / Evidence stability

只有在 deterministic/retrieval/binding roots 排除后，且 evidence 明确指向 structured output variance 时，才改 prompt/schema/bounded repair/candidate presentation。

LLM 不得 invent Evidence；repair 不得猜 Gold；不得 retry-to-improve benchmark。

## 10. Acceptance / Partial Revert

一个 multi-root bundle 只要：

- targeted / controls PASS；
- Gold/Validation/Blind 边界保持；
- precision / structured validity 无重要回归；
- fixed-journal 总体改善或关闭多个真实 structural misses；

即可接受有效子项。

若 A/B 有 gain、C regression：只撤 C。始终维护 `BEST_KNOWN_GOOD_COMMIT`。

## 11. 测试节奏

### Level 1 — subfix

```text
targeted tests
affected audited units
negative controls
adversarial cases
```

### Level 2 — bundle

```text
fixed10 journal
offline/gated M1/M2
per-family diff
precision / regression
network-call count
```

### Level 3 — meaningful checkpoint

```text
full pytest
compileall
validate_project
validate_competition_data
validate_competition_runtime
git diff --check
```

不要每个微小 patch 都跑完整 suite。

## 12. 扩样与 fresh provider

有 meaningful gain 后：

```text
fixed10 → Development 20 → 40 → ALL79
```

便宜的 retrieval/fact/binding funnel 可以更频繁覆盖 ALL79，以发现 fixed10 没覆盖的大类问题。

fresh provider 只在 meaningful bundle、关键 funnel 关闭或准备新 best checkpoint 时执行。fixed 与 fresh 结果分开记录；单次 provider variance 不能覆盖 deterministic tests 已证明正确的 generic fix。

## 13. 不可破坏边界

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

## 14. 与其他 owner 的接口

- Frontend：稳定 RiskItem / Evidence / Calculation / Verifier / conflict-recheck schema；
- Market-X：可靠 issuer/listing identity 与必要 Document metadata；
- Dynamic Model：若模型需要 Document feature，提供 versioned schema-bound vector，不从 Gold 重建；
- Release：最终冻结 SHA、Prompt/Schema/Config identity、ALL79 metrics、artifact manifest。

## 15. 历史记录与停止条件

历史 Batch001–009 只保留单一 `V046_ROLE_B_EXPERIMENT_LEDGER.md` + machine-readable reports + Git history；不要再为每个小 batch 往 `docs/` 主目录堆新的当前计划。

只有以下情况停止：

1. ALL79 `M1>=0.80`、`M2>=0.85` 并形成 freeze candidate；
2. 所有 remaining roots 都被证明依赖真实不可得外部输入，代码侧无可行动 root；
3. Owner 明确 `STOP`。

单次失败、root rejected、fixed10 不涨、fresh variance、subfix regression、merge conflict、一个 batch 结束都不是停止条件。

在 DONE 前：`AUTO_CONTINUE = TRUE`。
