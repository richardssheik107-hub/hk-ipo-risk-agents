# Documentation Index and Governance

> 状态日期：`2026-08-29`

仓库当前文档收敛为“一套冻结指标协议 + 一套实时 Release Gate + 一套统一执行计划”。历史 PR 报告和一次性运行提示词不作为当前状态源。

## 1. 当前权威文档

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口、最新数字和当前优先级 |
| `COMPETITION_METRIC_PROTOCOL.md` | 冻结 Metric-v2、Gold、split、M1/M2/M3/M5 口径；历史 M4 rubric 保留为 optional diagnostic |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一实时 Release Gate / blocker 状态源** |
| `COMPETITION_CLOSURE_PLAN.md` | 当前统一执行计划和优先级 |
| `ROADMAP.md` | 剩余路线短版 |
| `ROLE_B_M1_M2_PLAN.md` | B 线当前 Batch009 checkpoint、root cause 和 ALL79 计划 |
| `V046_ROLE_B_DETERMINISTIC_FACT_BATCH_008.md` | Batch008 accepted legacy cash deterministic measurement |
| `V046_ROLE_B_WIDE_SPRINT_BATCH_009.md` | Batch009 partial-accept measurement、rejected ranked-table 记录 |
| `V046_ROLE_B_EXPERIMENT_LEDGER.md` | Batch001–009 实验台账 |
| `ROLE_D_MODEL_DECISION.md` | frozen PR-F vs v2 candidate 的 promote/retain 决策 |
| `V045_ROLE_D_FINAL_CLOSURE.md` | D 线正式物化、receipt、strict revalidation 边界 |
| `SUBMISSION_RUNBOOK.md` | 从当前状态到 final package 的操作手册 |
| `TEAM_QUICKSTART.md` | fresh clone 后离线回放三案例 |
| `team/README.md` | 五人并行执行总索引及 owner 文档入口 |
| `PROJECT_SPEC.md` | 产品范围、Dynamic New-IPO 目标和不可破坏原则 |
| `ARCHITECTURE.md` | runtime / modeling / diagnostics 架构 |
| `DATA_SCHEMA.md` | runtime、评测和 artifact contract |
| `COMPETITION_DATA_OVERVIEW.md` | 数据与 Development / Validation / Blind 边界 |

## 2. Source-of-truth hierarchy

出现冲突时：

1. 代码 validator / Pydantic / fail-closed guard；
2. `reports/frozen/*.json`、hash-bound manifest / receipt；
3. 冻结 Metric-v2 对 M1/M2/M3/M5 的定义；
4. `V0.4_RELEASE_ACCEPTANCE.md` 对**当前 Release Gate 是否适用**的判定；
5. `COMPETITION_CLOSURE_PLAN.md`；
6. lane 文档 / Runbook；
7. research、历史 PR、Git history。

### M4 / Human Review

冻结 Metric-v2 中的 M4 explanation rubric 仍可作为 optional quality diagnostic，但 active Release policy 已明确：

```text
M4 6 human reviews = NOT_REQUIRED_FOR_RELEASE
```

Human Review UI/export 可以保留，不新增真人标注，不影响 `COMPETITION_READY`。

## 3. 当前状态摘要

```text
Role-B latest comparable fixed-journal gated:
M1 = 14/30 = 46.67%
M2 = 21/48 = 43.75%

Role-B latest real fresh checkpoint remains Batch005:
M1 = 11/30
M2 = 17/48
structured valid = 38/40

Batch008 = accepted legacy cash deterministic fix
Batch009 = accepted Legal lifecycle fix
ranked-table candidate = REJECTED / REVERTED
historical GLM-5.3 harness = archived MEASURED_FAIL

D frozen PR-F = formal identity
D v2 candidate Recall = 52.17%; F1 = 42.11%; not promoted

Market final-three = 3/3
Frozen Model final-three = 3/3
Final Supervisor E1 = 3/3 first-attempt
M3 = 1.0 x 3
recheck = 17/17
Evidence screenshot = 17/17 precise
seven-stage = 21/21
canonical replay = 66 files
team clone / fresh clone / Streamlit smoke / CI = PASS

overall = NOT COMPETITION_READY
```

fixed-journal / fixed10 仍只是诊断，正式 B Gate 仍是 ALL79 Development。

## 4. 当前未关闭工作

```text
P0 Role-B ALL79 M1/M2
P0 Dynamic New-IPO Full Path
P0 Role-D promote/retain + strict release identity
P1 competition capability demos
P1 freeze / one-shot Validation / audits / secure package
```

Role-B Batch009 后优先：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflicts
→ fixed-vs-fresh LLM / Evidence variance
```

Final Supervisor、M3、final-three Market/Model、Evidence screenshot、team-ready replay 已进入 regression-protection 状态，不再作为开放式优化主线。

## 5. Dynamic New-IPO 状态

当前三案例是稳定 replay，不是期望的能力上限。

```text
Phase 1 — 438 historical frozen universe
Market-X → frozen model dynamic inference → native SHAP

Phase 2 — arbitrary new IPO
PIT history → Dynamic Market-X → frozen model inference → SHAP → report
```

不得通过 case-specific handoff / hardcoding 假装泛化。

## 6. 五人执行入口

见 [`team/README.md`](team/README.md)：

```text
Person 1  M1/M2 Document Intelligence
Person 2  Frontend / Product UX
Person 3  Dynamic Market-X
Person 4  Dynamic Model / SHAP
Person 5  Release / Submission
```

各 lane 不得跨界为了“让页面绿”或“让 Gate 绿”而改变其他 lane 的真实语义。

## 7. 文档生命周期

长期保留文档必须至少满足一项：

- 当前状态源、计划或可重复 Runbook；
- 被代码、CI 或 validator 消费的合同；
- 不可重建的冻结测量 / provenance；
- 有明确消费者的 research / annotation 证据。

历史 batch 报告可以保留用于 provenance，但不得覆盖当前实时状态源。

## 8. 治理边界

不能移除：

- Existing Gold immutable；
- Validation one-shot；
- Blind 隔离；
- Evidence scope；
- PIT；
- Trace；
- deterministic calculation；
- frozen score 语义；
- Secret/PDF/raw licensed data 安全边界。

可以移除的是项目内部不再需要的流程 Gate，例如已经取消的 M4 真人评审要求。
