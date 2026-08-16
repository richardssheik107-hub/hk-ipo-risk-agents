# Roadmap

> Status snapshot: 2026-08-16  
> 当前唯一主线：**End-to-End Closed Loop First**。

## 版本路线

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.2.0 | 真实文档纵向切片与数据治理 | RELEASED |
| v0.3.0 | Financial / Legal / Business 多 Agent 文档风险分析 | RELEASED / FROZEN |
| Retriever V3 research | BM25 / Table / LambdaMART / Locked evaluation | MERGED / FROZEN |
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

Retriever V3、BM25、table-aware lane、LambdaMART LTR 与最终 Locked evaluation 已进入仓库历史并冻结。

重要治理规则：

- 历史 Locked 10 已正式消费；
- 不允许继续在该 10 case 上调参后重新称其为 blind；
- v0.5 若重启 Retriever 研究，只能在 development 上开发，并建立新的 unseen / external / temporal holdout。

因此 Retriever 研究不是当前 v0.4 的前置阻塞项。

## v0.4 当前 readiness

以 `research/V04_DATA_READINESS.md` 最新审计为基准：

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| IPO OHLCV outcome coverage | 432 / 438 |
| Document Risk Snapshot pipeline | AVAILABLE |
| Existing authoritative snapshots | 0 / 438 at latest readiness audit |
| HSI history | MISSING |
| Industry benchmark mapping | MISSING |
| Industry-index history | MISSING |
| Total-market turnover | MISSING |
| Model-ready gate | BLOCKED |

其中 0 / 438 是该 readiness audit 时点的“已 materialize artifact”状态，不代表文档分析 pipeline 不可运行。

## Closed Loop 执行状态

| Phase | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze current Document Intelligence | **READY / CURRENT** | v0.3 tests、offline、Mock、真实回归稳定 |
| CL-2 | Build IPO-level Document Risk Features | **CURRENT** | 批量 authoritative snapshots + deterministic feature table |
| CL-3 | Close minimum Market Data | **PARTIAL** | 至少完成第一版模型真正需要的 benchmark / market inputs |
| CL-4 | Freeze 5D Outcome Policy | PENDING | 仅用 2020–2023 development 决定 classification threshold |
| CL-5 | Build Model-ready Dataset | BLOCKED BY CL-2/3/4 | X_document + X_market + y 可重建 |
| CL-6 | Logistic / Linear Baseline | NOT STARTED | Market-only / Document-only / Combined 可公平比较 |
| CL-7 | LightGBM + Explainability | NOT STARTED | baseline 完整可复现 |
| CL-8 | Market Agent MVP | NOT STARTED | 冻结模型输出契约 |
| CL-9 | Final Supervisor | NOT STARTED | Document + Market 结果可组合 |
| CL-10 | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED | PDF → Final Report 完整运行 |

## 接下来严格执行

```text
1. Freeze current Document Intelligence
2. Run 438-case authoritative document snapshot materialization
3. Build IPO-level Document Risk Feature table
4. Close minimum benchmark / market data needed by first model
5. Freeze 5D outcome policy on development only
6. Build model-ready dataset
7. Run Logistic / Linear baseline
8. Run LightGBM + explainability
9. Add Market Agent
10. Add Final Supervisor
11. Complete Streamlit full E2E
12. Freeze v0.4
```

除非出现阻断闭环的 bug、数据泄漏或不可复现问题，否则在第 12 步前不重新把主线切回 Retriever、Fine-tuning 或大规模 Prompt / UI 优化。

## 正式建模比较

必须保留三组：

```text
Market-only
Document-only
Document + Market
```

核心问题不是单一 AUC 是否足够高，而是 Document Risk 是否对 Market-only 提供稳定的增量信息。

## 时间切分

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在模型和 feature policy 冻结前不得用于调参。

## 当前文档入口

- 总执行计划：[`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- 完整文档索引：[`README.md`](README.md)