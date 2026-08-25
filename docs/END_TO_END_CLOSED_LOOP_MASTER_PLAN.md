# HK IPO Risk Agents — End-to-End Closed Loop Master Plan

> Status snapshot: **2026-08-25**  
> Current Gate: **PR-H PARTIAL / BLOCKED**  
> Program sequence: **v0.4.3 Baseline Freeze → Competition Hardening → v0.4.5 COMPETITION_READY → Submission**

## 1. Program objective

项目分两段完成：

### Baseline closed loop

```text
Prospectus PDF
→ Parser / Retriever
→ Financial / Legal / Business Agents
→ Evidence / deterministic Calculation
→ Verifier / Document Supervisor
→ Production Document-X
→ Market-X
→ Outcome / Canonical Dataset
→ Baseline / LightGBM / Explainability
→ Market Agent / Final Supervisor
→ Streamlit / Final Report
```

### Competition hardening

```text
CH-0 Scorecard Lock
→ CH-1 Multi-Horizon Diagnosis
→ CH-2 Document Benchmark / Targeted Hardening
→ CH-3 Market Intelligence
→ CH-4 Multi-Agent Conflict / Trace
→ CH-5 Evidence Viewer / Competition Product
→ CH-6 Formal Evaluation / Freeze
→ Submission
```

原则：先证明问题在哪里，再优化；不把弱 5D AUC 自动解释为“需要更复杂模型”。

## 2. Frozen foundation

```text
PR-A Document X                 COMPLETE / FROZEN
PR-B Market-X Core              COMPLETE / FROZEN
PR-C 5D Outcome                 COMPLETE / FROZEN
PR-D Canonical Dataset          COMPLETE / FROZEN
Oracle v2                       COMPLETE / FROZEN / EVALUATION-ONLY
PR-E Baseline + Oracle          COMPLETE / FROZEN
PR-F LightGBM + Explainability  COMPLETE / FROZEN
PR-G Market Agent + Supervisor  COMPLETE / FROZEN
PR-H Full E2E                   PARTIAL / BLOCKED
```

Measured anchors:

```text
Official cases                  438
Production Document-X           438 / 438, 100 dims
Market-X Core                   438 / 438, 30 positions
5D outcome                      424 / 438
Canonical model-ready           424 = 354 Dev + 70 Val
Oracle v2                       98 materialized / 96 strict
Oracle split                    77 Dev / 19 Val
2025 Blind y accessed           false
```

## 3. Current market readiness

Market-X Core remains frozen. Optional Extended readiness is now:

```text
HSI return / volatility         438 / 438
HKEX turnover 20D               438 / 438
industry return                   0 / 438
```

Industry source history exists, but the delivered company classification does not provide a PIT-safe historical effective mapping. Production industry features remain intentionally unavailable. Missing is explicit; no proxy or zero fill is allowed.

## 4. Modeling governance and finding

Time policy remains:

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

Frozen feature arms:

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

PM=M under the frozen tree policy and all 100 Production Document features have zero split/gain/SHAP use. Oracle `OM-M=-0.0143`, 95% paired-bootstrap `[-0.3171,0.2917]` on 19 Validation cases.

This is a **diagnostic signal**:

- current 5D target may be poorly aligned with structural prospectus risk;
- 100-dimensional Document representation may be sparse/coarse;
- 354 training cases are small relative to feature complexity;
- automatic Document extraction quality still requires direct benchmark;
- short-horizon IPO outcomes may be driven more by point-in-time market/issuance context.

It is not permission to tune on 2024, invert scores, or call the experiment a failure of prospectus information itself.

## 5. PR-H objective

PR-H closes the baseline product, not the research question.

Required real-case path:

```text
3–5 real 2024 IPOs
PDF
→ Risk / Evidence / Calculation / page-bbox
→ governed Market-X runtime
→ frozen PR-F per-case score + SHAP handoff
→ Rule
→ Final Supervisor
→ 13-section report / Streamlit
```

Remaining formal blockers:

1. original frozen PR-F runtime or pre-existing hash-bound handoff;
2. at least three matching real 2024 prospectus PDFs;
3. full 3–5 case matrix with all four channels governed and available.

PR-H PASS creates `v0.4.3 BASELINE E2E FREEZE`.

## 6. Competition strategy

### Track A — Risk Intelligence / Auditability

```text
Risk extraction
→ Evidence / Calculation / page / bbox
→ Verifier
→ conflict / re-check / human review
→ auditable Final Supervisor
```

Targets:

```text
key risk quality target >= 80%
key Evidence Recall     >= 85%
Agent/Tool/Evidence trace = 100%
```

### Track B — Market Warning / Predictive Validation

```text
PIT Market / IPO context
+ governed model signal
+ SHAP / uncertainty
+ 1D / 5D / 20D / 60D outcomes
→ explainable warning
```

### Track C — Multi-Agent Product

```text
real conflict detection
→ Evidence re-check
→ Skill / Verifier challenge
→ Supervisor arbitration
→ Evidence Viewer / Agent Trace
```

## 7. Competition decision logic

### CH-1

Build independent 1D / 20D / 60D outcomes plus market-adjusted return, drawdown and volatility. Keep frozen 5D unchanged. Compare M/P/P-Core/PM/O/OM under the same time governance.

### CH-2

Benchmark each current formal risk with Precision / Recall / F1 / Evidence Recall / Evidence Precision. Attribute failures to retrieval, parser/table, semantic extraction, calculation, rule or Gold uncertainty. Only the worst 2–3 classes receive targeted changes.

### CH-3

Prioritize IPO-specific point-in-time signals: recent IPO count, break rate, recent performance, HSI, turnover/activity, and PIT-safe comparable context. Market Agent outputs interpretation plus provenance, not a second opaque predictor.

### CH-4

Upgrade parallel Agent outputs to observable collaboration: conflict detection → re-check → challenge → arbitration. Preserve unresolved uncertainty.

### CH-5

Build five competition workspaces: Risk Command Center, Risk Map, Evidence Viewer, Market & Model, Agent Trace.

### CH-6

Stop feature growth and freeze benchmark, market set, multi-horizon evaluation, model/SHAP, real conflicts, product UI and final regression evidence.

## 8. Five-person execution model

```text
A  integration / CI / Gate / release / submission
B  Document benchmark / Evidence / targeted fixes
C  Market / PIT / outcome data
D  feature audit / multi-horizon / model / statistics
E  conflict / Supervisor / Evidence Viewer / UI/demo
```

CH-1/2/3 run in parallel. CH-4/5 overlap once their input contracts stabilize. A performs an integration checkpoint every 2–3 days.

Detailed assignments: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).

## 9. Final release sequence

```text
PR-H PASS
→ v0.4.3 Baseline Freeze
→ CH-0
→ CH-1 / CH-2 / CH-3 parallel
→ CH-4 / CH-5
→ Competition Beta
→ CH-6 Formal Freeze
→ v0.4.5 COMPETITION_READY
→ Submission package
→ Demo rehearsal
```

Detailed competition acceptance and submission tree: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).

## 10. Permanent governance

- LLM performs semantic extraction/interpretation; deterministic code owns calculations, identities, feature vectors, hashes and model fitting/scoring;
- formal RiskItem requires Evidence; exact numeric claims require Calculation;
- Verifier / Supervisor do not invent raw Evidence;
- missing does not mean zero/safe;
- 2025 Blind y stays closed until formal release policy says otherwise;
- 2024 Validation is not recycled into a tuning set;
- `uncalibrated_model_score` is never presented as real probability;
- frozen PR-A–PR-F artifacts are not silently rewritten by competition work.
