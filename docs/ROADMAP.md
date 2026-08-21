# Roadmap

> Status snapshot: **2026-08-21**  
> 当前唯一主线：**End-to-End Closed Loop First**。  
> PR-A：**COMPLETE / FROZEN**；下一正式里程碑：**PR-B — Market-X Core + Governed EOD Store（NOT STARTED）**。

## 版本路线

| 版本 / Track | 目标 | 状态 |
| --- | --- | --- |
| v0.2.0 | 真实文档纵向切片与数据治理 | RELEASED / HISTORICAL |
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
- 稳定 Production Retriever；
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

### PR-A Document + Oracle Materialization & Coverage

PR-A 已完成并冻结。正式物化 source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

冻结结果：

- official 2020–2024 cohort：438 / 438；
- Production analysis：438 / 438；
- authoritative snapshots：438 / 438；
- Production Document-X：438 / 438；
- feature schema：`v04_document_features_v1`，100 维；
- Production failures：0；
- silent drops：0；
- Oracle materialized：60；
- `no_reviewed_gold`：378；
- Production ∩ Oracle：60；
- A6 determinism：438 checked，0 mismatches，PASS；
- 2025 blind access：NO。

冻结记录见：

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

## 当前真实 readiness

以下数字来自已完成的 PR-A materialization 与既有市场数据审计：

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| Local prospectus coverage | 438 / 438 |
| IPO OHLCV outcome coverage | 432 / 438 |
| Authoritative Document Snapshot pipeline | AVAILABLE |
| Authoritative snapshots | 438 / 438 |
| Production Document-X | 438 / 438, 100 dimensions |
| Oracle Document-X | 60 materialized; 378 no reviewed Gold |
| Production failures / silent drops | 0 / 0 |
| HSI history | MISSING |
| Industry benchmark mapping / history | MISSING |
| Total-market turnover | MISSING |
| PR-A Document materialization gate | **COMPLETE / FROZEN** |
| PR-B Market-X Core | **NOT STARTED / NEXT** |
| Full Model-ready data gate | BLOCKED |

PR-A 完成不等于 Model-ready data gate 已打开。完整闭环仍需要后续受治理的 Market-X、Outcome 与 Dataset。

## Closed Loop 执行状态

| Phase / PR | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze Current Document Intelligence | **COMPLETE / FROZEN** | 已完成 |
| CL-2 / PR-A | Document + Oracle Materialization & Coverage | **COMPLETE / FROZEN** | 已完成：438 coverage + Production X + Oracle + A6 determinism |
| CL-3 / PR-B | Market-X Core + Governed EOD Store | **NOT STARTED / NEXT** | point-in-time Market-X Core manifest + coverage |
| CL-4 / PR-C | Freeze 5D Outcome Policy | PENDING | development-only target policy frozen |
| CL-5 / PR-D | Canonical Model-ready Dataset | BLOCKED BY B/C | one rebuildable dataset + manifests |
| CL-6 / PR-E | Baseline + Oracle Diagnostic | NOT STARTED | M/P/O/PM/OM fair comparison |
| CL-7 / PR-F | LightGBM + Explainability | NOT STARTED | baseline complete and reproducible |
| CL-8/9 / PR-G | Market Agent + Final Supervisor | NOT STARTED | frozen model output contract |
| CL-10 / PR-H | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED | PDF → Final Report complete |

## PR-A 已完成任务拆解

```text
PR-A0  Freeze execution context / hashes                         DONE
PR-A1  Add thin canonical CLI: scripts/run_v04_pr_a.py          DONE
PR-A2  Run deterministic Development pilot                       DONE
PR-A3  Materialize 2020–2024 Production snapshots/features      DONE
PR-A4  Materialize Oracle inventory/features                     DONE
PR-A5  Build unified coverage table                              DONE
PR-A6  Rerun and verify stable hashes                            DONE
```

PR-A 的 Gate 目标是让 438 个 case **全部有可审计状态**，所有失败都有明确 stage / reason，并验证持久化 artifact 的确定性。实际冻结结果为 438 / 438 Production 成功、0 failure、0 silent drop。

### PR-A 冻结输出

Coverage 中保留：

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

以及：

```text
Production materialized count
Production failure count by reason
Oracle materialized count
Production ∩ Oracle intersection count
```

## 后续严格顺序

正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
PR-B  Market-X Core + Governed EOD Store             NEXT
PR-C  5D Outcome Policy Freeze
PR-D  Canonical Model-ready Dataset
PR-E  Baseline + Oracle Diagnostic
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E + Real-case Demo
v0.4 Freeze
```

准备性研究可以提前并行，但**不得把准备工作视为后续正式 Gate 已开始/已通过，也不得越过上述顺序合并到 main**。

每个 PR 必须：

- 从最新 `main` 创建或同步；
- 范围单一；
- CI 全绿；
- manifest / report 可重复；
- 不把一次性实验垃圾堆入活文档；
- 当前正式 Gate 合并后再推进下一正式 milestone。

## 正式建模比较

PR-D / PR-E 至少冻结：

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

2024 用于冻结方案的正式 validation / model-family comparison，不允许反复调参后继续称 untouched validation。

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

## 文档治理状态

2026-08-21 已将 PR-A 完成状态同步到活文档：

- PR-A materialization / coverage / determinism：COMPLETE / FROZEN；
- Document-X authoritative snapshots：438 / 438；
- Production Document-X：438 / 438；
- Oracle：60，`no_reviewed_gold`：378；
- PR-B：NOT STARTED / NEXT；
- full Model-ready gate：仍 BLOCKED。

剩余 research 文档仅保留仍有当前契约或冻结治理价值的内容。

## 当前文档入口

- 总执行计划：[`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 当前架构：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- Schema / modeling contracts：[`DATA_SCHEMA.md`](DATA_SCHEMA.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- PR-A 冻结报告：[`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- Document / Market feature contract：[`research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md`](research/V04_DOCUMENT_MARKET_FEATURE_CONTRACT.md)
- Pre-listing Market X：[`research/V04_PRELISTING_MARKET_FEATURES.md`](research/V04_PRELISTING_MARKET_FEATURES.md)
- Oracle：[`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
- 完整文档索引：[`README.md`](README.md)
