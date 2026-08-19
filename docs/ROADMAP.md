# Roadmap

> Status snapshot: **2026-08-19**  
> 当前唯一主线：**End-to-End Closed Loop First**。  
> 当前唯一执行里程碑：**PR-A — Document + Oracle Materialization & Coverage**。

## 版本路线

| 版本 / Track | 目标 | 状态 |
| --- | --- | --- |
| v0.2.0 | 真实文档纵向切片与数据治理 | RELEASED |
| v0.3.0 | Financial / Legal / Business 多 Agent 文档风险分析 | RELEASED / FROZEN |
| Retriever V3 research | BM25 / Table / LambdaMART / Locked evaluation | MERGED / FROZEN |
| Oracle Document Modeling | Expert Gold 上限特征 + baseline foundations | MERGED / EVALUATION-ONLY |
| v0.4-MVP | Document Risk → Market Outcome 完整闭环 | **ACTIVE** |
| v0.4.1 | LightGBM + Explainability | PLANNED |
| v0.4.2 | Market Agent + Final Supervisor | PLANNED |
| v0.4.3 | Streamlit Full E2E Demo | PLANNED |
| v0.5.0 | Retriever / LLM / Agent / Verifier 研究级优化 | DEFERRED / ORACLE-GAP-DEPENDENT |
| v0.6.0 | 正式评测、消融、失败分析、Blind Test | PLANNED |
| v1.0.0 | 最终发布 / 比赛 / 作品集版本 | PLANNED |

## 已完成并冻结

### v0.3 Document Intelligence

当前稳定基线已具备：

- 真实 PDF Parser；
- 共享 Retriever；
- Financial / Legal / Business Agents；
- 8 类正式文档风险；
- deterministic Skills / Calculations；
- Specialized Verifier；
- Document Supervisor；
- Service；
- Streamlit；
- Markdown / JSON 报告；
- Mock / offline / optional-AI 降级路径。

**CL-1 已完成。** v0.4 不再要求先提高 Retriever 指标。

### Retriever research

Retriever V3、BM25、table-aware lane、LambdaMART LTR 与最终 Locked evaluation 已进入主线并冻结。

治理规则：

- 历史 Locked 10 已消费；
- 不允许继续在该 10 case 上调参后重新称其为 blind；
- v0.5 若重启 Retriever 研究，必须建立新的 unseen / external / temporal holdout。

### Oracle Document Modeling

Oracle track 已合入主线，定位为**评测上限 / 错误归因工具**，不是生产路径。

已有：

- Effective Gold loader；
- Oracle Document Feature manifest / content hash；
- Oracle batch materialization CLI；
- Oracle Gold inventory / provenance index；
- deterministic Logistic Regression baseline harness；
- 对应单元测试。

Oracle 不能进入 Production runtime，也不能读取 2025 blind y。

## 当前真实 readiness

以下数字沿用 `research/V04_DATA_READINESS.md` 最近一次真实审计，不因计划文档更新而虚构变化：

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| Local prospectus coverage | 438 / 438 |
| IPO OHLCV outcome coverage | 432 / 438 |
| Authoritative Document Snapshot pipeline | AVAILABLE |
| Existing authoritative snapshots | 0 / 438 at latest readiness audit |
| Production Document Feature vectorizer | AVAILABLE |
| Oracle Document Feature builder | AVAILABLE |
| Oracle Logistic baseline harness | AVAILABLE / WAITING DATASET |
| HSI history | MISSING |
| Industry benchmark mapping / history | MISSING |
| Total-market turnover | MISSING |
| Model-ready gate | BLOCKED |

`0 / 438` 表示最近一次 readiness audit 时尚未进行全量 authoritative materialization，不代表 pipeline 不可运行。

## Closed Loop 执行状态

| Phase / PR | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze Current Document Intelligence | **COMPLETE / FROZEN** | 已完成 |
| CL-2 / PR-A | Document + Oracle Materialization & Coverage | **ACTIVE / CURRENT** | 438 coverage + Production X + Oracle coverage + intersection + deterministic rerun |
| CL-3 / PR-B | Market-X Core + Governed EOD Store | PARTIAL / NEXT | point-in-time Market-X Core manifest + coverage |
| CL-4 / PR-C | Freeze 5D Outcome Policy | PENDING | development-only target policy frozen |
| CL-5 / PR-D | Canonical Model-ready Dataset | BLOCKED BY A/B/C | one rebuildable dataset + manifests |
| CL-6 / PR-E | Baseline + Oracle Diagnostic | NOT STARTED | M/P/O/PM/OM fair comparison |
| CL-7 / PR-F | LightGBM + Explainability | NOT STARTED | baseline complete and reproducible |
| CL-8/9 / PR-G | Market Agent + Final Supervisor | NOT STARTED | frozen model output contract |
| CL-10 / PR-H | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED | PDF → Final Report complete |

## PR-A 当前任务拆解

PR-A 必须按以下顺序推进：

```text
PR-A0  Freeze execution context / hashes
PR-A1  Add thin canonical CLI: scripts/run_v04_pr_a.py
PR-A2  Run deterministic Development pilot
PR-A3  Materialize 2020–2024 Production snapshots/features
PR-A4  Materialize Oracle inventory/features
PR-A5  Build unified coverage table
PR-A6  Rerun and verify stable hashes
```

PR-A 的目标不是要求 438 / 438 全部成功，而是让 438 个 case **全部有可审计状态**，并且所有失败都有明确 stage / reason。

### PR-A 必须输出

```text
case_id
source_year
dataset_split
production_analysis_status
production_snapshot_status
production_document_available
production_failure_stage
production_failure_reason
production_snapshot_hash
production_feature_hash
production_feature_manifest_hash
oracle_document_available
oracle_failure_reason
oracle_feature_hash
oracle_feature_manifest_hash
oracle_effective_annotation_hash
```

以及四个核心统计：

```text
Production materialized count
Production failure count by reason
Oracle materialized count
Production ∩ Oracle intersection count
```

## 后续严格顺序

```text
PR-A  Document + Oracle Materialization & Coverage
PR-B  Market-X Core + Governed EOD Store
PR-C  5D Outcome Policy Freeze
PR-D  Canonical Model-ready Dataset
PR-E  Baseline + Oracle Diagnostic
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E + Real-case Demo
v0.4 Freeze
```

每个 PR 必须：

- 从最新 `main` 创建；
- 范围单一；
- CI 全绿；
- manifest / report 可重复；
- 不把一次性实验垃圾堆入活文档；
- merge 后再开启下一阶段。

## 正式建模比较

PR-D/PR-E 至少冻结：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

Production 与 Oracle 比较必须使用相同 cohort、split、target、preprocessing 和 model family。

## 时间切分

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2025 在 feature / target / model policy 冻结前不得用于调参。Oracle 同样禁止读取 2025 blind y。

## 当前禁止主线化的工作

在 PR-E Oracle diagnostic 出来前，不重新把以下内容拉回主线：

- Retriever 调参；
- LLM Reranker；
- Fine-tuning / LoRA；
- 大规模 Prompt 重构；
- 新专业 Agent；
- 深度学习市场模型；
- 大规模 UI 重构。

## 当前文档入口

- 总执行计划：[`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- Document / Market feature contract：[`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md)
- Pre-listing Market X contract：[`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- Oracle 评测路径：[`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
- 完整文档索引：[`README.md`](README.md)
