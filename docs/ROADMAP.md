# Roadmap

> Status snapshot: 2026-08-18  
> 当前唯一主线：**End-to-End Closed Loop First**。

## 版本路线

| 版本 / Track | 目标 | 状态 |
| --- | --- | --- |
| v0.2.0 | 真实文档纵向切片与数据治理 | RELEASED |
| v0.3.0 | Financial / Legal / Business 多 Agent 文档风险分析 | RELEASED / FROZEN |
| Retriever V3 research | BM25 / Table / LambdaMART / Locked evaluation | MERGED / FROZEN |
| Oracle Document Modeling | Expert Gold 上限特征 + IPO structure/context + baseline foundation | **MERGED / EVALUATION-ONLY** |
| v0.4-MVP | Document Risk → Market Outcome 完整闭环 | **ACTIVE** |
| v0.4.1 | LightGBM + Explainability | PLANNED |
| v0.4.2 | Market Agent + Final Supervisor | PLANNED |
| v0.4.3 | Streamlit Full E2E Demo | PLANNED |
| v0.5.0 | Retriever / LLM / Agent / Verifier 研究级优化 | DEFERRED |
| v0.6.0 | 正式评测、消融、失败分析、Blind Test | PLANNED |
| v1.0.0 | 最终发布 / 比赛 / 作品集版本 | PLANNED |

## 已完成基线

v0.3 已具备：

- 真实 PDF Parser；
- 共享 Retriever；
- Financial / Legal / Business Agents；
- 8 类正式文档风险；
- deterministic Skills / Calculations；
- Specialized Verifier；
- Supervisor；
- Service；
- Streamlit；
- Markdown / JSON 报告；
- Mock / offline / optional-AI 降级路径。

该层现在作为 Document Intelligence 稳定基线，不再要求先继续优化 Retriever。

## Retriever 研究状态

Retriever V3、BM25、table-aware lane、LambdaMART LTR 与最终 Locked evaluation 已进入主线历史并冻结。

重要治理规则：

- 历史 Locked 10 已正式消费；
- 不允许继续在该 10 case 上调参后重新称其为 blind；
- v0.5 若重启 Retriever 研究，只能在 development 上开发，并建立新的 unseen / external / temporal holdout。

因此 Retriever 研究不是当前 v0.4 的前置阻塞项。

## Oracle Document Modeling 状态

Oracle track 已合入主线，定位为**评测上限与错误归因工具**，不是生产路径。

当前已有：

- audited pass1 + explicit audit overlay 的 Effective Gold loader；
- versioned Oracle Document Feature manifest / content hash；
- Oracle feature batch materialization CLI；
- Oracle Gold inventory / provenance index；
- IPO structure features；
- point-in-time IPO market-context features；
- governed target-IPO EOD filtered cache builder；
- deterministic Logistic Regression baseline harness；
- 对应单元测试。

Oracle track 必须满足：

- 只使用上市前可得 X；
- 2025 blind 不得 join y；
- 与 production pipeline 使用完全相同的 Market X、y、split 和模型进行比较；
- 不得把 Oracle Gold 特征接入生产实时/离线分析路径。

它将在 CL-5 model-ready dataset 完成后用于回答：

```text
Oracle 有效、Production 弱  → 文档流水线存在较大信息损失
Oracle 也弱                → 信号 / target / 样本量可能才是主要瓶颈
Oracle 与 Production 接近   → 当前文档流水线已接近可用上限
```

## v0.4 当前 readiness

以 `research/V04_DATA_READINESS.md` 最新审计为基准：

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| IPO OHLCV outcome coverage | 432 / 438 |
| Document Risk Snapshot pipeline | AVAILABLE |
| Existing authoritative snapshots | 0 / 438 at latest readiness audit |
| Oracle Document Feature builder | AVAILABLE |
| Oracle Logistic baseline harness | AVAILABLE / WAITING DATASET |
| IPO EOD filtered-store builder | AVAILABLE |
| HSI history | MISSING |
| Industry benchmark mapping | MISSING |
| Industry-index history | MISSING |
| Total-market turnover | MISSING |
| Model-ready gate | BLOCKED |

其中 0 / 438 是 readiness audit 时点的“已 materialize artifact”状态，不代表文档分析 pipeline 不可运行。

## Closed Loop 执行状态

| Phase | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze current Document Intelligence | **READY / CURRENT** | v0.3 tests、offline、Mock、真实回归稳定 |
| CL-2 | Build IPO-level Document Risk Features | **CURRENT** | 批量 authoritative snapshots + deterministic feature table |
| CL-3 | Close minimum Market Data | **PARTIAL** | 至少完成第一版模型真正需要的 market inputs |
| CL-4 | Freeze 5D Outcome Policy | PENDING | 仅用 2020–2023 development 决定 classification threshold |
| CL-5 | Build Model-ready Dataset | BLOCKED BY CL-2/3/4 | X_document + X_market + y 可重建 |
| CL-6 | Baseline + Oracle Diagnostic | NOT STARTED | Market-only / Production Document / Oracle Document / Combined 可公平比较 |
| CL-7 | LightGBM + Explainability | NOT STARTED | baseline 与数据契约完整可复现 |
| CL-8 | Market Agent MVP | NOT STARTED | 冻结模型输出契约 |
| CL-9 | Final Supervisor | NOT STARTED | Document + Market 结果可组合 |
| CL-10 | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED | PDF → Final Report 完整运行 |

## 接下来严格执行

```text
1. Freeze current Document Intelligence
2. Run authoritative document snapshot materialization
3. Build IPO-level Production Document Risk Feature table
4. Index and materialize Oracle Document Features for eligible reviewed cases
5. Close minimum market data and build governed EOD cache
6. Freeze 5D outcome policy on development only
7. Build one model-ready dataset + frozen manifests
8. Run Logistic/Ridge baseline on Market-only / Production Document / Oracle Document / Combined
9. Use Oracle-vs-Production gap to decide whether document-pipeline optimization is justified
10. Run LightGBM + explainability
11. Add Market Agent
12. Add Final Supervisor
13. Complete Streamlit full E2E
14. Freeze v0.4
```

除非出现阻断闭环的 bug、数据泄漏或不可复现问题，否则在第 14 步前不重新把主线切回 Retriever、Fine-tuning 或大规模 Prompt / UI 优化。

## 正式建模比较

至少保留四组：

```text
A. Market-only
B. Production Document-only
C. Oracle Document-only
D. Production Document + Market
```

如果 Oracle 样本覆盖允许，再增加：

```text
E. Oracle Document + Market
```

所有组必须使用相同 cohort、相同时间切分、相同 y policy 和相同模型族，禁止为了某一组单独改变样本或阈值。

## 时间切分

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在模型和 feature policy 冻结前不得用于调参。Oracle track 同样禁止读取 2025 blind y。

## 当前文档入口

- 总执行计划：[`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- Oracle 评测路径：[`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
- 完整文档索引：[`README.md`](README.md)
