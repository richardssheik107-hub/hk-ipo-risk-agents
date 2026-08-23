# Documentation Audit — 2026-08-23

## Scope

本轮审计覆盖当前仓库所有叙述性项目文档：

- 根目录 `README.md`；
- 根目录 `AGENTS.md`；
- 根目录 `CHANGELOG.md`；
- `docs/` 下全部手写项目文档；
- `docs/research/` 下全部研究 / contract 文档；
- completion report 与 frozen governance 文档的状态一致性和历史/当前语义。

`docs/annotation/gpt_expert_v1_1/` 是 governed annotation asset / case-packet 集合，不属于普通叙述性文档；本轮确认其目录边界但不批量改写 annotation 内容。

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
6. Competition plan 仍用历史 `PR-C → PR-H` 作为“当前”路径，需要改成“PR-E → PR-H”；PR-C / PR-D 只作为 frozen prerequisites。
7. `COMPETITION_DATA_OVERVIEW.md` 容易把 PR-B `432/438` EOD coverage 与 PR-C `424/438` target coverage 混为一谈。
8. 某些 frozen completion reports 的“next milestone / not started”是**冻结当日的历史下游状态**，需要显式标注，避免被误读为当前 Roadmap。

## Updated active documents

本轮重写 / 更新：

- `README.md`
- `docs/README.md`
- `docs/ROADMAP.md`
- `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
- `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- `docs/PROJECT_SPEC.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_SCHEMA.md`
- `docs/COMPETITION_DATA_OVERVIEW.md`
- `docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`
- `docs/research/V04_DATA_READINESS.md`
- `docs/research/V04_CANONICAL_MODELING_DATASET.md`
- `docs/research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`

## Completion / frozen record policy

Completion reports 的**测量结果、hash、source revision、当时 Gate verdict**保持历史事实，不因后续阶段推进而改写。只允许做不改变 frozen facts 的 editorial clarification，例如明确“下游状态为 freeze-time snapshot”或移除已经删除的临时 audit 文件引用。

本轮对 `V04_PR_C_COMPLETION_REPORT.md` 做了这种最小 editorial cleanup；PR-A / PR-B / PR-D / Oracle-v2 completion records 同样按该历史语义审计。

## Stable references reviewed and kept

以下文档继续保留，因为仍有 reproducibility / contract / future-research 价值：

- `V04_PR_A_COMPLETION_REPORT.md`
- `V04_PR_A_RUNBOOK.md`
- `V04_PR_B_COMPLETION_REPORT.md`
- `V04_PR_C_COMPLETION_REPORT.md`
- `V04_PR_D_COMPLETION_REPORT.md`
- `V04_ORACLE_V2_COMPLETION_REPORT.md`
- `V04_PR_D_INPUT_BINDING.md`
- `V04_ORACLE_REFRESH_GOVERNANCE.md`
- `research/V04_5D_OUTCOME_POLICY.md`
- `research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`
- `research/V04_MARKET_FOUNDATION.md`
- `research/V04_PRELISTING_MARKET_FEATURES.md`
- `research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`
- `research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`

Retriever 文档只约束未来 v0.5 重启研究，不是当前 v0.4 执行入口。

根目录 `AGENTS.md` 经审计，其 Evidence / architecture / blind / protected-interface 开发规则仍有效，不做无意义改写。`CHANGELOG.md` 是 release history，不用当前 v0.4 状态覆盖既有 v0.1/v0.2/v0.3 历史记录，因此保持不变。

## Removed obsolete documents

以下文件属于已结束阶段的 temporary handoff / preflight / one-off audit，删除后仍由 Git history 保留：

- `V04_C_P0_FILTERED_EOD_READINESS_REPORT.md`
- `V04_PR_A3_OFFLINE_RUNBOOK.md`
- `V04_PR_C_A_GATE_AUDIT.md`
- `V04_ROLE_A_CODEX_HANDOFF.md`
- `V04_ROLE_A_CROSS_TEAM_PREP.md`
- `V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`

删除原则：其关键冻结事实已经进入 completion report、frozen manifest 或长期 technical contract；继续留在当前文档树只会产生状态漂移。

## Documentation ownership rule

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
*_COMPLETION_REPORT.md        historical immutable measured-stage facts
reports/frozen/*.json         machine-readable frozen evidence
```

后续任何 Gate 完成后，只更新对应层；临时跨成员交接优先放 PR body / issue / package README，不再新增长期 `handoff_2` / `final_handoff` / `preflight_final` 类文档。

## Current next action after this audit

当前正式推进点仍然是 PR-E：消费 frozen PR-D Production matrices 和 frozen Oracle v2 features，使用 time-aware Development evaluation 与 untouched 2024 Validation，完成 M / P / PM 与 M / P / O / PM / OM baseline + Oracle diagnostic。

文档清理本身：

```text
DOES NOT start PR-E model training
DOES NOT modify frozen runtime artifacts
DOES NOT modify public Schema / Protocol
DOES NOT access 2025 Blind y
```
