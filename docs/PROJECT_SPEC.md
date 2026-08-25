# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-25**  
> Baseline: **PR-A–PR-G COMPLETE / FROZEN**  
> Current formal Gate: **PR-H PARTIAL / BLOCKED**  
> Target release: **v0.4.3 baseline → v0.4.5 COMPETITION_READY**

## 1. Product definition

HK IPO Risk Agents 是一个 Evidence-driven、多 Agent 协同、可审计的港股 IPO 招股书风险分析与上市后风险预警系统。

```text
Prospectus PDF
→ Parser / Retriever
→ Financial / Legal / Business Agents
→ Evidence / Calculation
→ Verifier / Document Supervisor
→ Document-X
→ governed Market-X
→ Outcome / Modeling
→ Market Agent / Final Supervisor
→ Report / Streamlit
```

产品不把单一模型分数当最终结论，也不把未校准 score 描述为实际下跌概率或投资建议。

## 2. Current v0.4 state

```text
v0.3 Document Intelligence          COMPLETE / FROZEN
PR-A Document-X                     COMPLETE / FROZEN
PR-B Market-X Core                  COMPLETE / FROZEN
PR-C 5D Outcome                     COMPLETE / FROZEN
PR-D Canonical Dataset              COMPLETE / FROZEN
Oracle v2                           COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle              COMPLETE / FROZEN
PR-F LightGBM + Explainability      COMPLETE / FROZEN
PR-G Market Agent + Supervisor      COMPLETE / FROZEN
PR-H Full E2E                       PARTIAL / BLOCKED
```

Measured production cohort:

```text
438 official cases
438 Document-X / 100 dims
438 Market-X Core / 30 positions
424 valid 5D outcomes
424 canonical = 354 Dev + 70 Val
Oracle v2 = 98 materialized / 96 strict = 77 Dev + 19 Val
2025 Blind y accessed = NO
```

## 3. Formal Document risk scope

### Financial

```text
cash_runway
continuous_loss
revenue_growth
customer_concentration
supplier_concentration
```

### Legal

```text
redemption_rights
material_litigation_compliance
```

### Business

```text
precommercial_product
```

Every formal RiskItem requires real Evidence. Exact numeric claims use deterministic Calculation/Skill. `pending / rejected / needs_review` remain explicit states rather than being silently dropped.

## 4. Trust boundaries

### LLM may

- extract and interpret semantics;
- assess contextual relevance;
- generate constrained explanations.

### LLM may not

- replace deterministic financial calculations;
- create verified risk without Evidence;
- invent market facts or missing values;
- change frozen model score;
- call an uncalibrated score a probability;
- bypass Verifier / Supervisor governance.

### Deterministic code owns

```text
calculation
schema / identity
PIT guards
feature vectorization
hash / manifest
model fitting / scoring
reproducibility
```

## 5. Market specification

### Core

Frozen `Market-X Core`:

```text
438 / 438
15 raw + 15 missing indicators = 30 positions
strict PIT audited
```

### Extended current readiness

```text
HSI 5D / 20D / volatility       438 / 438
HKEX turnover 20D                438 / 438
industry return                    0 / 438
```

Industry classification remains PIT-blocked because the available company classification lacks historically effective/listing-time semantics. Industry return stays unavailable until a valid temporal mapping exists.

Runtime source-of-truth is governed `PreListingMarketFeatureSnapshot` or a lossless governed projection. Legacy `MarketSnapshot` is compatibility-only.

## 6. Production / Oracle isolation

Production:

```text
real Prospectus
→ Parser / Retriever / Agents
→ Snapshot
→ Production Document-X
```

Oracle:

```text
Reviewed Expert Gold
→ Oracle feature builder
→ Oracle-X
```

Oracle is `evaluation_only=true` and `production_consumable=false`. Gold answers, Gold pages or manual labels never enter Production X.

## 7. Frozen predictive baseline

Frozen arms:

```text
M   Market only
P   Production Document only
O   Oracle Document only
PM  Market + Production
OM  Market + Oracle
```

PR-F Full Production 2024:

```text
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM and M are prediction-equivalent under the frozen LightGBM policy; Production Document features received zero split/gain/SHAP use. Oracle `OM-M=-0.0143`, bootstrap interval crosses zero on a 19-case Validation intersection.

Formal interpretation: stable Document increment is **not validated under the current 5D target/sample/representation/model**. This does not prove prospectus information is useless. The model remains an auxiliary warning channel.

## 8. PR-H baseline product Gate

Required path:

```text
3–5 real 2024 IPOs
PDF
→ Document / Evidence / Calculation
→ governed Market-X
→ frozen per-case PR-F score + SHAP
→ Rule
→ Final Supervisor
→ 13-section report / Streamlit
```

Current blockers:

1. restore original frozen PR-F runtime or pre-existing hash-bound sanitized handoff;
2. provide at least three matching real 2024 prospectus PDFs;
3. run the 3–5 case matrix with all required governed channels.

PR-H does **not** require a higher 5D AUC. It requires correct consumption, traceability, honest degradation and reproducibility. PASS creates `v0.4.3 BASELINE E2E FREEZE`.

## 9. Competition product objective

Competition version is judged on three complementary capabilities.

### Risk Intelligence / Auditability

```text
risk extraction
Evidence / Calculation / page / bbox
Verifier
human review / audit trail
```

Targets:

```text
key risk quality target >= 80%
key Evidence Recall     >= 85%
```

### Market Warning / Predictive Validation

```text
PIT IPO context / Market Environment
+ model score / SHAP / uncertainty
+ 1D / 5D / 20D / 60D validation
```

### Multi-Agent Collaboration

```text
conflict detection
→ Evidence re-check
→ Skill / Verifier challenge
→ Supervisor arbitration
→ resolved / unresolved uncertainty
```

Target: `Agent / Tool / Evidence traceability = 100%`.

## 10. Competition hardening rules

### CH-1

Build independent 1D/20D/60D outcomes, market-adjusted returns and risk outcomes; keep frozen 5D unchanged.

### CH-2

Benchmark every formal risk with Precision/Recall/F1/Evidence Recall/Evidence Precision. Only benchmark-proven weak classes receive targeted Retriever/Table/LLM/Skill changes.

### CH-3

Enhance PIT-safe IPO Heat, recent IPO performance, HSI, turnover/activity and comparable context. No fake proxy.

### CH-4

Implement real conflict/re-check/challenge/arbitration and preserve unresolved uncertainty.

### CH-5

Final competition workspaces: Risk Command Center, Risk Map, Evidence Viewer, Market & Model, Agent Trace.

### CH-6

Freeze all benchmark/model/market/trace/product evidence and create `v0.4.5 COMPETITION_READY`.

## 11. Time / Blind governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 is not recycled into a tuning set. 2025 y remains closed until formally authorized. `ROC-AUC < 0.5` is not permission to reverse score direction after seeing Validation.

## 12. Submission definition of done

Final submission must contain:

```text
source + configs + environment
reproducible runbook
Document benchmark
Market/PIT methodology
multi-horizon model evaluation
SHAP / ablation / error analysis
real Evidence and conflict cases
competition Streamlit
3–5 stable star demos
final reports/screenshots
```

Detailed execution: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).  
Detailed acceptance/submission: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).
