# HK IPO Risk Agents — Current Architecture

> Status snapshot: **2026-08-25**  
> Baseline components PR-A–PR-G: **COMPLETE / FROZEN**  
> Current formal Gate: **PR-H PARTIAL / BLOCKED**  
> Competition target: **v0.4.5 COMPETITION_READY**

## 1. Architecture form

项目保持模块化单体：一个仓库、一个主要 Python 应用，通过稳定 Pydantic Schema / Protocol 连接模块。当前不引入与闭环无关的 Kafka、Redis queue、Neo4j、Kubernetes 或微服务拆分。

```text
Streamlit / Report
        ↓
IPOAnalysisService / controlled upper service
        ↓
Parser / Retriever / Domain Agents / Skills / Verifier
        ↓
Document Supervisor / IPOAnalysisResult
        ↓
Document Snapshot / Production Document-X
        ↓
Market-X Core (+ governed optional Extended)
        ↓
Outcome / Canonical Dataset
        ↓
Baseline / LightGBM / Explainability
        ↓
Market Agent / Final Supervisor
        ↓
Competition Evidence Viewer / Agent Trace / Final Report
```

禁止反向依赖：Agent 不操作前端；UI 不直接读取任意 raw model/data files；Parser 不依赖 Agent；Schema 不依赖具体实现。

## 2. Protected interfaces

跨阶段修改必须单独审查：

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

新增 real component 必须有 contract test 并通过 controlled registry/wiring 注册。

## 3. Document runtime

```text
Prospectus PDF
→ DocumentParser
→ DocumentChunk(page / bbox / text / metadata)
→ Retriever
→ Evidence
→ Financial / Legal / Business Agents
→ deterministic Skills / Calculation
→ Verifier
→ Document Supervisor
→ IPOAnalysisResult
```

规则：

- verified RiskItem 必须有 Evidence；
- 精确数值由 deterministic code 计算；
- LLM unavailable / partial 必须显式降级；
- Verifier / Supervisor 不创造原始 Evidence；
- failure / pending / needs_review 不 silent drop。

## 4. Frozen Document modeling boundary

```text
IPOAnalysisResult
→ V03DocumentRiskSnapshot
→ v04_document_features_v1
→ Production Document-X
```

Frozen facts:

```text
438 / 438 Production Document-X
100 dimensions
0 Production failures
0 silent drops
```

Competition CH-2 可以在不重写 frozen artifact 的前提下建立新的 benchmark/representation version；任何新 `P-Core` 必须预先定义、独立版本化，不能查看 2024 后事后挑 feature。

## 5. Market architecture

### Core — frozen

```text
schema  v04_ipo_market_context_features_v1
policy  ipo_market_context_policy_v1
15 raw + 15 missing indicators = 30 positions
438 / 438
```

### Extended — governed optional

Current readiness:

```text
HSI return / volatility     438 / 438
HKEX turnover 20D           438 / 438
industry return               0 / 438
```

12 HSCI official price series and HKEX turnover source are governed. Production industry returns remain PIT-blocked because the available company classification lacks historical effective/listing-time semantics. Static mapping, fake benchmark and neutral zero are prohibited.

Runtime source-of-truth is `PreListingMarketFeatureSnapshot` or a lossless governed projection. Legacy `MarketSnapshot` is v0.3 compatibility only.

## 6. Outcome / canonical architecture

Frozen baseline:

```text
PR-C FiveDayOutcomeTarget       424 available / 14 unavailable
PR-D canonical dataset          424 = 354 Dev + 70 Val
```

Competition CH-1 adds independently versioned outcomes rather than mutating PR-C:

```text
1D / 20D / 60D returns
market-adjusted returns
20D / 60D drawdown
20D / 60D volatility
severe-break flag
```

All new targets preserve identity, availability/missing reason, time split and Blind governance.

## 7. Production / Oracle separation

Production:

```text
real PDF → automated pipeline → Production X
```

Oracle:

```text
Reviewed Expert Gold → Oracle v2 X
```

Oracle frozen facts:

```text
98 materialized
96 strict usable
77 Dev / 19 Val
142 features
evaluation_only = true
production_consumable = false
```

Gold answer/page/label cannot leak into Production runtime or Production X.

## 8. Modeling architecture

Frozen arms:

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

Frozen PR-F finding: Production `M=0.4246`, `P=0.5000`, `PM=0.4246` ROC-AUC on 2024; PM=M under the frozen tree policy. Scores remain `uncalibrated_model_score`.

Competition modeling does not start by replacing LightGBM. It first diagnoses:

```text
Document extraction quality
→ Document representation quality
→ horizon alignment
→ Market / IPO context strength
→ only then model-family value
```

## 9. PR-G / PR-H boundary

PR-G is COMPLETE / FROZEN:

```text
Document Supervisor
+ Market Context
+ frozen model evidence / optional per-case model projection
+ Rule
→ Final Supervisor
→ 13-section report
```

PR-H current Gate must prove the full governed path on 3–5 real 2024 IPOs. Missing frozen PR-F runtime/handoff and insufficient real PDFs are capability blockers; they do not authorize retraining.

## 10. Competition architecture additions

### CH-2 Document Benchmark

Benchmark remains evaluation infrastructure, not runtime authority. It measures per-risk Precision/Recall/F1/Evidence metrics and error attribution.

### CH-3 Market Intelligence

Market Agent may produce structured `Market Environment` interpretation only from governed PIT facts, with reasons and provenance.

### CH-4 Conflict / Trace

Target collaboration path:

```text
Agent claim
→ Conflict Detector
→ Evidence re-check / targeted retrieval
→ Skill
→ Verifier challenge
→ Final Supervisor arbitration
```

Trace records Agent / Tool / Evidence / Calculation / resolution identity. Unresolved conflict remains visible.

### CH-5 Product

Final workspaces:

```text
Risk Command Center
Risk Map
Evidence Viewer
Market & Model
Agent Trace
```

UI remains a consumer of governed outputs and cannot fabricate unavailable state.

## 11. Reproducibility / artifact policy

Large runtime artifacts and licensed raw data stay outside Git. Git contains code, tests, small manifests/reports and hashes. Cross-machine handoff verifies source revision + manifest + SHA256 and excludes labels/Blind data unless explicitly authorized.

## 12. Time / Blind governance

```text
2020–2023  Development
2024       Validation
2025       Blind Test
```

2024 is not reused as a tuning set. 2025 Blind y remains inaccessible until a formal release decision. Competition work does not relax this boundary.
