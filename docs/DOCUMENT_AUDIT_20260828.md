# Documentation Audit — 2026-08-28

> 审计基线：`a2d1f16f6e72e5520881b362e356bdf2d09e2809`

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

新增：

- `COMPETITION_CLOSURE_PLAN.md`；
- `ROLE_B_M1_M2_PLAN.md`；
- 本审计文件。

## 4. 已核验并保留，不追溯改写

- `COMPETITION_METRIC_PROTOCOL.md`：冻结指标合同；
- `V045_ROLE_D_FINAL_CLOSURE.md`：最新 D 证据边界；
- `V04_PR_D_INPUT_BINDING.md`；
- `V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md`；
- Oracle audit / governance / completion docs；
- `V045_ROLE_D_V2_CANDIDATE_REPORT.md`：research candidate；
- `CHANGELOG.md`：历史事实记录，不因新计划清洗。

## 5. 删除的过期/重复文件

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

删除原因：旧 blocker/next step、v0.4.5 Runner-only、重复角色排期、历史 benchmark 身份混淆、PR completion report 冒充当前状态。内容仍可从 Git 历史恢复。

## 6. 流程限制调整

删除：固定 2–4 轮、Runner-only、只能读两个 summary、绝对禁止 Retriever/model/transport Development 实验、Screenshot optional P2。

保留：Gold immutable、Validation one-shot、Blind 隔离、Evidence scope、PIT、Calculation、Trace、Secret/PDF/raw-data 安全。

## 7. 发现的治理不一致

`CHANGELOG.md` 当前保留了一条“使用 2025 Blind 文档定位缺陷并确认结果”的历史记录。它没有说明 Blind outcome/y 被访问，但说明 Blind 输入曾被观察，因此旧文档中笼统的 `Blind accessed=false` 不能再解释为“输入和标签均从未接触”。

处理：

- 历史记录保留，不删除；
- 当前文档统一使用精确表述 `Blind outcome/y not accessed`；
- 从本规则生效起，2025 Blind 输入也不得用于优化；
- 最终治理报告如实披露该历史输入检查。

## 8. 文档生命周期

长期文档必须是当前状态/计划/Runbook、代码/CI 消费的合同、不可重建 provenance，或仍有明确消费者的 research/annotation 材料。
