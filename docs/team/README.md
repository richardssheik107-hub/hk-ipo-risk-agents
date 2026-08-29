# Five-Person Competition Execution Index

> 状态日期：`2026-08-29`  
> 目的：把当前剩余比赛任务固定成 5 条可以并行推进的工作流；不再新增第二套 Roadmap。

## 当前五人分工

| Owner | 主任务 | 核心目标 | 优先级 |
|---|---|---|---|
| **Person 1** | M1 / M2 文档智能优化 | ALL79 M1 `>=80%`、M2 `>=85%` | **P0** |
| **Person 2** | 前端 / 产品展示 | 把现有真实系统做成答辩级最终 UI | **P0/P1** |
| **Person 3** | Market-X 动态泛化 | 任意合法新 IPO 得到真实 Market-X 或诚实降级 | **P0** |
| **Person 4** | Model / Prediction / SHAP 动态化 | 新案例真实 frozen-model inference + native SHAP；完成 D 决议 | **P0** |
| **Person 5** | 最终集成 / 验收 / 文档 / 提交包 | Freeze / Validation / audits / fresh clone / ZIP | **P1 → 最后 P0** |

详细任务：

```text
01_M1_M2_OWNER.md
02_FRONTEND_OWNER.md
03_DYNAMIC_MARKET_X_OWNER.md
04_DYNAMIC_MODEL_OWNER.md
05_RELEASE_SUBMISSION_OWNER.md
```

## 当前稳定产品基线

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
rechecks = 17/17
budget skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
fresh clone / Streamlit smoke / team-ready checks = PASS
```

这条 final-three 线路是 regression baseline / 答辩 fallback，不是能力上限。

## Person 1 — M1 / M2 Document Intelligence

文档：[`01_M1_M2_OWNER.md`](01_M1_M2_OWNER.md)

PR #189 后正式 fixed-journal gated：

```text
Batch009 M1 = 14/30 = 46.67%
Batch009 M2 = 21/48 = 43.75%
offline = 9/30, 15/48
last real fresh = Batch005 11/30, 17/48
```

已接受 Batch008 cash deterministic compatibility、Batch009 Legal lifecycle recognition；direct ranked concentration-table candidate 已拒绝并回滚，不能直接恢复。

当前执行模式是 autonomous multi-root wide sprint：

```text
retrieval candidate generation / ranking
+ exact page / anchor Evidence binding
+ remaining deterministic / numeric extraction
+ genuine conflicts
+ fixed-vs-fresh LLM / Evidence stability
```

多个 proven compatible roots 可同轮推进，独立 commit，bundle benchmark，出现回归只撤问题 subfix。

最终完成条件：

```text
ALL79 Development
M1 >=0.80
M2 >=0.85
real LLM =79/79
```

## Person 2 — Frontend / Product Experience

文档：[`02_FRONTEND_OWNER.md`](02_FRONTEND_OWNER.md)

最终清楚支持：

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

统一呈现 Document Risk、Evidence、Market、Model/SHAP、Conflict/Recheck、Final Supervisor、Report/Trace。所有 channel state 必须真实，不能为“全绿”伪造数据。

## Person 3 — Dynamic Market-X

文档：[`03_DYNAMIC_MARKET_X_OWNER.md`](03_DYNAMIC_MARKET_X_OWNER.md)

路线：

```text
438 historical governed artifacts
→ unified cache-first runtime
→ arbitrary new IPO dynamic PIT Market-X
```

有合法数据真实算，无合法数据明确 `PARTIAL / UNAVAILABLE`；不允许 zero-fill 或 post-listing leakage。

## Person 4 — Dynamic Model / Prediction / SHAP

文档：[`04_DYNAMIC_MODEL_OWNER.md`](04_DYNAMIC_MODEL_OWNER.md)

同时关闭：

```text
PROMOTE_V2 / RETAIN_FROZEN_PR_F formal decision
+ final frozen model package
+ dynamic feature-vector inference
+ native SHAP
```

final-three per-case handoff 继续保留为稳定 baseline，但最终不能作为泛化机制。

## Person 5 — Release / Submission

文档：[`05_RELEASE_SUBMISSION_OWNER.md`](05_RELEASE_SUBMISSION_OWNER.md)

从现在开始持续做 integration watch，最后切换 P0：

```text
freeze
→ one-shot ALL19 Validation
→ CI / Blind / PIT / provenance / determinism / security / licensing audits
→ artifact index
→ fresh clone
→ secure ZIP + SHA-256 manifest
```

## 依赖关系

```text
Person 1 Document Intelligence ─────┐
                                    │
Person 3 Dynamic Market-X ──────────┼──→ Person 4 Dynamic Model / SHAP
                                    │            │
existing governed runtime ──────────┘            │
                                                 ▼
                                      Final Supervisor / Report
                                                 │
                                                 ▼
                                      Person 2 Final Frontend
                                                 │
                                                 ▼
                                      Person 5 Release / Submit
```

Person 2 可以提前完成信息架构和状态语义，不必等待 Person 3/4；但不能为未完成动态通道伪造 available。

Person 5 从项目开始做 integration watch，只有所有核心行为冻结后才运行最终 one-shot Validation。

## Shared non-negotiables

```text
Existing Gold immutable
Gold never enters runtime
Validation only once after freeze
2025 Blind untouched for optimization
PIT-safe Market
missing != zero
no company/stock/case/page/Gold-text hardcoding
no fake Evidence / bbox / Market / Model
uncalibrated model score != probability
fallback != real-provider success
no secrets / licensed PDF / raw EOD / raw journal / absolute local path in Git
```

## Merge 原则

稳定 `main` 始终是可回退答辩基线。所有开发在 feature branch；targeted / integration / relevant CI / `git diff --check` 通过后再 PR。

Role-B multi-root sprint 中每个独立 root 尽量单独 commit；bundle 回归时只撤问题 subfix，不丢掉已经证明有效的收益。

## 最终完成条件

```text
ALL79 M1 >=0.80
ALL79 M2 >=0.85
M3 =1.0
Dynamic Market-X acceptable
formal D model decision complete
Dynamic Model / SHAP complete
final frontend complete
capability proof complete
one-shot Validation complete under freeze
latest-main CI / Blind / provenance / determinism / security / licensing PASS
fresh clone PASS
secure submission package PASS
```

只有全部真实成立才可声明 `COMPETITION_READY`。
