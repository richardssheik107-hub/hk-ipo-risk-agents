# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-25**  
> Baseline: **PR-A–PR-G COMPLETE / FROZEN**  
> Current Gate: **PR-H PARTIAL / BLOCKED**  
> Target: **v0.4.5 COMPETITION_READY**

## 1. Product definition

HK IPO Risk Agents 是一个 Evidence-driven、LLM-enhanced、多 Agent 协同、可审计的港股 IPO 招股书风险分析与上市后风险预警系统。

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial / Legal / Business Agents
→ LLM semantic reasoning where appropriate
→ deterministic Calculation / Verifier
→ governed Market Skills + LLM Market Agent
→ Model / Rule auxiliary signals
→ LLM Final Supervisor
→ conflict / targeted re-check / uncertainty
→ Report / Evidence Viewer / Agent Trace / Human Review
```

## 2. Competition scope

正式 Competition Release 必须覆盖：

```text
long-PDF parsing
standard financial risk
non-standard legal/business risk
LLM grounded semantic extraction
multi-agent collaboration + Skill orchestration
fundamental + market-sentiment fusion
1D / 5D / 20D / 60D real-performance validation
explainable report
human-in-the-loop review
runnable prototype / submission artifacts
```

Targets:

```text
关键风险要素抽取准确率      >= 80%
关键 Evidence Recall         >= 85%
Agent / Tool / Evidence trace = 100%
```

## 3. Five-person ownership

```text
A  Integration / CI / contracts / release / submission
B  LLM Document Intelligence / Evidence / benchmark
C  Market Intelligence / Skills / LLM interpretation
D  Outcome / frozen PR-F / evaluation
E  LLM Final Supervisor / conflict / trace / product
```

## 4. Formal Document risk scope

### Financial

```text
cash_runway
continuous_loss
revenue_growth
customer_concentration
supplier_concentration
```

### Legal / governance

```text
redemption_rights
material_litigation_compliance
related_party_transaction   # competition extension
```

### Business

```text
precommercial_product
core_product / pipeline / commercialization semantics
Disclosure Tone / Obfuscation bounded analysis
```

Every formal RiskItem requires real Evidence. Exact numeric claims use deterministic Calculation/Skill. `pending / rejected / needs_review` remain explicit.

## 5. LLM trust boundary

### LLM may

- extract bounded Legal/Business semantics from supplied Evidence;
- interpret governed Market facts;
- synthesize Agent outputs;
- detect conflict / uncertainty;
- request targeted re-check;
- generate constrained explanation.

### LLM may not

- create Evidence or page/bbox identity;
- invent market facts;
- replace deterministic financial calculations;
- modify frozen model score;
- call an uncalibrated score a probability;
- bypass Verifier / provenance controls.

### Deterministic code owns

```text
calculation
schema / identity
PIT guards
feature materialization
hash / manifest
model fitting/scoring
outcome calculation
reproducibility
```

## 6. Market specification

Frozen `Market-X Core` remains 438/438, 30 positions, PIT audited.

Competition Market layer prioritizes:

```text
HSI trend / volatility
HKEX turnover / activity
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
IPO Heat
Market Regime
optional PIT-safe comparable context
```

Industry return remains unavailable until a historically effective company-industry mapping exists.

## 7. Outcome / prediction specification

Frozen PR-C 5D remains unchanged. Competition sidecar must add:

```text
return_1d
return_20d
return_60d
```

alongside existing 5D, so final validation covers:

```text
1D / 5D / 20D / 60D
```

Optional risk outcomes:

```text
break_flag_1d
significant_drop_5d
drawdown_20d
drawdown_60d
```

## 8. Model specification

Frozen PR-F remains auxiliary. Current 2024 Full Production:

```text
M   ROC-AUC 0.4246
P   ROC-AUC 0.5000
PM  ROC-AUC 0.4246
```

No broad model search or 2024 retuning is part of the final sprint. Product consumes original frozen PR-F score + SHAP only if a valid runtime/handoff is recovered; otherwise ModelSignal is unavailable.

## 9. Multi-Agent collaboration specification

Required path:

```text
Agent claim
→ Conflict Detector
→ targeted Evidence re-check
→ Skill / Agent rerun
→ Verifier challenge
→ Final Supervisor arbitration
→ resolved / partially_resolved / unresolved
```

Trace must retain Agent / Tool / Evidence / Calculation / model/provider / conflict / re-check / final status identity.

## 10. Product UX specification

Competition UI prioritizes high-value workspaces:

```text
Risk Command Center
Evidence + AI Analysis
Market & Model
Agent Trace
Human Review / Final Report
```

Evidence Viewer must support page/bbox-based source navigation where available. Human Review must keep machine result separate from reviewer decision/note.

## 11. Submission definition of done

```text
real LLM Legal / Business semantics active
Market Agent grounded in PIT facts
LLM Final Supervisor active
controlled conflict/re-check path works
1D / 5D / 20D / 60D outcomes generated
Risk / Evidence benchmark artifact exists
Agent / Tool / Evidence trace complete
>=3 stable real IPO demos
Evidence Viewer / Human Review usable
prediction table / reasoning logs / reports generated
full CI + real-case smoke pass
submission package reproducible
```

## 12. Governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 is not recycled into a tuning set. 2025 y remains closed. Missing stays explicit. Competition work does not silently rewrite frozen PR-A–PR-G artifacts.
