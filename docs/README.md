# Documentation Index and Governance

> 状态日期：`2026-08-28`

仓库文档已经收敛为“一套指标、一套 Gate、一套总计划”。历史 PR 完成报告和一次性运行提示词不再作为当前状态源；需要时从 Git 历史或对应 PR 查询。

## 1. 当前权威文档

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口、最新数字与 6 阶段摘要 |
| `COMPETITION_METRIC_PROTOCOL.md` | M1–M5、Gold、split 与 evaluator 的唯一指标口径 |
| `V0.4_RELEASE_ACCEPTANCE.md` | 唯一实时 Gate / blocker 状态源 |
| `COMPETITION_CLOSURE_PLAN.md` | 唯一统一执行计划、依赖关系和退出条件 |
| `ROADMAP.md` | 剩余路线的短版视图 |
| `ROLE_B_M1_M2_PLAN.md` | B 线 forensic、ablation、修复和 Full Development 计划 |
| `ROLE_D_MODEL_DECISION.md` | frozen PR-F 与 v2 candidate 的治理晋升决策 |
| `V045_ROLE_D_FINAL_CLOSURE.md` | D 线正式物化、receipt、strict revalidation 边界 |
| `SUBMISSION_RUNBOOK.md` | 从本地复验到 final bundle 的操作手册 |
| `TEAM_QUICKSTART.md` | fresh clone 后离线回放 final-three 的最短路径 |
| `PROJECT_SPEC.md` | 产品范围、赛题覆盖与不可破坏原则 |
| `ARCHITECTURE.md` | 当前 runtime 与 v0.4.6 B 线诊断架构 |
| `DATA_SCHEMA.md` | runtime、诊断、评测和交付 artifact contract |
| `COMPETITION_DATA_OVERVIEW.md` | 数据、Development / Validation / Blind 边界 |
| `DOCUMENT_AUDIT_20260828.md` | 本轮保留、更新和删除记录 |

## 2. 仍保留的技术与冻结合同

- `V04_PR_D_INPUT_BINDING.md`；
- `V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md`；
- `V04_ORACLE_GOLD_COVERAGE_AUDIT.md`；
- `V04_ORACLE_REFRESH_GOVERNANCE.md`；
- `V04_ORACLE_V2_COMPLETION_REPORT.md`；
- `V045_ROLE_D_V2_CANDIDATE_REPORT.md`：原始 research candidate 报告；
- `annotation/`、`research/` 中仍有明确消费者的材料。

这些文件不是当前路线图，但仍承担 contract、provenance 或 research 证据角色。

## 3. Source-of-truth hierarchy

出现冲突时按以下顺序裁定：

1. 代码 validator、Pydantic、Protocol 和 fail-closed guard；
2. `reports/frozen/*.json`、hash-bound manifest / receipt；
3. `COMPETITION_METRIC_PROTOCOL.md`；
4. `V0.4_RELEASE_ACCEPTANCE.md`；
5. `COMPETITION_CLOSURE_PLAN.md`；
6. 当前 lane 文档和 Runbook；
7. research、历史 PR、Git history。

文档中的“PASS implementation”不等于最终比赛 Gate 已通过；必须存在对应 runtime evidence。

## 4. 当前状态摘要

```text
B fixed-10 M1 = 23.33%
B fixed-10 M2 = 18.75%
B v0.4.6 diagnostics + read-only Evidence auditor = implemented; full measured run pending
D frozen M5 artifacts / receipt = recorded
D v2 candidate Recall = 52.17%; F1 = 42.11%; not promoted
C strict contract = 1/3
E accepted real-provider = 2/3
M3 = 3/3 exactly 1.0
M4 = 0/6
overall = NOT COMPETITION_READY
```

## 5. 文档生命周期

长期保留的文档必须至少满足一项：

- 当前唯一状态源、计划或可重复 Runbook；
- 被代码、CI 或 validator 直接消费的合同；
- 不可重建的冻结测量或 provenance；
- 仍有明确消费者的 research / annotation 证据。

以下内容不再长期保留在 `docs/` 根目录：

- 一次性 Codex 提示词；
- 已解除的 blocker；
- 旧角色排期；
- PR completion report；
- 与当前 Metric-v2 身份不一致的 benchmark 叙述；
- 被新计划完整取代的重复文档。

## 6. 治理边界

可以移除的只是流程冗余，例如固定迭代轮数、Runner-only 和绝对禁止检索实验。

不能移除：Existing Gold immutable、Validation one-shot、Blind 隔离、Evidence scope、PIT、Trace、deterministic calculation、Secret/PDF/raw data 安全边界。
