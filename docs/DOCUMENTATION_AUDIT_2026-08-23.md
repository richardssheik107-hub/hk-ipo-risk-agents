# Documentation Audit — 2026-08-23

## Scope

本轮审计覆盖：

- 根目录 `README.md`；
- `docs/` 下所有手写项目文档；
- `docs/research/` 下所有研究 / contract 文档；
- completion report 与 frozen governance 文档的状态一致性。

`docs/annotation/gpt_expert_v1_1/` 是 governed annotation asset / case packet 集合，不属于普通叙述性文档，本轮不改写其内容。

## Current authoritative state

```text
PR-A  COMPLETE / FROZEN
PR-B  COMPLETE / FROZEN
PR-C  COMPLETE / FROZEN
PR-D  COMPLETE / FROZEN
Oracle v2 COMPLETE / FROZEN / EVALUATION-ONLY
PR-E  CURRENT FORMAL GATE
PR-F  WAITING PR-E
PR-G  WAITING PR-F
PR-H  WAITING PR-G
Competition Hardening STARTS AFTER PR-H BASELINE E2E
```

Measured anchors：

```text
Official cases                     438
Production Document-X              438 / 438 / 100 dims
Market-X Core                      438 / 438 / 30 positions
5D outcome available               424
Explicit exclusions                 14
Canonical dataset                  424 = 354 Dev + 70 Val
Oracle v2                           98 materialized / 96 strict usable
Oracle v2 split                     77 Dev / 19 Val
2025 Blind y accessed              false
```

## Main findings

1. 多份文档顶部已经写成 PR-D COMPLETE，但正文仍残留“PR-D formal materialization next / not complete”。
2. `V04_DATA_READINESS.md` 与 `V04_CANONICAL_MODELING_DATASET.md` 仍停在 PR-D 前状态。
3. Oracle research 文档仍以 Oracle v1 60-case 路径为主，未把 v2 98/96/77/19 作为当前正式 ceiling。
4. Role-A handoff / preflight / one-off readiness 文档在对应 Gate 冻结后仍留在当前索引，造成“历史任务看起来像当前任务”。
5. 根 README、docs index、Roadmap、Master Plan、Five-person Plan 重复维护大量同一状态，且个别段落不同步。
6. Competition plan 仍用历史 `PR-C → PR-H` 作为“当前”路径，需要改成“PR-E → PR-H”；PR-C/PR-D 仅作为 frozen prerequisites。

## Updated active documents

本轮将以下文档重写或更新为当前统一口径：

- `README.md`
- `docs/README.md`
- `docs/ROADMAP.md`
- `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
- `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- `docs/PROJECT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_SCHEMA.md`
- `docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`
- `docs/research/V04_DATA_READINESS.md`
- `docs/research/V04_CANONICAL_MODELING_DATASET.md`
- `docs/research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`

## Frozen references kept unchanged

以下文档记录 frozen fact / policy，不因当前 Gate 推进而改写历史事实：

- `V04_PR_A_COMPLETION_REPORT.md`
- `V04_PR_B_COMPLETION_REPORT.md`
- `V04_PR_C_COMPLETION_REPORT.md`
- `V04_PR_D_COMPLETION_REPORT.md`
- `V04_ORACLE_V2_COMPLETION_REPORT.md`
- `V04_PR_A_RUNBOOK.md`
- `V04_PR_D_INPUT_BINDING.md`
- `V04_ORACLE_REFRESH_GOVERNANCE.md`
- `research/V04_5D_OUTCOME_POLICY.md`
- `research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`
- `research/V04_MARKET_FOUNDATION.md`
- `research/V04_PRELISTING_MARKET_FEATURES.md`
- `research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`
- `research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`
- `COMPETITION_DATA_OVERVIEW.md`

其中 Retriever 文档仅作为未来 v0.5 重启研究的约束记录，不是当前 v0.4 执行入口。

## Removed obsolete documents

以下文档属于已结束阶段的临时 handoff / preflight / one-off audit，删除后仍可由 Git history 追溯：

- `V04_C_P0_FILTERED_EOD_READINESS_REPORT.md`
- `V04_PR_A3_OFFLINE_RUNBOOK.md`
- `V04_PR_C_A_GATE_AUDIT.md`
- `V04_ROLE_A_CODEX_HANDOFF.md`
- `V04_ROLE_A_CROSS_TEAM_PREP.md`
- `V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`

删除原则：其关键冻结事实已经进入 completion report、frozen manifest 或长期技术 contract；继续保留在当前文档树只会产生状态漂移。

## New documentation ownership rule

```text
README.md                     project overview only
docs/README.md                document index / source-of-truth only
ROADMAP.md                    current status + next Gate only
MASTER_PLAN.md                end-to-end sequence / governance only
FIVE_PERSON_EXECUTION_PLAN.md roles / active assignments only
PROJECT_SPEC.md               product semantics / success criteria only
ARCHITECTURE.md               module dependency / runtime boundaries only
DATA_SCHEMA.md                cross-module contracts only
V04_DATA_READINESS.md         measured data facts only
*_COMPLETION_REPORT.md        immutable completed-stage facts
reports/frozen/*.json         machine-readable frozen evidence
```

后续任何 Gate 完成后，只更新上述对应层，不再新增新的 `handoff_2` / `final_handoff` / `preflight_final` 类文档。

## Current next action after this audit

当前正式推进点仍然是 PR-E：消费 frozen PR-D Production matrices 和 frozen Oracle v2 features，使用 time-aware Development evaluation 与 untouched 2024 Validation，完成 M / P / PM 与 M / P / O / PM / OM baseline + Oracle diagnostic。文档清理本身不开始模型训练，也不改变任何 frozen data/model contract。
