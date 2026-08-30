# Documentation Index and Governance

> 状态日期：`2026-08-29`

仓库文档收敛为：**一个总计划、一个实时 Release Gate、一个冻结指标协议、五条 owner 执行线，以及少量长期规范 / 冻结证据。**

不再同时维护多份 Roadmap / Current Plan / lane plan / 单批次实验说明作为“当前状态源”。

## 1. 当前权威入口

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口与当前五项主任务 |
| `COMPETITION_CLOSURE_PLAN.md` | **唯一当前总计划 / 优先级 / 依赖关系** |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一实时 Release Gate / blocker 状态源** |
| `COMPETITION_METRIC_PROTOCOL.md` | 冻结 Metric-v2、Gold、split、M1/M2/M3/M5 口径 |
| `team/README.md` | 五人并行执行总入口 |
| `team/01_M1_M2_OWNER.md` | M1/M2 autonomous wide-sprint 执行线 |
| `team/02_FRONTEND_OWNER.md` | final frontend / product execution |
| `team/03_DYNAMIC_MARKET_X_OWNER.md` | Dynamic Market-X execution |
| `V046_ROLE_C_DYNAMIC_MARKET_X.md` | Dynamic Market-X 泛化合同、PIT 边界、missing_reason 词表、Model handoff 绑定 |
| `team/04_DYNAMIC_MODEL_OWNER.md` | Dynamic Model / Prediction / SHAP + D decision |
| `team/05_RELEASE_SUBMISSION_OWNER.md` | integration / freeze / Validation / submission |
| `V046_ROLE_B_EXPERIMENT_LEDGER.md` | Role-B Batch001–009 **历史总账**；不是 live plan |
| `ROLE_D_MODEL_DECISION.md` | frozen PR-F vs v2 promote/retain 决策入口 |
| `V045_ROLE_D_FINAL_CLOSURE.md` | Role-D hash-bound closure / receipt 历史证据 |
| `SUBMISSION_RUNBOOK.md` | freeze 到 secure package 的操作手册 |
| `TEAM_QUICKSTART.md` | fresh clone / canonical replay |

## 2. 长期规范 / 研究证据

这些不是“当前计划”，而是稳定 contract / architecture / research：

- `PROJECT_SPEC.md`
- `ARCHITECTURE.md`
- `DATA_SCHEMA.md`
- `COMPETITION_DATA_OVERVIEW.md`
- `research/*`
- `annotation/*`

Research 文档可以保留历史研究结论，但不能覆盖当前 Release / Execution 状态。

## 3. 当前五项主任务

| 主任务 | 核心目标 | 优先级 |
|---|---|---|
| M1 / M2 文档智能优化 | ALL79 M1 `>=80%`、M2 `>=85%` | P0 |
| 前端 / 产品展示 | 把真实系统做成答辩级最终 UI | P0/P1 |
| Market-X 动态泛化 | 任意合法新 IPO 得到真实 Market-X 或诚实降级 | P0 |
| Model / Prediction / SHAP 动态化 | 新案例真实 frozen-model inference + native SHAP | P0 |
| 最终集成、验收、文档和提交包 | Freeze / one-shot Validation / audits / fresh clone / ZIP | P1 → 最后 P0 |

final-three 全链路已经稳定，后续主要作为回归保护和答辩 fallback。

## 4. Role-B 当前口径

PR #189 已把 Batch008/009 accepted production fixes 和 fixed-journal checkpoint 合入 main：

```text
Batch009 fixed-journal gated M1 = 14/30 = 46.67%
Batch009 fixed-journal gated M2 = 21/48 = 43.75%
Batch009 offline M1 = 9/30
Batch009 offline M2 = 15/48
```

最后一个真实 fresh-provider checkpoint 仍是 Batch005：

```text
fresh gated M1 = 11/30
fresh gated M2 = 17/48
structured valid = 38/40
fallback = 2
```

因此 fixed-journal gain 与 fresh-provider evidence 必须分开写。

最新 accepted：Batch008 cash statement compatibility、Batch009 Legal lifecycle recognition。direct ranked concentration-table candidate 已因无 M1/M2 gain 且 supplier existence F1 回归而完整回滚，不作为当前路线。

当前 root 顺序：

```text
retrieval candidate generation / ranking
→ exact page / anchor Evidence binding
→ remaining deterministic / numeric extraction
→ genuine conflict fail-closed
→ fixed-vs-fresh LLM / Evidence variance
```

执行方式允许 multi-root wide sprint：多个 proven compatible roots 同轮推进、独立 commit、bundle benchmark、partial revert，仅保留 best checkpoint；有意义提升后尽快扩大 Development。

## 5. Source-of-truth hierarchy

出现冲突时按顺序：

1. 代码 validator / Pydantic / fail-closed guard；
2. `reports/frozen/*.json`、hash-bound manifest / receipt；
3. `COMPETITION_METRIC_PROTOCOL.md`；
4. `V0.4_RELEASE_ACCEPTANCE.md`；
5. `COMPETITION_CLOSURE_PLAN.md`；
6. `team/*` owner 文档 / Runbook；
7. experiment ledger / architecture / research / Git history。

fixed10 结果不能冒充 ALL79；fixed-journal 结果不能冒充 fresh-provider；Replay 不能冒充实时推理。

## 6. 文档生命周期

长期保留文档至少满足一项：

- 当前总计划 / Release Gate / Runbook；
- 被代码或 CI 消费的合同；
- 不可重建的冻结测量 / provenance / receipt；
- 单一历史总账；
- 有明确消费者的长期 research / annotation 证据。

以下类型不再长期保留在 `docs/` 主目录：

- 第二套 Roadmap；
- compatibility-only Current Plan；
- 已被 owner 文档替代的 lane plan；
- 001/002/003… 单批次实验说明；
- 一次性日期审计说明；
- 已被正式 decision 文档吸收的 candidate report。

这些历史信息仍可通过 Git history 和治理安全 `reports/` artifact 追溯。

## 7. Release policy

```text
current-case UI completed
!=
competition release passed
```

Human Review UI/export 可保留为 optional 人机协同能力，但不要求额外真人标注，不是当前 Release Gate。

不可移除的边界：Existing Gold immutable、Validation one-shot、Blind isolation、Evidence scope、PIT、deterministic Calculation、uncalibrated-score 语义、Secret/PDF/raw licensed data 安全。
