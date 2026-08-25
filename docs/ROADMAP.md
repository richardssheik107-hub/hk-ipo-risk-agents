# Roadmap

> Status snapshot: **2026-08-25**  
> Time budget: **5 days to competition submission**  
> Execution strategy: **return to the competition task → maximize real LLM value → finish governed E2E → stabilize demo → submit**

## 1. Current state

```text
v0.3 Document Intelligence          COMPLETE / FROZEN
PR-A–PR-G                           COMPLETE / FROZEN
PR-H Full E2E                       PARTIAL / BLOCKED
v0.4.3 Baseline E2E Freeze          NOT CREATED
Competition submission sprint       ACTIVE — 5 DAYS
Target                               v0.4.5 COMPETITION_READY
```

Frozen measured facts remain unchanged:

```text
Official 2020–2024 universe          438
Production Document-X                438 / 438, 100 dims
Market-X Core                        438 / 438, 30 positions
5D outcome                           424 / 438
Canonical model-ready                424 = 354 Dev + 70 Val
2025 Blind y accessed                NO
```

PR-F remains an honest auxiliary modeling baseline; weak 5D performance is not a reason to spend the remaining sprint on model exploration or Validation retuning.

## 2. Competition-first objective

The remaining work is no longer a broad research program. The product must directly satisfy the competition task:

```text
real prospectus PDF
→ grounded Evidence retrieval
→ Financial / Legal / Business Agents
→ LLM semantic extraction where semantics matter
→ deterministic Calculation where exact math matters
→ Verifier
→ governed Market context + LLM interpretation
→ model/rule auxiliary signal
→ LLM Final Supervisor
→ conflict / re-check / uncertainty
→ auditable final report + Streamlit demo
```

The LLM must create observable functional improvement, not merely appear as an API dependency.

## 3. Five-day execution sequence

```text
DAY 1  Real LLM Document Intelligence
DAY 2  LLM Market interpretation + LLM Final Supervisor + simple conflict re-check
DAY 3  3–5 real-case E2E + targeted fixes + small Offline-vs-AI check
DAY 4  Evidence / AI Analysis / Agent Trace product integration
DAY 5  Regression + submission package + freeze + rehearsal
```

This sequence supersedes the previous 3-week CH-0..CH-6 execution schedule for the current submission window. CH items remain backlog concepts only where they directly support the five-day deliverable.

## 4. What we deliberately stop doing

Until submission, do **not** spend primary capacity on:

```text
full 1D/5D/20D/60D research matrix
new P-Core / broad feature audit
new model family / hyperparameter exploration
large-scale Retriever redesign
new industry mapping research
large new market data families
full-corpus benchmark construction
story-only / presentation-only features without product value
```

Allowed work must fix a real competition requirement, an E2E blocker, a high-impact extraction error, or a visible product usability problem.

## 5. LLM-first acceptance

By submission, the real AI path must demonstrate:

```text
Legal Agent       LLM structured semantic extraction from supplied Evidence
Business Agent    LLM semantic cross-check / gap filling from supplied Evidence
Market Agent      LLM interpretation of governed pre-listing market facts
Final Supervisor  LLM synthesis / conflict detection / uncertainty / re-check request
```

Rules:

- LLM only reasons over supplied governed facts/Evidence;
- structured output must validate against schema;
- out-of-scope Evidence IDs fail closed;
- exact financial calculations stay deterministic;
- model score is auxiliary and uncalibrated unless explicitly calibrated;
- every visible AI conclusion must trace to Evidence / market facts / model drivers.

## 6. Minimum effect check

Do one small, submission-oriented comparison on the same 3–5 real cases:

```text
Offline deterministic mode
vs
AI-enhanced mode
```

Record only useful operational indicators:

```text
semantic fields resolved
formal risks resolved
needs_review / extraction_failed count
Evidence grounding validity
LLM structured-output validity
conflict/re-check usefulness
```

This is not a new research benchmark; it is a sanity check that LLM integration materially improves the product.

## 7. PR-H / model runtime rule

Restoring the frozen PR-F per-case handoff remains D's highest-priority model task, but it is time-boxed. Do not retrain/reconstruct/tune merely to unblock UI.

If the original frozen handoff cannot be recovered within the sprint, the formal PR-H all-channel Gate remains blocked and the product must show `Model Channel = unavailable` honestly. Document / Market / Rule / LLM Supervisor must continue to work. No fake model output is allowed.

## 8. Final submission gate

A competition release is accepted only if:

```text
>= 3 stable real IPO demos
real LLM calls visible in governed runtime
Evidence references resolve
Legal/Business semantic extraction works on selected cases
Market interpretation is PIT-safe
Final Supervisor can synthesize and expose uncertainty/conflict
Agent/LLM trace is visible
no fabricated Evidence / market / model facts
no 2025 Blind y access
full CI + real-case smoke pass
clone/install/run instructions are complete
```

Target tag after PASS:

```text
v0.4.5 COMPETITION_READY
```

Detailed ownership: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).  
Detailed five-day acceptance: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).
