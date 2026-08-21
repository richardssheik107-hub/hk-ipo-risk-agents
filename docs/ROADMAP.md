# Roadmap

> Status snapshot: **2026-08-21**  
> 当前唯一主线：**End-to-End Closed Loop First**。  
> PR-A：**COMPLETE / FROZEN**；PR-B：**COMPLETE / FROZEN**。
> 下一正式里程碑：**PR-C — 5D Outcome Policy Freeze / NOT STARTED**。
> PR-B freeze source revision：**`dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7`**。

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

当前稳定基线已具备真实 PDF Parser、稳定 Production Retriever、Financial/Legal/Business Agents、8 类正式文档风险、deterministic Skills/Calculations、Specialized Verifier、Document Supervisor、Service、Streamlit、Markdown/JSON 报告和 Mock/offline/optional-AI 降级路径。

**CL-1 已完成。** v0.4 不再要求先提高 Retriever 指标。

### Retriever research

Retriever V3、BM25、table-aware lane、LambdaMART LTR 与最终 Locked evaluation 已进入主线并冻结。历史 Locked 10 已消费；未来若重启研究必须建立新的 unseen/external/temporal holdout。

### Oracle Document Modeling

Oracle track 已合入主线，定位为 evaluation ceiling / error attribution，不是生产路径。Oracle 不能进入 Production runtime，也不能读取 2025 blind y。

### PR-A Document + Oracle Materialization & Coverage

PR-A 已完成并冻结。正式物化 source revision：

```text
13e0281f5e65a970caaf1255e56d08597e1ead70
```

冻结结果：

```text
official 2020–2024 cohort     438 / 438
Production analysis           438 / 438
authoritative snapshots       438 / 438
Production Document-X         438 / 438
feature schema                v04_document_features_v1 / 100 dims
Production failures           0
silent drops                  0
Oracle materialized           60
no_reviewed_gold              378
Production ∩ Oracle           60
A6 determinism                438 checked / 0 mismatches / PASS
2025 blind access             NO
```

Frozen records:

- [`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json)

## 当前真实 readiness

以下数字来自已完成的 PR-A 与 PR-B 正式 materialization / determinism 审计。

| 项目 | 当前状态 |
| --- | --- |
| Official 2020–2024 IPO universe | 438 / 438 available |
| Local prospectus coverage | 438 / 438 |
| IPO OHLCV outcome coverage | 432 / 438 |
| Authoritative snapshots | 438 / 438 |
| Production Document-X | 438 / 438, 100 dimensions |
| Oracle Document-X | 60 materialized; 378 no reviewed Gold |
| Production failures / silent drops | 0 / 0 |
| PR-B Core code/tests | COMPLETE / FROZEN |
| PR-B Core real coverage | 438 / 438 materialized; 0 failed; 0 silent drops |
| HSI history | MISSING — Extended |
| Industry benchmark mapping / history | MISSING — Extended |
| Total-market turnover | MISSING — Extended |
| PR-B Gate | PASS / COMPLETE / FROZEN |
| Full Model-ready data gate | BLOCKED |

## PR-B frozen boundary

### Market-X Core

Current Core contract:

```text
v04_ipo_market_context_features_v1
ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

Frozen implementation:

```text
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

Governance already implemented in code/tests:

- target cohort selected by authoritative `official_listed_date.year`, not `source_year`;
- governed EOD filter retains `OBJECT_ID` provenance;
- `S_DQ_AMOUNT` cannot become total-market turnover;
- target IPO post-listing data cannot enter target X;
- prior outcome is usable only after its target session occurred strictly before target listing;
- 2025 blind y is rejected;
- one-case failure remains visible in coverage;
- resume is conflict-safe;
- deterministic rebuild path exists.

### Market-X Extended

Existing frozen 20-position reference-market contract remains separate:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
```

HSI / authoritative industry benchmark / HKEX total-market turnover are still missing. These are explicit Extended limitations, **not inputs that PR-B Core is allowed to fake**.

## Closed Loop execution state

| Phase / PR | 内容 | 状态 | 进入下一阶段的关键条件 |
| --- | --- | --- | --- |
| CL-1 | Freeze Current Document Intelligence | **COMPLETE / FROZEN** | 已完成 |
| CL-2 / PR-A | Document + Oracle Materialization & Coverage | **COMPLETE / FROZEN** | 已完成 |
| CL-3 / PR-B | Market-X Core + Governed EOD Store | **COMPLETE / FROZEN** | 已完成 |
| CL-4 / PR-C | Freeze 5D Outcome Policy | **NEXT / NOT STARTED** | Development-only target policy decision |
| CL-5 / PR-D | Canonical Model-ready Dataset | BLOCKED BY C | versioned Core/Extended dataset contract + manifests |
| CL-6 / PR-E | Baseline + Oracle Diagnostic | NOT STARTED | M/P/O/PM/OM fair comparison |
| CL-7 / PR-F | LightGBM + Explainability | NOT STARTED | baseline complete and reproducible |
| CL-8/9 / PR-G | Market Agent + Final Supervisor | NOT STARTED | frozen model output contract |
| CL-10 / PR-H | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED | PDF → Final Report complete |

## PR-B completion evidence

```text
official coverage             438 / 438
Core materialized             438 / 438
failed / silent drops         0 / 0
PIT failures                  0
Development / Validation      368 / 70
determinism                   438 checked / 0 mismatches / PASS
coverage hash                 768b027676453d02d0cb5db8599acffbc2d58d7f5dc6e373bd9f4ddb305c974e
2025 blind y accessed         NO
```

Canonical command and exact acceptance criteria:

- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md)
- [`../reports/frozen/v04_pr_b_market_x_core_manifest.json`](../reports/frozen/v04_pr_b_market_x_core_manifest.json)

## 后续严格顺序

正式 milestone / Gate / mainline merge 顺序固定为：

```text
PR-A  Document + Oracle Materialization & Coverage   COMPLETE / FROZEN
PR-B  Market-X Core + Governed EOD Store             COMPLETE / FROZEN
PR-C  5D Outcome Policy Freeze                       NEXT / NOT STARTED
PR-D  Canonical Model-ready Dataset
PR-E  Baseline + Oracle Diagnostic
PR-F  LightGBM + Explainability
PR-G  Market Agent + Final Supervisor
PR-H  Streamlit Full E2E + Real-case Demo
v0.4 Freeze
```

每个 PR 必须范围单一、CI/测试真实通过、manifest/report 可重复、不提交大型 runtime 数据、不虚构 readiness 数字。

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

PR-D 必须显式决定如何把 30-position Market-X Core 和 optional 20-position Extended contract 纳入新的 canonical dataset version；不能静默修改现有历史 120-position Extended join。

## 时间切分

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 用于冻结方案的正式 validation/model-family comparison，不允许反复调参后继续称 untouched validation。2025 在 feature/target/model policy 冻结前不得用于调参，Oracle 同样禁止读取 2025 blind y。

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
- PR-B Gate：[`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- Codex local handoff：[`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md)
- 当前规格：[`PROJECT_SPEC.md`](PROJECT_SPEC.md)
- 当前架构：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- Schema / modeling contracts：[`DATA_SCHEMA.md`](DATA_SCHEMA.md)
- 数据 readiness：[`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)
- PR-A 冻结报告：[`V04_PR_A_COMPLETION_REPORT.md`](V04_PR_A_COMPLETION_REPORT.md)
- Oracle：[`research/ORACLE_DOCUMENT_MODELING_PIPELINE.md`](research/ORACLE_DOCUMENT_MODELING_PIPELINE.md)
