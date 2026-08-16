# Documentation Index

本目录只保留对**当前主线开发**有直接指导价值的活文档。

历史 v0.2 / v0.3 阶段的审计包、人工 review packet、handoff、Gate-A 执行计划、旧 Retriever pilot 和阶段性讨论稿已从当前 `main` 文档树移除。它们没有被抹除，仍可通过 Git history、旧 commit、PR 或 release 查询。

## 当前主线

项目当前执行策略为 **End-to-End Closed Loop First**：

```text
Prospectus PDF
→ Document Intelligence
→ IPO-level Document Risk Features
→ Pre-IPO Market Features
→ 5D Outcome
→ Model-ready Dataset
→ Baseline / LightGBM
→ Market Agent
→ Final Supervisor
→ Streamlit Full E2E
```

当前优先级是完成 v0.4 完整闭环，而不是继续优化单个 Retriever、Prompt 或 Agent。

## 文档优先级

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — 当前执行总计划与阶段 Gate。
2. [`ROADMAP.md`](ROADMAP.md) — 当前进度、阻塞项与下一步。
3. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、范围、信任边界与成功标准。
4. [`ARCHITECTURE.md`](ARCHITECTURE.md) — 模块边界与系统架构。
5. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 公共 Schema 与跨模块数据契约。
6. [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) — 赛事数据宇宙、年度切分与数据治理。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。

## v0.4 当前工作文档

以下文档直接服务于当前闭环：

- [`research/V04_MARKET_FOUNDATION.md`](research/V04_MARKET_FOUNDATION.md) — 市场数据、标签、年度切分和 blind 治理基础。
- [`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md) — Document Risk → 模型特征契约。
- [`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md) — 严格上市前市场特征契约。
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 当前真实数据覆盖、缺失源和 model-ready gate。

## 冻结研究参考

- [`research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md`](research/RETRIEVER_V3_PREFLIGHT_AND_RERANKER_V11_DECISIONS.md)

Retriever V3 / BM25 / Table / LambdaMART 等研究成果已经进入主线历史，但当前冻结，不作为 v0.4 前置条件。历史 Locked 10 已经正式消费，后续不得重新把它当作独立 blind set 调参；若 v0.5 重启 Retriever 优化，必须建立新的 unseen / external / temporal holdout。

## 当前下一项工作

以最新 readiness audit 为基准：

- v0.3 Document Intelligence 已可作为稳定基线；
- v0.4 Document / Market feature contracts 已存在；
- 官方 2020–2024 IPO universe 为 438 个 case；
- IPO OHLCV 现有覆盖 432 / 438；
- 438-case authoritative document snapshot 全量 materialization 尚未执行；
- HSI、行业 benchmark mapping / history、全市场 turnover 等完整 market-X 数据源仍缺失。

因此当前执行顺序为：

```text
CL-1 Freeze current Document Intelligence
CL-2 Materialize IPO-level Document Risk Features
CL-3 Close minimum real Market Data
CL-4 Freeze 5D Outcome policy
CL-5 Build model-ready dataset
```

后续模型、Market Agent、Final Supervisor 和 Streamlit E2E 按 Master Plan 顺序推进。

## 文档维护规则

以后新增文档前先判断它属于哪一类：

- **长期契约 / 当前执行指引**：可以进入 `docs/`；
- **阶段性实验结果**：优先进入可版本化 report / artifact，不长期堆在 `docs/`；
- **一次性 review packet / handoff / 临时计划**：完成后不保留在当前活文档树；
- **已被新版本替代的文档**：从当前树删除，由 Git history 保存历史。

目标是让任何新成员进入 `docs/` 后，能在几分钟内知道：**项目现在做到哪里、下一步做什么、哪些边界不能破坏。**