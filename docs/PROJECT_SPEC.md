# HK IPO Risk Agents — Current Project Specification

> Status snapshot: **2026-08-25**  
> Baseline: **PR-A–PR-G COMPLETE / FROZEN**  
> Current delivery mode: **5-day competition submission sprint**  
> Target: **v0.4.5 COMPETITION_READY**

## 1. Product definition

HK IPO Risk Agents 是一个 Evidence-driven、多智能体协同、可审计的港股 IPO 招股书风险分析与上市后风险预警系统。

最终比赛版核心链路：

```text
Prospectus PDF
→ Parser / Retriever
→ Financial / Legal / Business Agents
→ LLM semantic reasoning where needed
→ Evidence / Calculation
→ Verifier
→ governed Market facts + LLM Market interpretation
→ model/rule auxiliary signal
→ LLM Final Supervisor
→ conflict / re-check / uncertainty
→ Final Report / Streamlit / Agent Trace
```

## 2. Competition requirement first

The remaining sprint prioritizes working competition capabilities over exploratory research. The product must visibly demonstrate:

```text
long-document understanding
Evidence-grounded risk extraction
Financial / Legal / Business multi-agent specialization
real LLM semantic reasoning
point-in-time market interpretation
cross-agent synthesis / conflict handling
traceable final warning and report
```

Work that does not materially improve one of these capabilities is deferred until after submission.

## 3. Formal risk scope

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

Every formal RiskItem requires real Evidence. Exact numeric claims require deterministic Calculation. `pending / rejected / needs_review` remain explicit.

## 4. LLM responsibility

### Legal Agent

LLM is expected to resolve bounded legal semantics such as:

```text
right exists / effective / survives listing
termination / restoration conditions
actual litigation matter vs template disclosure
current / resolved / historical status
```

### Business Agent

LLM is expected to resolve bounded business semantics such as:

```text
core product identity
development stage
commercialization / launch status
product revenue vs generic revenue
```

### Financial Agent

Financial exact math remains deterministic. LLM may assist only with already-grounded textual ambiguity.

### Market Agent

LLM interprets only governed pre-listing market facts into a structured market environment. It does not manufacture data.

### Final Supervisor

LLM synthesizes existing channel outputs, detects conflict/uncertainty, requests at most one controlled re-check, and produces the final explanation. It never creates new Evidence.

## 5. Trust boundaries

### LLM may

- perform semantic extraction and contextual interpretation;
- fill bounded structured fields;
- summarize supported cross-agent findings;
- detect conflicts and uncertainty;
- request targeted re-check.

### LLM may not

- invent Evidence / market facts / model outputs;
- cite Evidence IDs outside supplied inputs;
- replace deterministic calculations;
- alter frozen model score;
- call an uncalibrated score a probability;
- bypass Verifier.

### Deterministic code owns

```text
financial calculations
schema / identity validation
PIT guards
feature vectorization
hash / manifest
model fitting / scoring
reproducibility
```

## 6. Frozen data/model baseline

```text
438 official cases
438 / 438 Production Document-X
438 / 438 Market-X Core
424 / 438 valid 5D outcomes
424 canonical = 354 Dev + 70 Val
2025 Blind y accessed = NO
```

Frozen PR-F remains an auxiliary warning baseline. The five-day sprint does not spend primary capacity on new model search, multi-horizon research or 2024 retuning.

## 7. Market specification

Use only already governed sources during the sprint:

```text
Market-X Core
HSI return / volatility
HKEX turnover
prior IPO context
```

Industry return remains unavailable while historical company classification mapping is PIT-blocked. Missing remains explicit.

## 8. PR-H / model channel

PR-H remains `PARTIAL / BLOCKED` until the original frozen PR-F per-case handoff and required all-channel real-case matrix are available.

D time-boxes recovery. If it cannot be recovered:

```text
Model channel = unavailable
formal PR-H remains blocked
Document + Market + Rule + LLM Supervisor still operate
```

No retraining or fabricated score is allowed merely to make the product look complete.

## 9. Competition UI requirement

Final UI prioritizes three primary workspaces:

### Risk Command Center

Overall assessment, top domain risks, market environment, model/rule state and uncertainty.

### Evidence + AI Analysis

For each key risk show:

```text
PDF page / bbox
Evidence
Agent
LLM task and structured semantic result
Calculation where applicable
Verifier
AI contribution
```

### Agent Trace + Final Supervisor

Show the actual flow from retrieval through domain Agents, Market interpretation, verification, conflict/re-check and final synthesis. Display provider/model/prompt/latency/token metadata where safe and available.

## 10. Minimal LLM effect check

For the same 3–5 real cases compare Offline vs AI-enhanced mode and record:

```text
semantic fields resolved
risk decisions resolved
needs_review / extraction_failed
Evidence grounding validity
structured-output validity
useful conflict/re-check count
```

This is a product acceptance check, not a full benchmark program.

## 11. Time / Blind governance

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

2024 is not recycled into a tuning set. 2025 y remains closed. Weak AUC is not permission to reverse score direction or tune on Validation.

## 12. Submission definition of done

```text
>=3 stable real IPO demos
real LLM provider path active
Legal/Business semantic reasoning visibly useful
Market interpretation grounded in PIT facts
LLM Final Supervisor active
at least one controlled conflict/re-check example
Evidence / Calculation / Verifier authoritative
Agent/LLM trace visible
model state honest
no fake market facts
no 2025 Blind y access
full CI + real-case smoke pass
reproducible runbook and submission package
```

Detailed execution: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).  
Detailed sprint acceptance: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).
