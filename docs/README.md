# Documentation Index

> Audit date: **2026-08-23**  
> Current formal Gate: **PR-G — Market Agent + Final Supervisor**
> PR-A / PR-B / PR-C / PR-D: **COMPLETE / FROZEN**  
> Oracle v2 / PR-E / PR-F: **COMPLETE / FROZEN**

本目录采用“**少量活文档 + 冻结完成记录 + 技术契约**”的维护方式，避免阶段推进后旧 handoff / readiness / preparation 文档继续制造口径冲突。

## 1. Source-of-truth hierarchy

发生口径冲突时，按以下优先级判断：

1. 代码中的 Pydantic / Protocol / validator；
2. `reports/frozen/*.json` 冻结 manifest；
3. 对应阶段的 `*_COMPLETION_REPORT.md`；
4. 当前活文档；
5. 历史研究文档 / Git history。

旧 planning / handoff 文档不能覆盖已经冻结的 manifest 或 completion report。

## 2. Active documents — 当前维护

| 文档 | 作用 |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | 当前进度、唯一下一 Gate、后续顺序 |
| [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) | v0.4 baseline E2E 总计划与 post-PR-F 战略 |
| [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) | A/B/C/D/E 角色边界与当前任务 |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | 产品目标、信任边界、成功标准 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 模块、依赖、Production / Oracle 隔离 |
| [`DATA_SCHEMA.md`](DATA_SCHEMA.md) | 公共数据与 v0.4 modeling contracts |
| [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) | 最新真实数据 readiness |
| [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) | PR-H baseline E2E 后的 CH-0..CH-6 |

## 3. Frozen completion records — 只记录已完成事实

这些文档不作为“当前待办”，而是冻结阶段的审计证据：

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- [`V04_PR_C_COMPLETION_REPORT.md`](V04_PR_C_COMPLETION_REPORT.md)
- [`V04_PR_D_COMPLETION_REPORT.md`](V04_PR_D_COMPLETION_REPORT.md)
- [`V04_PR_E_COMPLETION_REPORT.md`](V04_PR_E_COMPLETION_REPORT.md)
- [`V04_PR_F_COMPLETION_REPORT.md`](V04_PR_F_COMPLETION_REPORT.md)
- [`V04_ORACLE_V2_COMPLETION_REPORT.md`](V04_ORACLE_V2_COMPLETION_REPORT.md)
- [`V04_PR_D_INPUT_BINDING.md`](V04_PR_D_INPUT_BINDING.md)
- [`V04_ORACLE_REFRESH_GOVERNANCE.md`](V04_ORACLE_REFRESH_GOVERNANCE.md)

对应 frozen manifests 位于 `reports/frozen/`。

## 4. Stable technical / research references

以下文档仍有长期技术价值，但不是当前执行入口：

- [`V04_PR_A_RUNBOOK.md`](V04_PR_A_RUNBOOK.md) — PR-A frozen reproducibility reference
- [`research/V04_5D_OUTCOME_POLICY.md`](research/V04_5D_OUTCOME_POLICY.md) — frozen PR-C policy
- [`research/V04_CANONICAL_MODELING_DATASET.md`](research/V04_CANONICAL_MODELING_DATASET.md) — frozen PR-D canonical contract
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md)
- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md)
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md) — targeted restart constraints only
- [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md)

## 5. Current execution chain

```text
PR-A Document X                     COMPLETE / FROZEN
→ PR-B Market-X Core                COMPLETE / FROZEN
→ PR-C 5D Outcome Y                 COMPLETE / FROZEN
→ PR-D Canonical Dataset            COMPLETE / FROZEN
→ PR-E Baseline + Oracle Diagnostic COMPLETE / FROZEN
→ PR-F LightGBM + Explainability    COMPLETE / FROZEN
→ PR-G Market Agent + Final Supervisor CURRENT FORMAL GATE
→ PR-H Streamlit Full E2E
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 Competition Submission Freeze
```

## 6. Current measured facts

```text
Official 2020–2024 cases           438
Production Document-X              438 / 438, 100 dims
Market-X Core                      438 / 438, 30 positions
5D outcome available               424 / 438
Canonical model-ready              424 = 354 Dev + 70 Val
Oracle v1                          historical immutable: 60 materialized
Oracle v2                          98 materialized / 96 strict usable
Oracle v2 split                    77 Dev / 19 Val
2025 Blind y accessed              NO
```

PR-F frozen 2024 Full Production classification：`M ROC-AUC 0.4246`、`P 0.5000`、`PM 0.4246`。该结果保留为诚实 baseline；不能通过查看 2024 后反转 score、继续调参或重写口径来制造更高正式结果。

## 7. Current strategic interpretation

PR-E / PR-F 没有验证出稳定 Document 增量，也没有验证出稳定 Oracle ceiling。因此当前既不宣布“招股书无信号”，也不直接启动大规模 LLM 重构。

现行策略：

```text
PR-G / PR-H
→ 先完成 Document + Market + Model + Evidence + uncertainty 产品闭环

PR-H freeze 后
→ CH-1 multi-horizon
→ CH-2 direct risk / Evidence benchmark
→ CH-3 Market Sentiment
→ CH-4 trace / conflict
→ CH-5 screenshot / human review
→ CH-6 formal competition evaluation
```

Document enhancement 由 CH-2 的 Precision / Recall / F1 / Evidence Recall 与 error attribution 触发；短期 1D / 5D 预测增强优先在 CH-3 研究 point-in-time Market Sentiment / IPO context。Competition 目标不能简化成单一 5D AUC。

## 8. Documentation lifecycle rule

阶段性 handoff、preflight、temporary readiness 和 one-off audit 文档在对应正式 Gate 冻结后应删除，历史通过 Git history 保留；只有仍约束未来决策的研究结论保留在 `docs/research/`。

`docs/annotation/gpt_expert_v1_1/` 属于 governed annotation asset，不按普通叙述性文档清理，也不在本次文档去重中改写。

完整前一轮清理记录见 [`DOCUMENTATION_AUDIT_2026-08-23.md`](DOCUMENTATION_AUDIT_2026-08-23.md)。
