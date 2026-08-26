# Documentation Index and Governance

本文档是仓库文档治理入口。**当前状态只能由当前 Gate 文档、代码 validator、冻结 manifest 和最新实测报告共同确定，不能从历史 completion report 的“next step”语句推断。**

## 当前权威文档

| 文档 | 作用 |
|---|---|
| `../README.md` | 项目入口与当前摘要 |
| `V0.4_RELEASE_ACCEPTANCE.md` | **唯一当前 Gate / blocker 状态源** |
| `ROADMAP.md` | 只记录尚未关闭的执行路线 |
| `V04_FIVE_PERSON_EXECUTION_PLAN.md` | A/B/C/D/E ownership、handoff、merge boundary |
| `COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md` | 赛题要求 → 系统能力 → 验收 artifact 映射 |
| `SUBMISSION_RUNBOOK.md` | **最终安装、3-case smoke、readiness audit、打包与 freeze 操作手册** |
| `PROJECT_SPEC.md` | 产品边界与不可破坏原则 |
| `ARCHITECTURE.md` | 当前 runtime 架构 |
| `DATA_SCHEMA.md` | 当前公共/比赛 sidecar schema 说明 |
| `COMPETITION_DATA_OVERVIEW.md` | 数据范围、split、PIT/blind 边界 |
| `research/V04_DATA_READINESS.md` | 数据就绪技术事实 |
| `V045_ROLE_B_REAL_BENCHMARK_REPORT.md` | B 当前 governed offline benchmark 实测证据 |
| `V04_ROLE_E_COMPLETION_REPORT.md` | E 当前实现、3-case matrix 与 submission artifact 实测证据 |

`AGENTS.md` 是跨版本工程治理规则，优先级高于叙述性文档。

## Source-of-truth hierarchy

出现冲突时按以下顺序裁定：

1. 代码中的 validator / Pydantic / Protocol / fail-closed guard；
2. `reports/frozen/*.json` 与其 hash-bound frozen manifest；
3. 已冻结 completion report 中的**实测事实**；
4. `V0.4_RELEASE_ACCEPTANCE.md` 当前状态；
5. 其他 active docs；
6. research、历史 completion report、Git history。

历史文档可以保存当时的 Gate、下一步和限制，但它们的“当前/下一步”文本不会自动随 main 更新。

## 当前状态快照

当前 main 已完成：

- 3 个真实 2024 招股书 offline E2E 3/3 completed，完整性校验 3/3；
- 三案例 Agent / Tool / Evidence measured traceability 均为 1.0；
- Market Intelligence 已实现并正式接入 AI runtime，真实 provider 的 Market interpretation 已在两只真实 IPO 上通过；
- LLM Final Supervisor / conflict / bounded re-check / Human Review / 五工作区已实现；
- E 已生成 per-case reasoning log / case report / machine Gate-E1 evidence 的正式代码路径；
- A 已实现 final submission readiness、Blind/provenance/determinism audit、artifact index、Runbook 与 fail-closed packager；
- Role B 的 10-case governed offline benchmark **FAIL**：Risk P/R/F1 = 0%，Evidence Recall@5 = 20%；
- B 尚未完成固定 benchmark 上的 real-LLM measurement；
- D 尚未关闭最终 1D/5D/20D/60D submission package；
- final 3-case matrix 上的 real-provider Final Supervisor synthesis 尚未验收；
- Evidence page grounding 可用，parser 尚不产出 bbox；
- historical PR-H authentic frozen PR-F runtime/handoff 条件仍未闭合；
- 2025 Blind y 仍未访问。

精确 Gate 以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## 历史 / 冻结证据

以下类型默认**保留，不做“追当前状态”的编辑**：

- PR-A–PR-G completion reports；
- Oracle v1/v2 completion/evaluation records；
- `reports/frozen/*`；
- annotation protocol / receipt / ledger；
- Retriever、模型、数据源等 research technical notes；
- `CHANGELOG.md` 历史 release ledger。

如历史 completion report 写有“PR-X is next / not started”，应理解为 freeze-time handoff state，而不是当前 Roadmap。

## 已删除的过时/重复文档

本轮 A 文档审计删除以下不再承担唯一事实职责的文档：

- `END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`：与 Roadmap、五人计划、比赛硬化计划高度重复，且 Gate 状态已漂移；
- `DOCUMENTATION_AUDIT_2026-08-25.md`：一次性日期快照，本身会立即过时；治理规则已收敛到本文件；
- `UI_DESIGN_REFERENCE_2026-08-24.md`：一次性 UI 设计参考，相关产品结构已实现并由代码/tests 约束；
- `V045_ROLE_B_DOCUMENT_INTELLIGENCE_REPORT.md`：实现阶段报告已被 governed real benchmark 实测报告取代。

Git history 仍完整保留这些记录。

## 文档生命周期规则

新文档只有在满足至少一个条件时才应长期保留：

- 定义当前唯一 contract / Gate / ownership；
- 记录不可重建的冻结实测结果；
- 记录稳定技术设计，且仍有当前消费者；
- 作为 governed research / annotation evidence。

`SUBMISSION_RUNBOOK.md` 属于正式提交操作 contract，因此长期保留。禁止为了每一次 PR 新建长期“一次性 handoff / audit / preflight”文档；短期信息优先写 PR body，必须长期保留的内容合并进现有权威文档。

## 更新责任

- **A**：README、Gate、Roadmap、ownership、release/submission docs、readiness/audit/package tooling；
- **B**：Role-B benchmark / Document semantic evidence；
- **C**：Market technical evidence；
- **D**：Outcome/model/evaluation artifacts；
- **E**：Supervisor/Trace/Product completion evidence；
- shared architecture/schema 变更必须由 A 做 cross-lane review。
