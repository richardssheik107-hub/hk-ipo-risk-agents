# Documentation Index

> Status snapshot: **2026-08-20**

本目录只把**当前主线开发真正需要阅读的文档**作为活文档维护。历史 v0.2 / v0.3 审计、handoff、旧 Retriever pilot、旧 Evidence Intelligence 设计稿和一次性执行稿通过 Git history / release 保留，不继续堆在当前阅读路径。

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

CL-1 Document Intelligence freeze 已完成。当前不继续优化 Retriever、Prompt、LLM 或 Agent，而是先把现有系统在 2020–2024 official 438-case universe 上变成可审计、可重建的建模数据资产。

## 文档优先级

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — **唯一权威执行总计划**，包含 PR-A 的步骤与 Gate；
2. [`ROADMAP.md`](ROADMAP.md) — 当前阶段状态、下一里程碑；
3. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、范围、信任边界与成功标准；
4. [`ARCHITECTURE.md`](ARCHITECTURE.md) — **当前架构**，旧 v0.2 / v0.3 设计历史已移除；
5. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 当前公共 Schema 与 v0.4 建模契约说明；
6. [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) — 原始赛事语料与 v0.4 official modeling cohort 的区别。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。

## v0.4 当前工作文档

- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 最近一次真实 readiness 审计；PR-A ready 与 full model-ready blocked 的区别；
- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md) — 市场数据、标签、年度切分和 blind 治理基础；
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md) — Production Document Risk → 模型特征契约；
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — 严格上市前 Market X 契约与当前真实数据可用性；
- [`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md) — evaluation-only 的专家 Gold 上限 / 错误归因路径。

## 冻结研究参考

- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md)

Retriever V3 / BM25 / Table / LambdaMART 等成果已进入主线并冻结。历史 Locked 10 已消费；未来若重启 Retriever，必须建立新的 unseen / external / temporal holdout。

该文件**不是当前执行计划**，保留它只是因为其中的数据治理和未来重启条件仍有约束力。

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

Production 是最终产品路径，不依赖专家答案。

### Oracle

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document Features
```

Oracle 只用于研究上限和错误归因，不进入 production runtime，不读取 2025 blind y，也不能把专家答案泄漏进 Production X。

## 当前 PR-A 要做什么

PR-A 不是“再优化一次 Agent”，而是回答四个基础问题：

```text
1. 438 个 official 2020–2024 IPO 中，Production Document X 成功多少？
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

当前缺少的是一个**PR-A 统一执行入口**：

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

## 当前真实 readiness

计划文档更新不等于数据已经重新跑过。当前数字继续以 `research/V04_DATA_READINESS.md` 为准：

- official universe：438 / 438；
- local prospectus：438 / 438；
- IPO OHLCV：432 / 438；
- authoritative snapshots：最近一次真实 audit 时 0 / 438；
- HSI / industry benchmark / total-market turnover：仍缺失；
- PR-A Document materialization：可以开始；
- full Model-ready data gate：仍 blocked。

这些数字只有在真实 materialization / source audit 后才允许更新。

## 时间治理

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在 feature / target / model policy 冻结前不得用于选特征、阈值、模型或 Prompt / Retriever / LLM 调优。

## `docs/annotation/` 为什么还存在

`docs/annotation/gpt_expert_v1_1/` 中保留的内容属于**机器测试 / frozen fixture 资产**，不是当前团队阅读文档。上一轮清理已验证部分测试和 Retriever preflight 仍依赖这些文件，因此不能当作普通历史 Markdown 删除。

不要把该目录重新扩展成历史 protocol / handoff 文档仓库。

## 文档维护规则

- **长期契约 / 当前执行指引**：进入 `docs/`；
- **运行时 / 测试 fixture**：只保留机器真正依赖的最小资产；
- **阶段性实验结果**：进入可版本化 report / artifact；
- **一次性 handoff / 临时计划**：完成后不长期保留为活文档；
- **真实 readiness 数字**：只有真实运行后更新；
- **已被新版本替代的说明或死链接**：从当前树 / 当前正文移除，由 Git history 保存。

目标是让新成员进入 `docs/` 后几分钟内就能回答：**现在做到哪里、下一步只做什么、哪些边界不能破坏。**
