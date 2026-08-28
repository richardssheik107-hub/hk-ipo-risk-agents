# Documentation Audit — 2026-08-28

> 审计基线：`a2d1f16f6e72e5520881b362e356bdf2d09e2809`

本审计的目标是让仓库只保留一套当前计划、一套 Gate、一套指标口径和必要的技术/治理合同。历史实现过程仍可从 Git 历史、PR 和 commit 追溯，不再以大量 completion report 混入当前文档入口。

## 1. 当前文档层级

### 当前状态与执行

- `../README.md`：项目入口与简明状态；
- `README.md`：文档索引与状态源层级；
- `COMPETITION_CLOSURE_PLAN.md`：唯一统一执行计划；
- `ROADMAP.md`：6 阶段剩余路线摘要；
- `V0.4_RELEASE_ACCEPTANCE.md`：唯一实时 Gate；
- `ROLE_B_M1_M2_PLAN.md`：B 线当前工作计划；
- `V045_ROLE_D_FINAL_CLOSURE.md`：D 线正式证据与复验边界；
- `SUBMISSION_RUNBOOK.md`：最终复现与封包命令。

### 指标、架构与数据合同

- `COMPETITION_METRIC_PROTOCOL.md`；
- `PROJECT_SPEC.md`；
- `ARCHITECTURE.md`；
- `DATA_SCHEMA.md`；
- `COMPETITION_DATA_OVERVIEW.md`；
- `V04_PR_D_INPUT_BINDING.md`；
- `V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md`。

### 冻结证据与治理

- `V04_ORACLE_GOLD_COVERAGE_AUDIT.md`；
- `V04_ORACLE_REFRESH_GOVERNANCE.md`；
- `V04_ORACLE_V2_COMPLETION_REPORT.md`；
- `V045_ROLE_D_V2_CANDIDATE_REPORT.md`（research candidate，非正式替代）；
- `annotation/`、`research/` 下仍有明确消费者的材料。

## 2. 本轮更新的文档

- `../README.md`；
- `README.md`；
- `ROADMAP.md`；
- `V0.4_RELEASE_ACCEPTANCE.md`；
- `PROJECT_SPEC.md`；
- `ARCHITECTURE.md`；
- `DATA_SCHEMA.md`；
- `SUBMISSION_RUNBOOK.md`；
- `COMPETITION_METRIC_PROTOCOL.md`；
- `COMPETITION_DATA_OVERVIEW.md`；
- `CHANGELOG.md`；
- 新增 `COMPETITION_CLOSURE_PLAN.md`；
- 新增 `ROLE_B_M1_M2_PLAN.md`；
- 新增本文档。

## 3. 删除的过期或重复文档

以下文件不再作为当前事实源，删除后仍可通过 Git 历史查询：

```text
COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md
V045_CURRENT_EXECUTION_PLAN.md
V045_ROLE_B_FIXED10_ITERATION_WORKFLOW.md
V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
V045_ROLE_B_REAL_BENCHMARK_REPORT.md
V04_FIVE_PERSON_EXECUTION_PLAN.md
V04_C_HSI_SOURCE_INTEGRATION_REPORT.md
V04_PR_A_COMPLETION_REPORT.md
V04_PR_B_COMPLETION_REPORT.md
V04_PR_C_COMPLETION_REPORT.md
V04_PR_D_COMPLETION_REPORT.md
V04_PR_E_COMPLETION_REPORT.md
V04_PR_F_COMPLETION_REPORT.md
V04_PR_G_A_GATE_REVIEW.md
V04_PR_G_COMPLETION_REPORT.md
V04_PR_H_COMPLETION_REPORT.md
V04_ROLE_E_COMPLETION_REPORT.md
```

删除原因：

- 与当前 Gate / Roadmap / Closure Plan 重复；
- 包含已解除 blocker 或旧 next step；
- 使用 v0.4.5 Runner-only 流程描述，未覆盖 v0.4.6 forensic/ablation；
- 历史 PR 完成报告不应被误读为当前项目状态；
- 历史 benchmark 不应与当前 Metric-v2 fixed-10 混用。

## 4. 去掉的过度流程约束

- 固定最多 2–4 轮；
- Codex 只能执行 Runner、不得完整审计；
- 只能读取 `iteration_summary` / `failure_focus`；
- 任何情况下都禁止 Retriever 重构；
- 任何情况下都禁止模型 / transport 对照；
- 每轮只能改一个文件或一个函数；
- Evidence screenshot 只是可选 P2；
- fixed-10 达标即可视为比赛达标。

替代规则是：开发集内、身份冻结、无 Gold 泄漏、测试和消融充分、指标不退化、达到停止条件即停止。

## 5. 继续保留的硬治理规则

- Existing Gold immutable；
- Validation one-shot after freeze；
- Blind outcome inaccessible before authorization；
- Evidence scope / Trace / PIT / deterministic calculation；
- 无公司、case、股票、页码特判；
- 无 Secret、授权 PDF、raw EOD、绝对路径进入 Git 或 bundle；
- `COMPETITION_READY` 必须由真实 artifact 证明。

## 6. 文档生命周期

一个文档只有满足以下至少一项才长期保留：

- 当前唯一状态源、计划或运行手册；
- 仍被代码/CI/validator 直接消费的合同；
- 不可重建的冻结测量或 provenance；
- 仍有明确消费者的 research / annotation 证据。

普通 PR 完成报告、一次性 Codex 提示词、已解除 blocker 和过期 next step 不再长期保留在 `docs/` 根目录。
