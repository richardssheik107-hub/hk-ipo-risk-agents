# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-21**
> Stable document baseline: **v0.3.0 RELEASED / FROZEN**  
> PR-A Document materialization: **COMPLETE / FROZEN**
> Active program: **v0.4 End-to-End Closed Loop**  
> PR-B Market-X Core: **COMPLETE / FROZEN ON MAIN**
> Next formal milestone: **PR-C — 5D Outcome Policy Freeze / NOT STARTED**

本文件描述当前有效架构与仍有约束力的边界。历史 v0.2/v0.3 设计过程和已完成的一次性实验通过 Git history/release 追溯。

## 1. Architecture form

项目保持**模块化单体**：一个仓库、一个主要 Python 应用，以稳定 Pydantic Schema / Protocol 连接模块。

当前不引入与闭环无关的微服务、Kafka、Redis queue、Neo4j 或 Kubernetes。

核心依赖方向：

```text
Streamlit
  ↓
IPOAnalysisService / controlled upper service
  ↓
Document Workflow
  ↓
Parser / Retriever / Domain Agents / Skills / Verifier / Document Supervisor
  ↓
IPOAnalysisResult
  ↓
V04 Document Modeling Boundary
  ↓
Production Document X
  ↓
Market-X Core + optional governed Market-X Extended
  ↓
Outcome / Canonical Modeling Dataset
  ↓
Model / Explainability
  ↓
Market Agent / Final Supervisor
  ↓
Final Report / UI
```

禁止反向依赖：Agent 不操作前端，Schema 不依赖具体实现，Parser 不依赖 Agent，产品层不直接读取内部 raw model/data files。

## 2. Frozen Production Document Runtime

v0.3 已冻结为 v0.4 第一版 Production Document Intelligence：

```text
Prospectus PDF
    ↓
DocumentParser
    ↓
DocumentChunk
    ↓
Stable Retriever / Evidence
    ↓
Financial Agent ─┐
Legal Agent ─────┼→ Specialized Verifier → Document Supervisor
Business Agent ──┘                         ↓
                                      IPOAnalysisResult
```

当前真实主工作流为 `enhanced_v2`；`mvp_v1` 保留兼容/Mock/回归用途。

Offline 配置可让外部 LLM 明确 unavailable，但真实 Parser/Retriever/Agents 仍可运行。LLM unavailable 不得被伪造成成功；数字计算由 deterministic Skill 完成；无 Evidence 不得形成正式 verified 风险。

## 3. Frozen Document Modeling Boundary

PR-A 已完成 438-case materialization：

```text
IPOAnalysisResult
  ↓
V04DocumentSnapshotMaterializer
  ↓
V03DocumentRiskSnapshot
  ↓
DOCUMENT_FEATURE_MANIFEST_V1
  ↓
Production Document X
```

冻结结果：

```text
438 / 438 authoritative snapshots
438 / 438 Production Document-X
v04_document_features_v1
100 dimensions
0 Production failures
0 silent drops
```

该边界只消费最终结构化 Document result，不反向调用 Retriever、Agent 或 LLM。

### 3.1 Production path

```text
PDF
→ Parser
→ Retriever
→ Financial / Legal / Business Agents
→ Skills
→ Verifier
→ Document Supervisor
→ V03DocumentRiskSnapshot
→ Production Document X
```

### 3.2 Oracle path

Oracle 是 evaluation-only ceiling/error-attribution path：

```text
Reviewed Expert Gold
→ EffectiveRiskGoldView
→ Oracle Document X
```

当前 materialized Oracle = 60；no reviewed Gold = 378。Oracle 不进入 Production runtime，不向 Production X 泄漏专家答案，不读取 2025 blind y。

## 4. Market Foundation

市场层与 Document Runtime 解耦：

```text
Official IPO metadata
+ governed IPO daily bars
→ MarketLabelGenerator
→ MarketOutcomeLabel
```

已冻结基础规则：

- official listing price 为 return base；
- horizon 按 observed eligible trading sessions；
- 缺 listing price/history 时显式 unavailable；
- 2025 blind y 不进入 development/validation modeling record；
- official listing year 决定 modeling cohort，不使用 document `source_year` 替代。

当前 governed IPO OHLCV coverage = 432 / 438；6 个 case eligible but outcome unavailable。

## 5. Market-X Core — frozen PR-B boundary

PR-B Core 的目标不是依赖当前缺失的 HSI/industry/turnover 后才开始，而是先把**已经真实受治理且可严格 point-in-time 的市场上下文**稳定物化。该目标已经完成并冻结在 `main`。

Canonical flow：

```text
Official IPO metadata
+ governed IPO EOD
+ prior-IPO offer/context facts
+ prior-IPO outcomes already known before target listing
        ↓
IPO Market Context Core
        ↓
v04_ipo_market_context_features_v1
        ↓
30-position Core vector
        ↓
coverage / provenance / failure / determinism audit
```

Core schema/policy：

```text
schema:  v04_ipo_market_context_features_v1
policy:  ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent __missing indicators
= 30 ordered positions
```

Core features cover recent IPO counts, prior funds raised, recent IPO 1D break rate / 5D return and same-industry historical IPO context.

### 5.1 Core PIT boundary

For target listing date `T`:

```text
prior_ipo.listing_date < T
prior_1d.target_trading_date < T
prior_5d.target_trading_date < T
```

The target IPO's own listing-day/post-listing price never enters its X. If a prior IPO 5D outcome only becomes observable on `T`, it is not available strictly before the target listing and is excluded.

The same-industry Core context may use the authoritative IPO metadata's industry description as a peer grouping label; it is **not** an industry-index benchmark mapping and must not be treated as one.

### 5.2 Governed EOD store

Canonical builder:

```text
scripts/build_v04_ipo_eod_store.py
```

Current filter schema:

```text
v04_ipo_eod_filter_v2
```

The cohort is selected by authoritative `official_listed_date.year in 2020–2024`, not by prospectus `source_year`.

The filtered store retains `OBJECT_ID` for source-record provenance. `S_DQ_AMOUNT` remains a per-security source field and is never reinterpreted as total-market turnover.

### 5.3 Core orchestration

Canonical PR-B CLI:

```text
scripts/run_v04_pr_b.py
```

It orchestrates:

```text
Official 438-case cohort
→ governed EOD store
→ prior-IPO PIT context preparation
→ per-case Core artifacts
→ coverage / failure report
→ provenance freeze
→ conflict-safe resume
→ deterministic rebuild audit
```

The CLI does not expose a 2025 blind-outcome option.

PR-B has passed its Gate and is now a frozen 438-case Core asset. Targeted/full tests, the real pilot/full materialization and deterministic resume are recorded in [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md).

## 6. Market-X Extended — frozen optional source-dependent layer

The existing reference-market contract remains frozen and separate from Core:

```text
Governed HSI / industry benchmark / market activity
+ prior IPO information
→ PreListingMarketFeatureEngine
→ PreListingMarketFeatureSnapshot
→ MARKET_FEATURE_MANIFEST_V1
→ Extended Market Feature Vector
```

Versions:

```text
v04_prelisting_market_features_v1
v04_market_features_v1
```

Fixed 10 raw features:

```text
hsi_return_5d
hsi_return_20d
industry_return_5d
industry_return_20d
recent_ipo_break_rate
recent_ipo_return_5d
recent_ipo_1d_sample_count
recent_ipo_5d_sample_count
market_turnover_20d_mean
market_volatility_20d
```

Each raw feature has an adjacent `__missing` indicator, giving 20 ordered positions.

Current real Extended-source gaps:

```text
governed HSI daily history
authoritative industry→benchmark mapping
governed industry-index histories
governed HKEX total-market turnover
```

Hard prohibitions:

- Hang Seng Bank ≠ HSI；
- workbook industry name ≠ authoritative industry benchmark mapping；
- single-security `S_DQ_AMOUNT` ≠ total-market turnover；
- missing reference source ≠ neutral zero；
- no fake benchmark observation may be created merely to force an observation date.

Extended source absence must remain explicit. It is not by itself a PR-B Core failure.

## 7. Modeling dataset boundary

### 7.1 Existing Document / Extended foundations

Document-only foundation：

```text
V03DocumentRiskSnapshot + MarketOutcomeLabel
→ V04ModelingDatasetBuilder
```

Existing Extended market-augmented foundation：

```text
V04ModelingRecord + PreListingMarketFeatureSnapshot
→ V04MarketAugmentedDatasetBuilder
```

Its historical combined order is:

```text
100 Production Document features
+
20 Extended Market features
```

### 7.2 Downstream PR-D implication

PR-B Core introduces a distinct 30-position versioned artifact. PR-D must therefore make an explicit, versioned canonical-dataset decision about Core and optional Extended feature groups rather than silently mutating the old 120-position Extended join contract.

Any PR-D join must exact-match identity/governance fields such as `case_id`, stock, listing date/cohort and split. Blind outcome cannot form a modeling record；2025 remains feature-only until formally opened.

## 8. Formal modeling sequence

```text
PR-B Market-X Core                 COMPLETE / FROZEN
→ PR-C 5D Outcome Policy Freeze    NEXT / NOT STARTED
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
```

Formal split:

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Development 用于 threshold/feature/model policy；2024 用于冻结方案 validation；2025 policy freeze 前只准备 X，不读取 y。

Formal comparison framework：

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Only comparisons using the same cohort/target/split/preprocessing/model family can support Production-vs-Oracle attribution.

## 9. Product boundary

Later PR-G / PR-H：

```text
Document assessment
+ Market context
+ frozen model output
+ explainability drivers
+ Evidence / provenance
+ missingness / conflicts
→ Market Agent / Final Supervisor
→ final report
→ Streamlit
```

Market Agent can explain frozen model/context but cannot override model scores or manufacture market evidence.

Streamlit only consumes `IPOAnalysisService` / a controlled upper service and cannot directly read raw Market CSVs, model binaries or Parser/Agent internals.

## 10. Module responsibilities

- `app/`: presentation only；
- `src/ipo_risk/services/`: controlled product-facing business entry；
- `src/ipo_risk/workflows/`: Document workflow/state/failure routing；
- `src/ipo_risk/agents/`: Financial/Legal/Business；future Market Agent after model freeze；
- `src/ipo_risk/skills/`: deterministic calculations；
- `src/ipo_risk/parsers/`: PDF → `list[DocumentChunk]` including page/bbox；
- `src/ipo_risk/retrieval/`: Evidence discovery/ranking; current research frozen；
- `src/ipo_risk/providers/`: external source adapters; credentials from environment only；
- `src/ipo_risk/market/`: market labels/Core/Extended features/governance/validation；
- `src/ipo_risk/modeling/`: Document/Oracle/Market dataset/modeling boundary；
- `src/ipo_risk/predictors/`: current rule-based compatibility, later frozen statistical model adapter；
- `src/ipo_risk/evaluation/`: research/evaluation/regression；
- `src/ipo_risk/reporting/`: structured reports and later final synthesis output。

## 11. Protected interfaces

The following are protected architecture/public boundaries:

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

Any change must state compatibility impact and add contract tests.

The frozen PR-B Core implementation does not alter these protected interfaces；it hardens existing market research/orchestration code and adds a script-level materialization entry point.

## 12. Evidence / Calculation / Verification

Formal RiskItem must have Evidence. Numeric conclusions require auditable deterministic Calculation containing inputs/formula/result/unit/evidence IDs/success-error. Verifier/Supervisor cannot create original Evidence. Unsupported conclusions remain pending/needs_review/rejected/unavailable rather than being invented.

## 13. Current execution state

Completed/frozen：

```text
v0.3 Document Intelligence
Retriever V3 research
V04 Market Foundation contracts
V04 Document feature contract
V04 Extended Pre-listing Market feature contract
Oracle modeling foundations
PR-A 438-case Document + Oracle materialization
PR-B 438-case Market-X Core + governed EOD materialization
```

Frozen execution evidence：

```text
targeted tests                  68 passed
full pytest                    1303 passed
5-case pilot                   5 / 5
438-case full materialization  438 / 438
resume + determinism           438 checked / 0 mismatches / PASS
2025 blind y accessed          NO
```

PR-C is the next formal milestone and remains **NOT STARTED**.

Frozen PR-B evidence / historical audit records：

- [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md) — authoritative measured completion report；
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) — frozen acceptance / reproducibility contract；
- [`V04_ROLE_A_CROSS_TEAM_PREP.md`](V04_ROLE_A_CROSS_TEAM_PREP.md) — historical preparation record；
- [`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md) — historical execution handoff。

The Role-A preparation/handoff files are no longer current execution instructions.

## 14. Retriever / LLM future position

Retriever/LLM optimization is deferred until PR-E. If Oracle is strong while Production is materially weak under a fair comparison, v0.5 may reopen Retriever/LLM/Agent research with a new unseen holdout. Historical Locked 10 is already consumed and cannot be reused as blind.

## 15. Source of truth

Current execution / governance source of truth：

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
2. [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)
3. [`ROADMAP.md`](ROADMAP.md)
4. [`PROJECT_SPEC.md`](PROJECT_SPEC.md)
5. this architecture document
6. [`DATA_SCHEMA.md`](DATA_SCHEMA.md)
7. [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md)

Frozen PR-B evidence is carried by [`V04_PR_B_COMPLETION_REPORT.md`](V04_PR_B_COMPLETION_REPORT.md), [`../reports/frozen/v04_pr_b_market_x_core_manifest.json`](../reports/frozen/v04_pr_b_market_x_core_manifest.json), and [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md).
