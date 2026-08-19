# Documentation Index

> Status snapshot: **2026-08-19**

本目录只把**当前主线开发真正需要阅读的文档**作为活文档维护。历史 v0.2 / v0.3 审计、handoff、旧 Retriever pilot 和一次性执行稿通过 Git history / release 保留，不继续堆在当前阅读路径。

## 当前主线

项目当前执行策略为 **End-to-End Closed Loop First**：

```text
Prospectus PDF
→ Document Intelligence
→ Production Document Features
→ Pre-IPO Market Features
→ 5D Outcome
→ Model-ready Dataset
→ Baseline + Oracle Diagnostic
→ LightGBM
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
```

当前唯一执行里程碑：

> **PR-A — Document + Oracle Materialization & Coverage**

CL-1 的 Document Intelligence freeze 已完成。当前不继续优化 Retriever、Prompt、LLM 或 Agent，而是先把现有系统在 2020–2024 官方 438-case universe 上变成可审计、可重建的建模数据资产。

## 文档优先级

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — **唯一权威执行总计划**，包含 PR-A 的具体步骤与 Gate；
2. [`ROADMAP.md`](ROADMAP.md) — 当前阶段状态、下一里程碑；
3. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、范围、信任边界与成功标准；
4. [`ARCHITECTURE.md`](ARCHITECTURE.md) — 模块边界与系统架构；
5. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 公共 Schema 与跨模块数据契约；
6. [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) — 赛事数据宇宙、年度切分与数据治理。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。

## v0.4 当前工作文档

- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 最近一次真实数据 readiness 审计；
- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md) — 市场数据、标签、年度切分和 blind 治理基础；
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md) — Production Document Risk → 模型特征契约；
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — 严格上市前 Market X 契约；
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md) — evaluation-only 的专家 Gold 上限建模路径。

## 当前两条 Document 路径

### Production

```text
Prospectus
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Skills
→ Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document Features
```

Production 路径是真正进入最终产品的路径，不依赖专家答案。

### Oracle

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document Features
```

Oracle 只用于研究上限和错误归因，不进入生产 runtime，不读取 2025 blind y，也不能把专家答案泄漏进 Production X。

## 当前 PR-A 要做什么

PR-A 不是“再优化一次 Agent”，而是回答四个最基础的问题：

```text
1. 438 个官方 2020–2024 IPO 中，Production Document X 成功多少？
2. 哪些失败或降级？具体失败在哪一阶段、为什么？
3. Oracle Gold 实际可 materialize 多少？
4. Production 与 Oracle 的公平交集有多少？
```

当前底层能力已经存在：

- `scripts/run_v03_batch_analysis.py` — Production batch analysis；
- `src/ipo_risk/modeling/materialization.py` — authoritative snapshot boundary；
- `src/ipo_risk/modeling/features.py` — frozen Production feature manifest / vectorizer；
- `scripts/index_oracle_gold.py` — Oracle eligibility / provenance inventory；
- `scripts/build_oracle_document_features.py` — Oracle feature materialization。

当前缺少的是一个**PR-A 统一执行入口**。Master Plan 已冻结首个代码 deliverable：

```text
scripts/run_v04_pr_a.py
```

它必须是薄 orchestration CLI，只串联既有模块，不把 Parser / Retriever / Agent 业务逻辑复制进去。

## PR-A 的严格顺序

```text
PR-A0  Freeze execution context and hashes
PR-A1  Implement scripts/run_v04_pr_a.py + tests
PR-A2  Run small deterministic Development pilot
PR-A3  Run 2020–2024 Production materialization
PR-A4  Run Oracle materialization
PR-A5  Build unified coverage table
PR-A6  Rerun and verify deterministic hashes
```

只有 PR-A PASS 后才进入 PR-B Market-X Core。

## 当前真实 readiness 不变

计划文档更新不等于数据已经重新跑过。当前数字继续以 `V04_DATA_READINESS.md` 为准：

- official universe：438 / 438；
- local prospectus：438 / 438；
- IPO OHLCV：432 / 438；
- authoritative snapshots：最近一次真实 audit 时 0 / 438；
- HSI / industry benchmark / total-market turnover：仍缺失。

这些数字只有在真实 materialization / source audit 后才允许更新。

## 时间治理

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在 feature / target / model policy 冻结前不得用于选特征、阈值、模型或 Prompt / Retriever / LLM 调优。

## 冻结研究参考

- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md)

Retriever V3 / BM25 / Table / LambdaMART 等成果已进入主线历史并冻结。历史 Locked 10 已消费；未来若重启 Retriever，必须建立新的 unseen / external / temporal holdout。

## 文档维护规则

- **长期契约 / 当前执行指引**：进入 `docs/`；
- **运行时 / 测试夹具**：进入适当数据或 fixture 路径；
- **阶段性实验结果**：进入可版本化 report / artifact；
- **一次性 handoff / 临时计划**：完成后不长期保留为活文档；
- **真实 readiness 数字**：只有真实运行后更新；
- **已被新版本替代的说明**：从当前树移除，由 Git history 保存。

目标是让任何新成员进入 `docs/` 后几分钟内就能回答：**现在做到哪里、下一步只做什么、哪些边界不能破坏。**
