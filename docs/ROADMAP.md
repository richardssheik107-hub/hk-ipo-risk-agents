# Roadmap

> Status snapshot: **2026-08-25**  
> Current formal Gate: **PR-H — Streamlit Full E2E + 3–5 real 2024 IPO demo**  
> Execution strategy: **Freeze baseline → diagnose signal → targeted hardening → competition product → submission**

## 1. Current state

| Phase | Status | Frozen / active result |
| --- | --- | --- |
| v0.3 Document Intelligence | COMPLETE / FROZEN | real PDF → Evidence → Agents → Verifier → Supervisor |
| PR-A Document materialization | COMPLETE / FROZEN | 438/438 Production Document-X, 100 dims |
| PR-B Market-X Core | COMPLETE / FROZEN | 438/438, 30 positions, PIT audited |
| PR-C 5D Outcome | COMPLETE / FROZEN | 424 available / 14 explicit unavailable |
| PR-D Canonical Dataset | COMPLETE / FROZEN | 424 = 354 Development + 70 Validation |
| Oracle v2 | COMPLETE / FROZEN / EVALUATION-ONLY | 98 materialized / 96 strict = 77 Dev + 19 Val |
| PR-E Baseline + Oracle | COMPLETE / FROZEN | time-aware baseline + Oracle diagnostic |
| PR-F LightGBM + Explainability | COMPLETE / FROZEN | LightGBM / SHAP / calibration assessment / ablation / error analysis |
| PR-G Market Agent + Final Supervisor | COMPLETE / FROZEN | real 2410.HK, 13 sections, deterministic traceability |
| PR-H Full E2E | **PARTIAL / BLOCKED** | governed runtime implemented; formal 3–5 case gate not passed |
| v0.4.3 Baseline E2E Freeze | NOT CREATED | after PR-H PASS |
| CH-0..CH-6 | PLANNED | formal competition hardening |
| v0.4.5 | PLANNED | COMPETITION_READY / Submission Freeze |

## 2. PR-H remaining blockers

PR-H is not blocked by missing code design. It is blocked by immutable/runtime inputs required for the formal gate:

1. restore original frozen PR-F runtime or an already generated hash-bound sanitized handoff;
2. provide at least 3 matching real 2024 prospectus PDFs;
3. execute 3–5 cases with Document / Market / Model / Rule all governed and available;
4. pass determinism / provenance / Evidence / Blind checks.

No retraining, reconstruction, score inversion or 2024 retuning is allowed merely to unblock the UI.

## 3. Current measured anchors

```text
Official 2020–2024 universe          438
Production Document-X                438 / 438, 100 dims
Market-X Core                        438 / 438, 30 positions
5D outcome                           424 / 438
Canonical model-ready                424 = 354 Dev + 70 Val
Oracle v2 strict                     96 = 77 Dev + 19 Val
2025 Blind y accessed                NO
```

Market Extended current facts:

```text
HSI 5D / 20D / volatility readiness      438 / 438
HKEX turnover 20D readiness               438 / 438
production industry return                  0 / 438
industry reason                           PIT_BLOCKED / missing classification
```

Industry features remain explicitly unavailable until historically effective/PIT-safe classification exists.

## 4. Frozen modeling finding

PR-E / PR-F establish an honest baseline, not a competition ceiling.

```text
PR-F Full Production 2024
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

PM and M are prediction-equivalent under the frozen LightGBM policy; Production Document features received zero split/gain/SHAP use. Oracle `OM-M ROC-AUC = -0.0143` with 95% bootstrap `[-0.3171, 0.2917]` on only 19 Validation cases.

Interpretation: current 5D target / representation / sample / model did not validate stable Document increment. It does **not** prove prospectus risk information has no value. Competition work therefore diagnoses where signal is lost before choosing a new model.

## 5. Strict sequence

```text
NOW
PR-H real-case completion
→ v0.4.3 BASELINE E2E FREEZE
→ CH-0 Scope / Metrics Lock
→ CH-1 Multi-Horizon Outcome + Predictive Diagnosis
→ CH-2 Document Benchmark + Targeted Hardening
→ CH-3 Market Intelligence / IPO Context
→ CH-4 Multi-Agent Conflict + Full Trace
→ CH-5 Evidence Viewer + Competition Product
→ Competition Beta
→ CH-6 Formal Evaluation / Freeze
→ v0.4.5 COMPETITION_READY
→ Submission + Demo Rehearsal
```

CH-1 / CH-2 / CH-3 are executed substantially in parallel after CH-0. CH-4 / CH-5 begin once their data contracts are stable enough; they do not wait for every research experiment to finish.

## 6. Competition Scorecard

### Risk Intelligence

```text
Precision / Recall / F1 by risk
Evidence Recall / Evidence Precision
key risk quality target >= 80%
key Evidence Recall     >= 85%
```

### Predictive validation

```text
1D / 5D / 20D / 60D
M / P / P-Core / PM / O / OM
ROC-AUC / PR-AUC / Brier
regression metrics where appropriate
bootstrap uncertainty
```

### Multi-Agent / Auditability

```text
Agent / Tool / Evidence traceability = 100%
real conflict cases                  >= 3
unresolved uncertainty preserved     = 100%
```

## 7. Route decisions after diagnosis

```text
Oracle strong / Production weak
→ prioritize Document pipeline / representation

20D/60D stronger than 5D
→ structural Document risk is a longer-horizon signal

Market strong on 1D/5D
→ prioritize PIT IPO Heat / market context for short horizon

all predictive arms weak
→ keep model auxiliary and make Risk Intelligence / Evidence / Multi-Agent auditability the primary competition value
```

No route is selected by cherry-picking one Validation metric.

## 8. Compact schedule

| Window | Target |
| --- | --- |
| Day 1–3 | PR-H close + v0.4.3 freeze |
| Day 3–4 | CH-0 Scorecard lock |
| Day 4–8 | CH-1 / CH-2 / CH-3 first pass in parallel |
| Day 8–12 | targeted Document + Market + multi-horizon iteration |
| Day 10–14 | CH-4 real conflict resolution |
| Day 10–16 | CH-5 Evidence Viewer / product integration |
| Day 15–18 | Competition Beta Gate |
| Day 18–21 | CH-6 formal evaluation / regression / freeze |
| Final | submission package + demo rehearsal |

Detailed owners: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).  
Detailed hardening and submission acceptance: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).
