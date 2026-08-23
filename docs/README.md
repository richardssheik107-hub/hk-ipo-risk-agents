# Documentation Index

> Status snapshot: **2026-08-23**
> PR-A: **COMPLETE / FROZEN**
> PR-B: **COMPLETE / FROZEN ON MAIN**
> PR-C: **COMPLETE / FROZEN**
> PR-D: **COMPLETE / FROZEN**
> PR-E: **READY — FORMAL BASELINE NEXT / NOT STARTED**
> Competition track: **PLANNED AFTER PR-H BASELINE E2E — full scope frozen in `COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`**
> Latest A integration handoff: [`V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`](V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md)

本目录只把当前主线真正需要阅读的文档作为活文档维护。历史 v0.2 / v0.3 audit、旧 Retriever pilot、Role-A handoff 与一次性实验文档通过 Git history / release 保留。

## 1. Current execution chain

```text
Prospectus PDF
→ Document Intelligence
→ Production Document X
→ Market-X Core + optional governed Extended Market-X
→ 5D Outcome
→ Model-ready Dataset
→ Baseline + Oracle Diagnostic
→ LightGBM + Explainability
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
→ Baseline E2E Freeze
→ Competition Hardening
→ Competition Submission Freeze
```

正式 Gate / mainline merge 顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze                      COMPLETE / FROZEN
→ PR-D Canonical Model-ready Dataset                 COMPLETE / FROZEN
→ PR-E Baseline + Oracle Diagnostic                  READY / FORMAL BASELINE NEXT / NOT STARTED
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
→ v0.4.3 Baseline E2E Freeze
→ CH-0..CH-6 Competition Hardening
→ v0.4.5 COMPETITION_READY
```

准备性工作允许并行，但不得把准备工作描述为后续 Gate 已通过，也不得越过正式顺序合并到 `main`。赛题专项强化在 PR-H baseline E2E 跑通后正式启动，不是当前 PR-C Gate 的前置条件。

## 2. Read these first

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — 唯一权威总计划与 Gate 顺序；
2. [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) — 五人角色、并行准备和正式 Gate 边界；
3. [`ROADMAP.md`](ROADMAP.md) — 当前阶段状态与后续严格顺序；
4. [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) — PR-H baseline E2E 之后的赛题全量 requirement / owner / metric / deliverable / submission Gate；
5. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、信任边界与成功标准；
6. [`ARCHITECTURE.md`](ARCHITECTURE.md) — 当前模块与依赖边界；
7. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 公共 Schema / v0.4 建模契约；
8. [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 最新真实数据/source readiness；
9. [`V04_PR_C_A_GATE_AUDIT.md`](V04_PR_C_A_GATE_AUDIT.md) — PR-C 424/14 A-side Gate audit 与最后正式执行条件；
10. [`V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md`](V04_ROLE_A_INTEGRATION_GATE_HANDOFF.md) — PR-D integration Gate、Oracle identity 决策和 PR-G contract review；
11. [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md) — PR-B 冻结实测结果；
12. [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — PR-B frozen acceptance contract / reproducibility reference；
13. [`V04_PR_C_COMPLETION_REPORT.md`](V04_PR_C_COMPLETION_REPORT.md) — PR-C governed 438-case outcome materialization、threshold、determinism 与 freeze sign-off；
14. [`V04_ORACLE_REFRESH_GOVERNANCE.md`](V04_ORACLE_REFRESH_GOVERNANCE.md) — immutable PR-A Oracle v1、planned v2 refresh、annotation QA 与 PR-E 使用边界；
15. [`V04_PR_D_INPUT_BINDING.md`](V04_PR_D_INPUT_BINDING.md) — PR-D 三层 provenance binding、aggregate hash 算法与 P0 fail-closed Gate；
16. [`V04_PR_D_COMPLETION_REPORT.md`](V04_PR_D_COMPLETION_REPORT.md) — formal 438→424+14 materialization、354/70 split、resume 与 freeze sign-off；
14. [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md) — PR-A 冻结结果。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。`V04_ROLE_A_CROSS_TEAM_PREP.md` 与 `V04_ROLE_A_CODEX_HANDOFF.md` 仅保留为历史审计记录，不再作为当前执行入口。

## 3. PR-A frozen facts

```text
Official 2020–2024 cases       438
Production analysis            438 / 438
Authoritative snapshots        438 / 438
Production Document-X          438 / 438
Document feature schema        v04_document_features_v1
Document feature dimension     100
Production failures            0
Silent drops                   0
Oracle materialized            60
No reviewed Gold               378
Production ∩ Oracle            60
A6 checked                     438
A6 mismatches                  0
2025 blind access              NO
```

Frozen records:

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

## 4. PR-B frozen result

PR-B is now explicitly split into **Core** and **Extended**.

### 4.1 Market-X Core — COMPLETE / FROZEN

Current Core contract:

```text
v04_ipo_market_context_features_v1
ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Core only uses information already governed and historically available before each target listing:

```text
authoritative IPO identity / listing date
prior-IPO offer/context facts
governed IPO EOD
prior IPO 1D/5D outcomes only after their target sessions occurred before target listing
```

Implemented entry points:

```text
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

The governed EOD builder selects the cohort by authoritative `official_listed_date.year`, preserves `OBJECT_ID` provenance, and records that `S_DQ_AMOUNT` is per-security only.

Measured freeze evidence:

```text
official coverage              438 / 438
Core materialized              438 / 438
failed / silent drops          0 / 0
PIT failures                   0
Development / Validation       368 / 70
determinism                    438 checked / 0 mismatches / PASS
full pytest                    1303 passed / 0 failed / 2 warnings
2025 blind y accessed          NO
```

Frozen records:

- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_b_market_x_core_manifest.json`](../reports/frozen/v04_pr_b_market_x_core_manifest.json)

### 4.2 Market-X Extended — frozen contract, governed sources still missing

Existing Extended contract remains unchanged:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw + 10 missing indicators = 20 positions
```

Current real Extended source gaps:

```text
HSI daily history
industry → benchmark authoritative mapping
industry-index histories
HK total-market turnover
```

These gaps remain explicit. They are not a PR-B Core failure and cannot be filled with ungoverned proxies, fake benchmark rows or neutral zero.

Detailed contracts:

- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)

## 5. Active v0.4 research / contract docs

- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md) — IPO metadata, EOD, labels, split/blind foundation；
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md) — frozen 100-position Production Document contract and existing modeling joins；
- [`research/V04_5D_OUTCOME_POLICY.md`](research/V04_5D_OUTCOME_POLICY.md) — PR-C 5D raw/binary target policy, Blind boundary and formal materialization Gate；
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — frozen 20-position **Extended** PIT Market-X contract；
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — latest measured data/source readiness；
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md) — Oracle evaluation-only path；
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — frozen PR-B Core/Extended acceptance and reproducibility contract；
- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md) — frozen Retriever research reference, not current execution plan；
- [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) — baseline E2E 完成后的赛题专项增强与最终提交验收。

## 6. Production / Oracle separation

Production:

```text
Prospectus
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Skills
→ Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document X
```

Oracle:

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document X
```

Oracle is evaluation-only. It cannot enter Production runtime, cannot leak Gold page/Evidence ID/manual answers into Production X, and cannot use 2025 blind y.

## 7. Time governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 may eventually contain governed feature-only X after policy permits, but no 2025 y is used for feature/threshold/model/Retriever/LLM tuning before the blind evaluation is formally opened。Competition Hardening 不自动授权打开 2025 y。

## 8. Current stop condition

PR-C 已完成 governed materialization、deterministic resume、freeze validator 与 A final sign-off：

```text
PR-A  COMPLETE / FROZEN
→ PR-B COMPLETE / FROZEN ON MAIN
→ PR-C COMPLETE / FROZEN
     438 coverage
     424 available / 14 unavailable
     Development q25 = -0.1000
     438 determinism / 0 mismatch
→ PR-D COMPLETE / FROZEN
```

PR-C 的真实 Development-only q25、438 target artifacts、424/14 coverage、438/0 determinism 与 small freeze manifest 已完成并冻结，详见 `V04_PR_C_COMPLETION_REPORT.md`。

PR-D 已在 `main@a1385dba...` 上正式完成 materialization：438 upstream、424 model-ready、14 explicit exclusions、354 Development、70 Validation；三层 binding、same-provenance resume 和冻结清单均通过。PR-E formal baseline 已解锁但尚未开始。

## 9. Post-baseline Competition Hardening

PR-H baseline E2E 通过以后，项目不立即做无边界的模型/Prompt优化，而是按 [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md) 逐项补齐赛题明确要求：

```text
1D / 5D / 20D / 60D outcome validation（5D primary）
现金消耗 / 对赌赎回 / 关联交易 / 集中度 / 核心管线专项
文本粉饰度原文 diagnostic
市场情绪 Agent + 同行估值 / 情绪热度 Skills
Agent conflict detection / re-check / arbitration
关键风险抽取准确率 >= 80%
Evidence recall >= 85%
Agent / Tool / Evidence traceability = 100%
PDF page / paragraph / bbox screenshot
human review
prediction table / reasoning logs / evidence / case report submission package
```

只有完成该计划的 Submission Freeze Gate 才标记 `COMPETITION_READY`。

## 10. Documentation maintenance rule

- Current contracts / execution guidance → `docs/`；
- machine fixtures required by tests → keep only minimum needed；
- runtime/full-run outputs → ignored artifact/report area unless a small freeze manifest is deliberately committed；
- readiness numbers → update only after real runs；
- superseded plans / handoffs → Git history/release 或明确标记 historical，不作为当前 source of truth。

A new contributor should be able to answer within minutes: **where we are, what Gate is next, what is already frozen, what remains blocked by the next Gate, what competition work comes after baseline E2E, and what cannot be crossed early.**
