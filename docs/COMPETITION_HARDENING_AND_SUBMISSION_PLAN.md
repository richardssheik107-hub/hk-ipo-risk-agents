# 港股 IPO 风险预警赛题强化与提交总计划（5-Day Competition Sprint）

> Status snapshot: **2026-08-25**  
> Remaining window: **5 days**  
> Current baseline: **PR-A–PR-G COMPLETE / FROZEN; PR-H PARTIAL / BLOCKED**  
> Target: **finish a strong, real, LLM-visible competition version and submit**

## 1. Strategy reset

The remaining sprint returns fully to the competition task itself. We intentionally reduce exploratory experiments, long research loops and narrative-only work.

The competition product must directly demonstrate:

```text
long prospectus parsing
→ grounded Evidence
→ multi-agent Financial / Legal / Business analysis
→ real LLM semantic understanding
→ deterministic financial calculation
→ verification
→ point-in-time market context
→ LLM market interpretation
→ model/rule auxiliary warning
→ LLM Final Supervisor
→ conflict / re-check / uncertainty
→ auditable final report / Streamlit
```

The goal is not to prove a new research thesis in five days. The goal is to make the system itself materially better and visibly AI-enabled.

## 2. Frozen baseline that we keep

We do not reopen completed PR-A–PR-G contracts or fabricate improved model results.

```text
438 official 2020–2024 cases
438 / 438 Production Document-X
438 / 438 Market-X Core
424 / 438 valid 5D outcome
424 canonical = 354 Dev + 70 Val
2025 Blind y accessed = NO
```

Frozen PR-F 5D modeling remains an auxiliary baseline. No remaining sprint capacity is allocated to broad model search, multi-horizon research or Validation retuning.

## 3. LLM role in the final product

### 3.1 Legal Agent — mandatory LLM value

LLM resolves complex clause semantics from retrieved Evidence, including:

```text
redemption / repurchase rights
current effectiveness
post-listing survival
termination conditions
restoration conditions
actual litigation/compliance matter vs generic disclosure
current / resolved / historical status
```

Output is structured and schema-validated. The LLM cannot cite Evidence outside the supplied set.

### 3.2 Business Agent — mandatory LLM value

LLM cross-checks or fills semantics that deterministic parsing cannot reliably resolve:

```text
core product identity
development stage
launch / commercialization status
product revenue vs generic revenue
pre-commercial condition
```

A conflict between deterministic facts and LLM facts becomes `NEEDS_REVIEW / CONFLICTING_VALUES`, not silent override.

### 3.3 Financial Agent — deterministic-first

Financial calculations remain Python-owned. LLM may only assist with semantic ambiguity when a concrete Evidence set already exists.

```text
LLM = understand text
Python = exact math / thresholds / calculation trace
```

### 3.4 Market Agent — LLM interpretation, not data invention

The Market Agent consumes only governed pre-listing facts:

```text
Market-X Core
HSI return / volatility
HKEX turnover
prior IPO context
available IPO activity facts
```

LLM converts them into structured interpretation:

```text
market_regime
risk_level
key_drivers
uncertainty
```

It must not create missing market values.

### 3.5 Final Supervisor — mandatory LLM synthesis

The final LLM Supervisor consumes only existing governed facts and produces:

```text
overall_assessment
key_findings
conflicts
uncertainty
recheck_requests
final_explanation
```

If a conflict is detected, the five-day version permits one controlled re-check:

```text
conflict
→ targeted retrieval / existing Skill
→ Verifier
→ Supervisor second pass
```

No infinite autonomous loop is required.

## 4. Five-day schedule

### Day 1 — Real LLM Document path

PASS requires at least one real prospectus to complete:

```text
PDF → Evidence → Legal/Business real LLM call → structured result → Risk builder → Verifier
```

Also establish auditable LLM metadata: provider/model/prompt version/latency/token usage/request identity or response hash where available.

### Day 2 — Market interpretation + Final Supervisor

PASS requires one real case to complete:

```text
Financial + Legal + Business
+ governed Market facts
+ Model/Rule state
→ LLM Final Supervisor
```

At least one conflict or uncertainty must be representable and one-step re-check must work.

### Day 3 — 3–5 real cases and targeted fixes

Select 3–5 stable cases. Fix only failures that block the selected competition capabilities.

Recommended case patterns:

```text
A  deterministic Financial / Calculation case
B  Legal or Business case where LLM resolves complex semantics
C  cross-agent or Document-vs-Market conflict case
```

Run a small same-case Offline-vs-AI check. Do not start a full benchmark project.

### Day 4 — Competition UI and trace

Final UI prioritizes only three primary workspaces:

```text
Risk Command Center
Evidence + AI Analysis
Agent Trace + Final Supervisor
```

Market/Model information is embedded into the Command Center / trace rather than creating many new pages.

### Day 5 — Freeze and submit

No new features. Only:

```text
bug fixes
regression
real-case smoke
README / runbook
screenshots / reports
release identity
submission package
demo rehearsal
```

## 5. Minimal effect validation

The submission must be able to answer: **what did the LLM actually improve?**

Use the same 3–5 cases in two modes:

```text
Offline deterministic
AI enhanced
```

Track only practical indicators:

```text
semantic fields resolved
formal risks resolved
needs_review count
extraction_failed count
Evidence grounding validity
structured response validity
useful conflict/re-check count
```

This is a product acceptance check, not a publication-grade experiment.

## 6. Competition product acceptance

### Document / Evidence

- real PDF processing;
- every formal risk is Evidence-grounded;
- exact numeric claims have Calculation;
- selected Legal/Business cases demonstrate real LLM semantic value;
- out-of-scope LLM citations fail closed.

### Multi-Agent

- Financial / Legal / Business / Market outputs are separately observable;
- Final Supervisor receives all available channels;
- conflict / uncertainty is explicit;
- one-step re-check is supported;
- unresolved cases remain unresolved.

### Market / Warning

- only PIT-safe pre-listing facts are consumed;
- Market LLM interpretation is traceable to those facts;
- frozen model score + SHAP is shown if the original PR-F handoff is recovered;
- otherwise Model channel is explicitly unavailable;
- Rule signal remains deterministic.

### Product

- >=3 stable real IPO demos;
- Evidence page/bbox and Agent/LLM trace visible;
- real Provider state visible without exposing secrets;
- final report is consistent with structured data;
- full CI + real-case smoke passes.

## 7. Explicit non-goals for the remaining five days

Do not prioritize:

```text
1D/20D/60D full modeling research
P-Core or broad feature-selection experiments
new XGBoost/CatBoost/Transformer model search
new calibration/tuning loops
large Retriever V3 restart
large prompt research grid
industry PIT blocker research
new broad market datasets
full 438-case LLM rerun unless required by final product
full annotation benchmark build
story-only diagrams or features not backed by working runtime
```

A small targeted change is allowed only when it fixes a selected real-case failure or competition requirement.

## 8. PR-H / v0.4.3 handling

PR-H formal all-channel blockers remain factual:

```text
frozen PR-F per-case runtime/handoff
>=3 matching real 2024 PDFs
all-channel formal case matrix
```

D time-boxes recovery of the original frozen PR-F handoff. We do not reconstruct or retrain to satisfy the UI.

If recovery fails, PR-H remains formally blocked; this does **not** stop the competition product from proceeding with explicit `Model unavailable`. No document may falsely claim v0.4.3 was frozen if the formal gate did not pass.

## 9. Five-person ownership

```text
A  integration / CI / main / release / submission
B  Legal + Business LLM Document intelligence / Evidence / Verifier
C  governed Market facts + LLM Market interpretation
D  frozen model handoff + minimal Offline-vs-AI effect check
E  LLM Final Supervisor + conflict/re-check + Evidence/AI Trace + UI
```

Detailed daily handoff is defined in [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).

## 10. Final release gate

A may mark the submission release `v0.4.5 COMPETITION_READY` only when:

```text
>=3 real cases stable
real LLM Document path works
real LLM Market interpretation works
real LLM Final Supervisor works
Evidence/Calculation/Verifier boundaries remain intact
Agent/LLM trace visible
conflict/re-check works on at least one selected case
model state is honest
no fake market data
no 2025 Blind y access
CI and real-case smoke pass
reproducible runbook is complete
```

The final submission is evaluated on the working system, not on the amount of exploratory research completed.
