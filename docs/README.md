# Documentation Index

> Status snapshot: **2026-08-21**  
> PR-A: **COMPLETE / FROZEN**  
> Current formal milestone: **PR-B — Market-X Core + Governed EOD Store**

本目录只把当前主线真正需要阅读的文档作为活文档维护。历史 v0.2 / v0.3 audit、旧 Retriever pilot、handoff 与一次性实验文档通过 Git history / release 保留。

## 1. Current execution chain

```text
Prospectus PDF
→ Document Intelligence
→ Production Document X
→ Pre-listing Market X
→ 5D Outcome
→ Model-ready Dataset
→ Baseline + Oracle Diagnostic
→ LightGBM + Explainability
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
```

正式 Gate / mainline merge 顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            CURRENT / NEXT
→ PR-C 5D Outcome Policy Freeze
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
```

准备性工作允许并行，但不得把准备工作描述为后续 Gate 已通过，也不得越过正式顺序合并到 `main`。

## 2. Read these first

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — 唯一权威总计划与 Gate 顺序；
2. [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) — 五人角色、并行准备和正式 Gate 边界；
3. [`V04_ROLE_A_CROSS_TEAM_PREP.md`](V04_ROLE_A_CROSS_TEAM_PREP.md) — A 在 PR-A 后如何提前帮助 B/C/D/E，以及哪些基础已经存在、不应重复实现；
4. [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — PR-B 的可执行 orchestration / PIT / coverage / provenance / determinism 验收契约；
5. [`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md) — 交给 Codex 的剩余实现队列与 stop condition；
6. [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md) — PR-A 冻结结果；
7. [`ROADMAP.md`](ROADMAP.md) — 阶段状态；
8. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、信任边界与成功标准；
9. [`ARCHITECTURE.md`](ARCHITECTURE.md) — 当前模块与依赖边界；
10. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 公共 Schema / v0.4 建模契约。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。

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

## 4. Current PR-B reality

The Market feature contract itself already exists and is frozen:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw features + 10 missing indicators = 20 positions
```

Existing foundations include the Pydantic Market feature schemas, deterministic `PreListingMarketFeatureEngine`, in-memory reference provider for tests, governed IPO OHLCV foundation, Market augmented dataset joins and blind feature-only export.

PR-B must now connect **real governed reference sources** and create canonical materialization/orchestration/audit around those foundations.

Current real source gaps:

```text
HSI daily history
industry → benchmark authoritative mapping
industry-index histories
HK total-market turnover
```

Detailed contract:

- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)

## 5. Active v0.4 research / contract docs

- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md) — IPO metadata, EOD, labels, split/blind foundation；
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md) — frozen 100-position Production Document contract and modeling join；
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — frozen 20-position PIT Market-X contract；
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — latest real data/source readiness；
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md) — Oracle evaluation-only path；
- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md) — frozen Retriever research reference, not current execution plan.

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

2025 in development may contain governed feature-only X after policy permits, but no 2025 y is used for feature/threshold/model/Retriever/LLM tuning before the blind evaluation is formally opened.

## 8. Documentation maintenance rule

- Current contracts / execution guidance → `docs/`;
- machine fixtures required by tests → keep only minimum needed;
- runtime/full-run outputs → ignored artifact/report area unless a small freeze manifest is deliberately committed;
- readiness numbers → update only after real runs;
- superseded plans → Git history/release, not active source of truth.

A new contributor should be able to answer within minutes: **where we are, what Gate is current, what already exists, what Codex/team should do next, and what cannot be crossed early.**
