# Documentation Index

> Status snapshot: **2026-08-21**
> PR-A: **COMPLETE / FROZEN**
> PR-B: **COMPLETE / FROZEN ON MAIN**
> Next formal milestone: **PR-C — 5D Outcome Policy Freeze / NOT STARTED**
> PR-B materialization source revision: **`dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7`**
> PR-B mainline publication: **PR #80**, post-merge documentation closure: **PR #81 / `2675646c359a0138080960c916e8ef526c085c88`**

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
```

正式 Gate / mainline merge 顺序：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze                      NEXT / NOT STARTED
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
3. [`ROADMAP.md`](ROADMAP.md) — 当前阶段状态与后续严格顺序；
4. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、信任边界与成功标准；
5. [`ARCHITECTURE.md`](ARCHITECTURE.md) — 当前模块与依赖边界；
6. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 公共 Schema / v0.4 建模契约；
7. [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 最新真实数据/source readiness；
8. [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md) — PR-B 冻结实测结果；
9. [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — PR-B frozen acceptance contract / reproducibility reference；
10. [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md) — PR-A 冻结结果。

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
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — frozen 20-position **Extended** PIT Market-X contract；
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — latest measured data/source readiness；
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md) — Oracle evaluation-only path；
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — frozen PR-B Core/Extended acceptance and reproducibility contract；
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

2025 may eventually contain governed feature-only X after policy permits, but no 2025 y is used for feature/threshold/model/Retriever/LLM tuning before the blind evaluation is formally opened.

## 8. Current stop condition

PR-B 已经完成、冻结并发布到 `main`。当前不需要继续维护 PR-B 工作分支，也不需要重复 pilot / full-run / determinism；除非出现明确的数据泄漏、冻结资产错误或不可复现问题，PR-B 不再重开。

下一允许进入的正式 milestone 是 PR-C，但它尚未启动：

```text
PR-A  COMPLETE / FROZEN
→ PR-B COMPLETE / FROZEN ON MAIN
→ STOP
→ PR-C NEXT / NOT STARTED
```

PR-C classification threshold 和 target policy 必须使用 Development 数据单独冻结；在获得独立 PR-C 任务授权前，不选择最终阈值、不读取 2025 y、不训练正式模型。

## 9. Documentation maintenance rule

- Current contracts / execution guidance → `docs/`；
- machine fixtures required by tests → keep only minimum needed；
- runtime/full-run outputs → ignored artifact/report area unless a small freeze manifest is deliberately committed；
- readiness numbers → update only after real runs；
- superseded plans / handoffs → Git history/release 或明确标记 historical，不作为当前 source of truth。

A new contributor should be able to answer within minutes: **where we are, what Gate is next, what is already frozen, what remains blocked by the next Gate, and what cannot be crossed early.**
