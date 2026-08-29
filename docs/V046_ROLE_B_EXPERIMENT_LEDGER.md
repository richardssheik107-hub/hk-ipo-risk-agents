# Role-B v0.4.6 — Batch 001–010 Experiment Ledger

> 文档类型：**HISTORICAL EXPERIMENT LEDGER / NOT A CURRENT PLAN**  
> 当前执行计划：`team/01_M1_M2_OWNER.md`  
> 当前 Release 状态：`V0.4_RELEASE_ACCEPTANCE.md`

本文件是 Role-B fixed10 / fixed-journal 历史实验的单一人类可读总账。过去的逐批 Markdown 说明已从 `docs/` 主目录清理；完整 diff 由 Git history 保留，机器可读结果继续保留在 `reports/v046_role_b/`。

| Batch | Decision | Main finding | Governed result |
|---|---|---|---|
| 001 | merged, trace contract corrected | cash-runway trace join had discarded valid candidates | official baseline M1 8/30, M2 11/48; corrected exact-anchor Recall@20 30/48 |
| 002 | accepted bounded conversion work | recovered deterministic Financial facts without changing retrieval | offline replay M1 5/30, M2 7/48 → 5/30, 9/48 |
| 003 | rejected production selector patch | zero proven period-selector bugs | fixed journal M1 10/30, M2 14/48 |
| 004 | accepted deterministic gain | preserve bounded pending concentration facts | fixed journal M1 12/30, M2 17/48; fresh gated 10/30, 15/48 |
| 005 | accepted deterministic gain | spaced decimals and local period binding | fixed journal M1 12/30, M2 18/48; fresh gated 11/30, 17/48 |
| 006 | rejected stale root | zero current period-candidate-missing units | production unchanged |
| 007 | rejected misclassified root | 11/11 governed pages had extractable text | 3 deterministic-fact and 3 retrieval-candidate reclassifications |
| 008 | accepted deterministic gain | legacy Chinese cash statement grammar / explicit Notes column | fixed journal gated M1 13/30, M2 20/48 |
| 009 | partial accept | generalized Legal lifecycle recognition accepted; direct ranked-table candidate rejected/reverted | fixed journal gated M1 14/30, M2 21/48; rejected candidate held totals flat and reduced supplier existence F1 to 0.80 |
| 010 | accepted monotonic gain | recover strict ranked-table row order as physical-page Evidence while leaving policy decisions unchanged | fixed journal gated M1 15/30, M2 24/48; Development20 offline M1 14/50, M2 28/98 |

## Comparable fixed-journal progression

只有共享 frozen fixed10 identity 和 canonical replay journal 的结果做直接比较：

```text
Batch003 floor  M1 10/30  M2 14/48
Batch004        M1 12/30  M2 17/48
Batch005        M1 12/30  M2 18/48
Batch008        M1 13/30  M2 20/48
Batch009        M1 14/30  M2 21/48
Batch010        M1 15/30  M2 24/48
```

Fresh provider checkpoint 单独记录，因为 journal/provider identity 不同，并包含真实 runtime variance。最后一个 real fresh checkpoint 仍是 Batch005：M1 `11/30`、M2 `17/48`。Batch008–010 `network_calls=0`，不得把 fixed-journal 结果描述为 fresh-provider gain。

## Latest accepted / rejected facts

Accepted：

- Batch008：legacy Chinese-word year/date、explicit Notes column、繁简体 operating-cash-flow wording 的 bounded deterministic compatibility；
- Batch009：generalized Legal redemption/restoration lifecycle recognition；
- Batch010：严格完整的 rank-1-to-5 table 仅用于恢复同一 physical page 的真实 Evidence，不直接改变风险事实、等级、状态、分数或 Calculation。fixed10 gated 净增 `+1 M1 / +3 M2`，Development20 offline 同样净增 `+1 M1 / +3 M2`，extra10 无回退。

Rejected：

- direct ranked concentration-table fact conversion：没有提升 canonical M1/M2，并使 supplier existence F1 `0.875 → 0.80`，已完整回滚；Batch010 没有恢复该决策路径。

历史 bounded audit 也已排除 broad period candidate generation 和 broad Parser preservation 作为当时 active root。

## Current handoff to live execution

当前 live 执行以 `team/01_M1_M2_OWNER.md` 为准。Batch010 后当前 root order：

```text
remaining deterministic / numeric extraction
→ risk conversion after consumed Evidence
→ exact page / anchor Evidence binding
→ genuine conflict fail-closed
→ fixed-vs-fresh LLM / Evidence variance
```

执行模式为 multi-root wide sprint / goal mode：多个 proven compatible roots 可同轮推进、独立 commit、bundle benchmark、partial revert，并在 meaningful gain 后按 Development20 → Development40 → ALL79 扩大。

## Validation and governance

```text
Batch010 targeted tests = 120 passed
full pytest = 2304 passed, 2 skipped, 3 warnings
validate_project = PASS
validate_competition_data = PASS
validate_competition_runtime = PASS
compileall = PASS
git diff --check = PASS
Development-only = true
Validation opened for tuning = false
2025 Blind outcome accessed for optimization = false
Existing Gold modified = false
runtime received Gold = false
```

full Development Gate 仍开放。fixed10 / Development20 提升是诊断 evidence，不是 Competition Ready。

## Preservation policy

不再为每个新 batch 在 `docs/` 主目录增加独立长篇说明。历史保存依赖：

```text
this consolidated ledger
+ reports/v046_role_b machine-readable artifacts
+ immutable/frozen receipts where applicable
+ Git commits / PR history
```
