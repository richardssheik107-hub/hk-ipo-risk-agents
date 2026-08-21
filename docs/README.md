# Documentation Index

> Status snapshot: **2026-08-21**

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

当前里程碑状态：

> **PR-A — COMPLETE / FROZEN**

> Next formal milestone: **PR-B — NOT STARTED**

CL-1 Document Intelligence freeze 与 PR-A Document materialization 均已完成。当前不继续优化 Retriever、Prompt、LLM 或 Agent；下一正式工作是构建受 point-in-time 治理的 Market-X。

## 文档优先级

遇到口径冲突时，按以下顺序理解当前项目：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) — **唯一权威执行总计划**，包含正式 milestone / Gate 顺序；
2. [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md) — **五人执行与职责计划**，规定角色、准备性并行与正式 Gate 边界；
3. [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md) — PR-A 的冻结结果、Coverage hash 生命周期与本地产物政策；
4. [`V04_PR_A_RUNBOOK.md`](V04_PR_A_RUNBOOK.md) — A / Pipeline Lead 的 PR-A 已冻结运行手册；
5. [`ROADMAP.md`](ROADMAP.md) — 当前阶段状态、下一里程碑；
6. [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — 产品目标、范围、信任边界与成功标准；
7. [`ARCHITECTURE.md`](ARCHITECTURE.md) — **当前架构**，旧 v0.2 / v0.3 设计历史已移除；
8. [`DATA_SCHEMA.md`](DATA_SCHEMA.md) — 当前公共 Schema 与 v0.4 建模契约说明；
9. [`COMPETITION_DATA_OVERVIEW.md`](COMPETITION_DATA_OVERVIEW.md) — 原始赛事语料与 v0.4 official modeling cohort 的区别。

开发规则另见根目录 [`AGENTS.md`](../AGENTS.md)。

## v0.4 当前工作文档

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md) — PR-A COMPLETE / FROZEN 的正式人类可读记录；
- [`V04_PR_A_RUNBOOK.md`](V04_PR_A_RUNBOOK.md) — PR-A 运行、Coverage、Reproducibility 的冻结操作手册；
- [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) — 最新真实 readiness：PR-A 已冻结，full model-ready gate 仍 blocked；
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

## PR-A 已完成什么

PR-A 已回答并冻结四个基础问题：

```text
1. official 2020–2024 的 438 个 IPO 是否都有 Production Document X？
   → 438 / 438
2. Production 是否存在失败或 silent drop？
   → failure = 0, silent drop = 0
3. Oracle Gold 实际可 materialize 多少？
   → 60；no_reviewed_gold = 378
4. Production 与 Oracle 的公平交集有多少？
   → 60
```

冻结结果：

- Production analysis：438 / 438；
- authoritative snapshot：438 / 438；
- Production Document-X：438 / 438；
- feature schema：`v04_document_features_v1`，100 维；
- Oracle：60；
- Production failure / silent drop：0 / 0；
- A6 determinism：438 checked，0 mismatches，PASS；
- 2025 access：NO。

统一执行入口：

```text
scripts/run_v04_pr_a.py
```

冻结记录：

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

## 五人执行与正式 Gate

完整角色与执行边界见 [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)。

固定角色：

```text
A  Tech Lead / Pipeline
B  Document / Agent
C  Market Data / PIT
D  Quant / ML Research
E  Oracle / Product Integration
```

正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
→ PR-B Market-X Core + Governed EOD Store            NEXT
→ PR-C 5D Outcome Policy Freeze
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
→ PR-G Market Agent + Final Supervisor
→ PR-H Streamlit Full E2E + Real-case Demo
```

团队可以并行做**准备性工作**，例如数据源调研、接口草案、测试夹具和 UI skeleton；但准备工作不能被标记为后续正式 Gate 已开始/已通过，也不能越过上述顺序合并到 `main`。

## PR-A 的冻结顺序

```text
PR-A0  Freeze execution context and hashes       DONE
PR-A1  Implement scripts/run_v04_pr_a.py + tests DONE
PR-A2  Run small deterministic Development pilot DONE
PR-A3  Run 2020–2024 Production materialization DONE
PR-A4  Run Oracle materialization                DONE
PR-A5  Build unified coverage table              DONE
PR-A6  Rerun and verify deterministic hashes     DONE
```

当前工程状态：A0–A6 全部完成，PR-A 已冻结。下一正式里程碑是 PR-B Market-X Core；PR-B 尚未开始正式 Gate。

## 当前真实 readiness

当前数字以 [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) 为准：

- official universe：438 / 438；
- local prospectus：438 / 438；
- IPO OHLCV：432 / 438；
- authoritative snapshots：438 / 438；
- Production Document-X features：438 / 438（100 维）；
- Oracle Document-X：60；`no_reviewed_gold`：378；
- Production failures / silent drops：0 / 0；
- HSI / industry benchmark / total-market turnover：仍缺失；
- PR-A Document materialization：**COMPLETE / FROZEN**；
- PR-B Market-X Core：**NOT STARTED / NEXT**；
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

`docs/annotation/gpt_expert_v1_1/` 中保留的内容属于**机器测试 / frozen fixture 资产**，不是当前团队阅读文档。部分测试和 Retriever preflight 仍依赖这些文件，因此不能当作普通历史 Markdown 删除。

不要把该目录重新扩展成历史 protocol / handoff 文档仓库。

## 文档维护规则

- **长期契约 / 当前执行指引**：进入 `docs/`；
- **运行时 / 测试 fixture**：只保留机器真正依赖的最小资产；
- **阶段性实验结果**：进入可版本化 report / artifact；
- **一次性 handoff / 临时计划**：完成后不长期保留为活文档；
- **真实 readiness 数字**：只有真实运行后更新；
- **已被新版本替代的说明或死链接**：从当前树 / 当前正文移除，由 Git history 保存。

目标是让新成员进入 `docs/` 后几分钟内就能回答：**现在做到哪里、下一步只做什么、谁负责什么、哪些准备可以并行、哪些正式 Gate 不能越过。**
