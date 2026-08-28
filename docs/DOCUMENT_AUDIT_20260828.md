# Documentation Audit — 2026-08-28

> 初始审计基线：`a2d1f16f6e72e5520881b362e356bdf2d09e2809`
>
> 已同步最新 main：`2b266a2d2ad67ace2635b11c4bae8ccd8c26ae33`

## 1. 目标

仓库现在只保留一套指标、一套 Gate、一套总计划和必要技术合同。历史实现过程从 Git/PR 查询，不再由几十份 completion report 充当当前入口。

## 2. 新的状态源

```text
README.md
docs/README.md
docs/V0.4_RELEASE_ACCEPTANCE.md
docs/COMPETITION_CLOSURE_PLAN.md
docs/ROADMAP.md
docs/ROLE_B_M1_M2_PLAN.md
docs/ROLE_D_MODEL_DECISION.md
docs/SUBMISSION_RUNBOOK.md
```

## 3. 本轮重写

- `../README.md`；
- `../AGENTS.md`；
- `README.md`；
- `ROADMAP.md`；
- `V0.4_RELEASE_ACCEPTANCE.md`；
- `PROJECT_SPEC.md`；
- `ARCHITECTURE.md`；
- `DATA_SCHEMA.md`；
- `COMPETITION_DATA_OVERVIEW.md`；
- `SUBMISSION_RUNBOOK.md`。

新增：`COMPETITION_CLOSURE_PLAN.md`、`ROLE_B_M1_M2_PLAN.md`、`ROLE_D_MODEL_DECISION.md` 和本文档。

## 4. 最新 main 纳入情况

PR #153 的 read-only Evidence auditor 与测试已保留在分支；其过期单案例状态报告没有恢复。当前计划将 auditor 视为已实现工具，同时仍将 Candidate/LLM/Builder lifecycle trace 列为待补缺口。

Role-D v2 candidate 已纳入当前计划，但仍保持 research candidate；正式 receipt 与 handoff 继续绑定 frozen PR-F，直到 A 创建 promotion record。

## 5. 已核验并保留，不追溯改写

- `COMPETITION_METRIC_PROTOCOL.md`：冻结指标合同；
- `V045_ROLE_D_FINAL_CLOSURE.md`：正式 D 证据边界；
- `V045_ROLE_D_V2_CANDIDATE_REPORT.md`：原始候选报告；
- `V04_PR_D_INPUT_BINDING.md`；
- `V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md`；
- Oracle audit / governance / completion docs；
- `CHANGELOG.md`：历史事实记录；
- annotation / research 中仍有消费者的材料。

## 6. 删除的过期/重复文件

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

内容仍可从 Git 历史恢复。

## 7. 流程限制调整

删除：固定 2–4 轮、Runner-only、只能读两个 summary、绝对禁止 Retriever/model/transport Development 实验、Screenshot optional P2。

保留：Gold immutable、Validation one-shot、Blind 隔离、Evidence scope、PIT、Calculation、Trace、Secret/PDF/raw-data 安全。

## 8. 发现的治理不一致

`CHANGELOG.md` 保留了一条使用 2025 Blind 文档定位缺陷的历史记录。它没有说明 outcome/y 被访问，但说明 Blind 输入曾被观察，因此旧文档中笼统的 `Blind accessed=false` 不能解释为“输入和标签均从未接触”。

处理：历史记录保留；当前文档使用精确表述；从本规则生效起不再使用 Blind 输入或 outcome 优化；最终治理报告如实披露。

## 9. 文档生命周期

长期文档必须是当前状态/计划/Runbook、代码/CI 消费的合同、不可重建 provenance，或仍有明确消费者的 research/annotation 材料。
