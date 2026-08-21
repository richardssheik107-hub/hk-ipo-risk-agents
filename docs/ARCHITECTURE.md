# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-21**  
> Stable document baseline: **v0.3.0 RELEASED / FROZEN**  
> PR-A Document materialization: **COMPLETE / FROZEN**  
> Active program: **v0.4 End-to-End Closed Loop**  
> Current formal milestone: **PR-B — Market-X Core + Governed EOD Store**

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
Pre-listing Market X
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

## 5. Pre-listing Market X — current PR-B boundary

Market-X semantic contract 已经存在并冻结：

```text
Governed reference data
+ prior IPO information known before target listing
→ PreListingMarketFeatureEngine
→ PreListingMarketFeatureSnapshot
→ MARKET_FEATURE_MANIFEST_V1
→ Market Feature Vector
```

版本：

```text
v04_prelisting_market_features_v1
v04_market_features_v1
```

固定 10 raw features：

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

每个 raw feature 有独立 `__missing` indicator，共 20 个 ordered positions。

PIT 硬边界：

```text
market_data_date <= observation_date < target_listing_date
```

目标上市日及之后的数据不得进入 X。Prior IPO outcomes 只有在其 target trading date 已经发生且不晚于目标 IPO observation date 时才能作为历史上下文。

### 5.1 Existing implementation

```text
src/ipo_risk/schemas/market_features.py
src/ipo_risk/market/features.py
src/ipo_risk/providers/market_reference.py
src/ipo_risk/providers/competition_market.py
src/ipo_risk/modeling/market_dataset.py
scripts/build_v04_ipo_eod_store.py
```

当前 `InMemoryMarketReferenceDataProvider` 是 deterministic test provider，不是完整真实来源适配器。

### 5.2 Current real-source gaps

仍缺：

```text
governed HSI daily history
authoritative industry→benchmark mapping
governed industry-index histories
governed HK total-market turnover
```

禁止：

- Hang Seng Bank 代替 HSI；
- 用 workbook industry name 猜 benchmark；
- 用 single-security `S_DQ_AMOUNT` 代替全市场 turnover；
- 用 0 静默填补真实 source missing。

PR-B 的工程目标是把真实来源接入现有 frozen engine，并完成 orchestration / provenance / coverage / PIT / determinism，而不是重写 feature semantics。

## 6. Modeling dataset boundary

Document-only foundation：

```text
V03DocumentRiskSnapshot + MarketOutcomeLabel
→ V04ModelingDatasetBuilder
```

Market-augmented foundation：

```text
V04ModelingRecord + PreListingMarketFeatureSnapshot
→ V04MarketAugmentedDatasetBuilder
```

Combined ordered vector：

```text
100 Production Document features
+
20 Market features
```

Join 必须 exact-match：`case_id`、stock、cohort/listing date、split 等。Blind outcome 不能形成 modeling record；2025 仅允许 feature-only blind export。

## 7. Formal modeling sequence

```text
PR-B Market-X
→ PR-C 5D Outcome Policy Freeze
→ PR-D Canonical Model-ready Dataset
→ PR-E Baseline + Oracle Diagnostic
→ PR-F LightGBM + Explainability
```

正式切分：

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

只有在相同 cohort/target/split/preprocessing/model family 下比较，Production vs Oracle gap 才可解释。

## 8. Product boundary

后续 PR-G / PR-H：

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

Market Agent 可以解释冻结模型和市场上下文，不能绕过模型自己修改 score 或制造 market evidence。

Streamlit 只能通过 `IPOAnalysisService` / 受控上层 service 获取业务结果，不能直接读取 Market CSV、模型二进制、Parser/Agent 内部对象。

## 9. Module responsibilities

- `app/`: presentation only；
- `src/ipo_risk/services/`: controlled product-facing business entry；
- `src/ipo_risk/workflows/`: Document workflow/state/failure routing；
- `src/ipo_risk/agents/`: Financial/Legal/Business；future Market Agent after model freeze；
- `src/ipo_risk/skills/`: deterministic calculations；
- `src/ipo_risk/parsers/`: PDF → `list[DocumentChunk]` including page/bbox；
- `src/ipo_risk/retrieval/`: Evidence discovery/ranking; current research frozen；
- `src/ipo_risk/providers/`: external source adapters; credentials from environment only；
- `src/ipo_risk/market/`: market labels/features/governance/validation；
- `src/ipo_risk/modeling/`: Document/Oracle/Market dataset/modeling boundary；
- `src/ipo_risk/predictors/`: current rule-based compatibility, later frozen statistical model adapter；
- `src/ipo_risk/evaluation/`: research/evaluation/regression；
- `src/ipo_risk/reporting/`: structured reports and later final synthesis output。

## 10. Protected interfaces

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

## 11. Evidence / Calculation / Verification

Formal RiskItem must have Evidence. Numeric conclusions require auditable deterministic Calculation containing inputs/formula/result/unit/evidence IDs/success-error. Verifier/Supervisor cannot create original Evidence. Unsupported conclusions remain pending/needs_review/rejected/unavailable rather than being invented.

## 12. Current execution state

Completed/frozen:

```text
v0.3 Document Intelligence
Retriever V3 research
V04 Market Foundation contracts
V04 Document feature contract
V04 Pre-listing Market feature contract
Oracle modeling foundations
PR-A 438-case Document + Oracle materialization
```

Current formal milestone:

```text
PR-B
real governed reference sources
→ canonical Market-X orchestration
→ 438-case coverage
→ PIT audit
→ provenance / failure report
→ deterministic rerun
→ Gate review
```

Role A/Codex contract:

- [`V04_ROLE_A_CROSS_TEAM_PREP.md`](V04_ROLE_A_CROSS_TEAM_PREP.md)
- [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md)
- [`V04_ROLE_A_CODEX_HANDOFF.md`](V04_ROLE_A_CODEX_HANDOFF.md)

## 13. Retriever / LLM future position

Retriever/LLM optimization is deferred until PR-E. If Oracle is strong while Production is materially weak under a fair comparison, v0.5 may reopen Retriever/LLM/Agent research with a new unseen holdout. The historical Locked 10 is already consumed and cannot be reused as blind.

## 14. Source of truth

1. [`END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)
2. [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md)
3. [`research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`](research/V04_PR_B_INTEGRATION_ACCEPTANCE.md) for current PR-B implementation/Gate
4. [`ROADMAP.md`](ROADMAP.md)
5. [`PROJECT_SPEC.md`](PROJECT_SPEC.md)
6. this architecture document
7. [`DATA_SCHEMA.md`](DATA_SCHEMA.md)
