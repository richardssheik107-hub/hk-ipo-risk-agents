# Documentation Index

> Audit date: **2026-08-25**  
> PR-A–PR-G: **COMPLETE / FROZEN**  
> Current formal Gate: **PR-H PARTIAL / BLOCKED**  
> Next release: **v0.4.3 Baseline E2E Freeze**

本目录采用“**少量活文档 + 冻结完成记录 + 稳定技术/研究参考**”的维护方式。阶段性 handoff、临时 readiness、过期 runbook 在其事实已进入 completion report / frozen manifest / active plan 后删除，历史保留在 Git history。

## 1. Source-of-truth hierarchy

发生冲突时，按以下优先级判断：

1. 代码中的 Pydantic / Protocol / validator；
2. `reports/frozen/*.json`；
3. 对应 `*_COMPLETION_REPORT.md` / formal Gate review；
4. 当前 active docs；
5. research reference / Git history。

Active planning 不改写 frozen historical facts；historical completion report 也不决定“当前下一 Gate”。

## 2. Active documents

| Document | Purpose |
| --- | --- |
| [`ROADMAP.md`](ROADMAP.md) | 当前 Gate、里程碑、压缩时间线 |
| [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) | baseline → competition 的总策略 |
| [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) | A/B/C/D/E 从现在到提交的协同分工 |
| [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) | CH-0..CH-6、Beta、submission 完整验收计划 |
| [`PROJECT_SPEC.md`](PROJECT_SPEC.md) | 产品目标、范围、信任边界、Definition of Done |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 运行时、数据、模型、Competition layers 的依赖边界 |
| [`DATA_SCHEMA.md`](DATA_SCHEMA.md) | frozen baseline 与 planned versioned competition contracts |
| [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) | 原始赛事数据宇宙与数据治理 |
| [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) | 当前 measured readiness |
| [`UI_DESIGN_REFERENCE_2026-08-24.md`](UI_DESIGN_REFERENCE_2026-08-24.md) | CH-5 产品设计参考，不作为当前 Gate |

## 3. Current execution chain

```text
PR-A Document-X                     COMPLETE / FROZEN
→ PR-B Market-X Core                COMPLETE / FROZEN
→ PR-C 5D Outcome                   COMPLETE / FROZEN
→ PR-D Canonical Dataset            COMPLETE / FROZEN
→ Oracle v2                         COMPLETE / FROZEN / EVALUATION-ONLY
→ PR-E Baseline + Oracle            COMPLETE / FROZEN
→ PR-F LightGBM + Explainability    COMPLETE / FROZEN
→ PR-G Market Agent + Supervisor    COMPLETE / FROZEN
→ PR-H Full E2E                     PARTIAL / BLOCKED
→ v0.4.3 Baseline Freeze
→ CH-0..CH-6 Competition Hardening
→ Competition Beta
→ v0.4.5 COMPETITION_READY
→ Submission
```

## 4. Completion / Gate records — keep immutable as historical evidence

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- [`V04_PR_C_COMPLETION_REPORT.md`](V04_PR_C_COMPLETION_REPORT.md)
- [`V04_PR_D_COMPLETION_REPORT.md`](V04_PR_D_COMPLETION_REPORT.md)
- [`V04_PR_E_COMPLETION_REPORT.md`](V04_PR_E_COMPLETION_REPORT.md)
- [`V04_PR_F_COMPLETION_REPORT.md`](V04_PR_F_COMPLETION_REPORT.md)
- [`V04_PR_G_COMPLETION_REPORT.md`](V04_PR_G_COMPLETION_REPORT.md)
- [`V04_PR_G_A_GATE_REVIEW.md`](V04_PR_G_A_GATE_REVIEW.md)
- [`V04_PR_H_COMPLETION_REPORT.md`](V04_PR_H_COMPLETION_REPORT.md) — current formal blocker record
- [`V04_ORACLE_V2_COMPLETION_REPORT.md`](V04_ORACLE_V2_COMPLETION_REPORT.md)

## 5. Stable governance / technical references

Keep because they contain durable contracts or evidence not duplicated by the active plan:

- [`V04_PR_D_INPUT_BINDING.md`](V04_PR_D_INPUT_BINDING.md)
- [`V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md`](V04_PR_G_FINAL_SUPERVISOR_CONTRACT.md)
- [`V04_ORACLE_REFRESH_GOVERNANCE.md`](V04_ORACLE_REFRESH_GOVERNANCE.md)
- [`V04_ORACLE_GOLD_COVERAGE_AUDIT.md`](V04_ORACLE_GOLD_COVERAGE_AUDIT.md)
- [`V04_C_HSI_SOURCE_INTEGRATION_REPORT.md`](V04_C_HSI_SOURCE_INTEGRATION_REPORT.md)
- [`research/V04_5D_OUTCOME_POLICY.md`](research/V04_5D_OUTCOME_POLICY.md)
- [`research/V04_CANONICAL_MODELING_DATASET.md`](research/V04_CANONICAL_MODELING_DATASET.md)
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md)
- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md)
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md) — only if CH-2 justifies reopening retrieval research

## 6. Current measured facts

```text
Official cases                        438
Production Document-X                 438 / 438, 100 dims
Market-X Core                         438 / 438, 30 positions
5D outcome                            424 / 438
Canonical                             424 = 354 Dev + 70 Val
Oracle v2 strict                      96 = 77 Dev + 19 Val
HSI Extended readiness                438 / 438
HKEX turnover 20D readiness           438 / 438
production industry return              0 / 438, PIT_BLOCKED
2025 Blind y accessed                 NO
```

## 7. Current interpretation

PR-F Full Production 2024: `M 0.4246 / P 0.5000 / PM 0.4246 ROC-AUC`; Production PM=M under the frozen LightGBM policy. This is a weak predictive baseline, not an engineering failure and not proof that prospectus information has no value.

Next research order is deliberate:

```text
Document benchmark
→ feature representation audit
→ 1D/5D/20D/60D diagnosis
→ IPO-specific Market Intelligence
→ only then decide whether Retriever / LLM / model family must change
```

## 8. Documentation lifecycle rule

Delete a document when all are true:

1. it is a one-off handoff / preflight / execution note;
2. its stage is complete or its findings are superseded;
3. durable facts already exist in code, frozen manifest, completion report or active plan;
4. no unique future governance constraint would be lost.

Do **not** bulk-delete completion reports, frozen governance records, annotation assets or research references solely because their stage is old.

Current cleanup decisions are recorded in [`DOCUMENTATION_AUDIT_2026-08-25.md`](DOCUMENTATION_AUDIT_2026-08-25.md).

`docs/annotation/gpt_expert_v1_1/` is governed annotation data and is not treated as narrative documentation cleanup scope.
