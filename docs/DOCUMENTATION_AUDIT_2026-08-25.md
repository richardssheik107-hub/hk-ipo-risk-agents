# Documentation Audit — 2026-08-25

## 1. Audit objective

本轮文档清理将 active documentation 从“v0.4 baseline 建设阶段”统一到新的正式路线：

```text
PR-H completion
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ Competition Beta
→ v0.4.5 COMPETITION_READY
→ Submission / Demo Rehearsal
```

同时固定五人角色、并行方式、比赛指标、multi-horizon 诊断、Document benchmark、Market Intelligence、Multi-Agent conflict、Evidence Viewer 与最终提交责任。

## 2. Source-of-truth hierarchy

文档冲突时：

1. Pydantic / Protocol / validator / executable contract；
2. `reports/frozen/*.json`；
3. formal completion report / Gate review；
4. current active docs；
5. stable research reference；
6. Git history。

本轮不修改 frozen manifest，也不重写历史 completion result。

## 3. Active documents refreshed

以下文档更新到 2026-08-25 current state：

```text
README.md
AGENTS.md
docs/README.md
docs/ROADMAP.md
docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md
docs/V04_FIVE_PERSON_EXECUTION_PLAN.md
docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md
docs/PROJECT_SPEC.md
docs/ARCHITECTURE.md
docs/DATA_SCHEMA.md
docs/COMPETITION_DATA_OVERVIEW.md
docs/research/V04_DATA_READINESS.md
```

`CHANGELOG.md` 是历史变更记录，本轮审计后**刻意不重写**。

关键同步事项：

- PR-G = COMPLETE / FROZEN；PR-H = PARTIAL / BLOCKED；
- v0.4.3 尚未创建；
- PR-H formal blockers 固定为 frozen PR-F runtime/handoff + 3–5 real 2024 PDFs + full case matrix；
- HSI Extended 与 HKEX turnover 已 438/438 readiness；
- production industry return 保持 0/438，因为 company classification PIT mapping 不安全；
- PR-F 弱 5D baseline 被保留为诊断事实，不触发 Validation retuning；
- CH-1/2/3 允许并行；CH-4/5 与前面稳定接口重叠推进；
- 最终版本目标明确为 v0.4.5 COMPETITION_READY + reproducible submission package。

## 4. Documents intentionally retained

### Completion / Gate records

保留所有 PR-A–PR-H / Oracle completion 与 formal Gate review，因为它们是历史事实和 frozen provenance。

### Durable technical/governance references

保留：

```text
V04_PR_D_INPUT_BINDING.md
V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md
V04_ORACLE_REFRESH_GOVERNANCE.md
V04_ORACLE_GOLD_COVERAGE_AUDIT.md
V04_C_HSI_SOURCE_INTEGRATION_REPORT.md
UI_DESIGN_REFERENCE_2026-08-24.md
```

这些文档仍提供未来 decision / CH-5 / provenance 所需的独立信息。

### Research references

`docs/research/` 中冻结 policy、canonical contract、market foundation、Oracle pipeline、Retriever restart constraints 等继续保留。它们不作为 current Gate 文档，但仍约束未来 targeted research。

### Annotation assets

`docs/annotation/gpt_expert_v1_1/` 是 governed annotation data，不属于叙述性文档清理范围。

## 5. Documents retired in this audit

以下文档删除，因为其 durable fact 已被 completion report / code / current active plan 覆盖，继续留在 active tree 只会造成阶段口径混乱：

```text
DOCUMENTATION_AUDIT_2026-08-23.md
V04_PR_A_RUNBOOK.md
V04_PR_D_ROLE_B_DOCUMENT_QA.md
V04_ROLE_E_FINDINGS_HANDOFF.md
V04_PR_G_FINDINGS.md
```

### Rationale

- `DOCUMENTATION_AUDIT_2026-08-23.md`：被本次 audit 替代；
- `V04_PR_A_RUNBOOK.md`：PR-A 已 frozen，正式结果在 completion report + executable script + manifest；
- `V04_PR_D_ROLE_B_DOCUMENT_QA.md`：一次性交接 QA，PR-D 已 frozen；
- `V04_ROLE_E_FINDINGS_HANDOFF.md`：closed-out handoff，仍有效的功效/Oracle结论已有独立 audit/tool 或进入 current strategy；
- `V04_PR_G_FINDINGS.md`：实施期 advisory，多数问题已由 PR-G/PR-H/follow-up fixes 解决，current blocker 以 PR-H completion report 为准。

Git history 保留全部被删文本，不丢失审计历史。

## 6. Documentation lifecycle rule going forward

新阶段原则上不再创建长期 `HANDOFF_FINAL` / `PREP_V2` / one-shot readiness 文档。

临时协作信息进入：

```text
PR body
issue / comment
short local package README
```

只有以下信息进入 active docs：

```text
current program state
formal plan / owner / Gate
stable architecture/schema contract
measured readiness
formal completion/freeze evidence
```

当 CH-0 开始后，Competition Scorecard 与 acceptance matrix 应直接进入现有 Competition plan 或 machine-readable artifact，不再平行创建多个相互重叠的总计划。

## 7. Safety boundary

This audit is documentation-only:

```text
Production code changed          NO
Frozen manifest changed          NO
Model/result changed             NO
2025 Blind y accessed            NO
Market/raw licensed data changed NO
UI/runtime changed               NO
```
