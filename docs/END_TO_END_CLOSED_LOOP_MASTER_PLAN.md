# HK IPO Risk Agents — End-to-End Competition Delivery Plan

> Status snapshot: **2026-08-25**  
> Time budget: **5 days**  
> Strategy: **working competition product first; exploratory research deferred**

## 1. Final product path

The final submission must make this path real and observable:

```text
Prospectus PDF
→ Parser / Retriever
→ Financial Agent
→ Legal Agent + LLM semantic extraction
→ Business Agent + LLM semantic cross-check
→ Evidence / deterministic Calculation
→ Verifier
→ governed Market context + LLM interpretation
→ frozen Model signal if available + Rule signal
→ LLM Final Supervisor
→ conflict / re-check / uncertainty
→ Final Report / Streamlit / Agent Trace
```

LLM is used where semantic reasoning matters. Deterministic code remains authoritative for exact calculations, identity, PIT, hashes, model scoring and reproducibility.

## 2. Frozen foundation

```text
PR-A–PR-G                           COMPLETE / FROZEN
PR-H                               PARTIAL / BLOCKED
Production Document-X              438 / 438
Market-X Core                      438 / 438
5D Outcome                         424 / 438
Canonical                          424 = 354 Dev + 70 Val
2025 Blind y accessed              false
```

The frozen PR-F model result is kept as an auxiliary research baseline. The sprint does not spend time trying to improve its 5D AUC.

## 3. Five-day priority order

```text
1. make real LLM Legal/Business extraction work
2. make governed Market facts produce LLM Market interpretation
3. make LLM Final Supervisor synthesize, detect conflict and request one re-check
4. stabilize 3–5 real IPO cases
5. expose Evidence + AI contribution + Agent Trace in the product
6. regression / freeze / submission
```

Anything outside this order is backlog unless it blocks the final product.

## 4. Deferred research

Until submission, defer:

```text
multi-horizon modeling
new feature families
new model families / tuning
full feature audit
large Retriever research
industry PIT research
full benchmark program
large-scale new market acquisition
```

A targeted fix is allowed when a selected real case proves it is necessary.

## 5. LLM governance

### LLM may

- interpret retrieved legal/business evidence;
- fill bounded semantic fields;
- interpret governed market facts;
- synthesize cross-agent findings;
- detect conflict/uncertainty and request re-check.

### LLM may not

- invent Evidence or market facts;
- cite IDs outside supplied inputs;
- replace exact financial calculations;
- alter frozen model output;
- convert an uncalibrated score into probability;
- bypass Verifier.

Structured outputs must validate against schemas. Provider failure must degrade honestly.

## 6. Real collaboration target

The competition version upgrades parallel Agent output into one controlled collaboration loop:

```text
Agent claims
→ LLM Final Supervisor detects conflict / uncertainty
→ one targeted retrieval or existing Skill
→ Verifier
→ Supervisor second pass
→ resolved or unresolved
```

One controlled re-check is enough for this sprint. Do not build an open-ended autonomous loop.

## 7. Effect validation

Use 3–5 selected real cases and compare:

```text
Offline deterministic
vs
AI enhanced
```

Record only whether LLM improves practical completion:

```text
semantic fields resolved
risk decisions resolved
needs_review / extraction_failed
Evidence grounding validity
structured-output validity
conflict/re-check usefulness
```

This check exists to prove functional value, not to create a new research paper.

## 8. Model and PR-H handling

D first attempts to restore the original frozen PR-F per-case handoff. This task is time-boxed.

If unavailable:

```text
formal PR-H remains BLOCKED
Model channel = unavailable
Document + Market + Rule + LLM Supervisor continue
```

Do not retrain or reconstruct PR-F simply to make the UI look complete.

## 9. Submission definition of done

```text
>=3 real IPO cases stable
real LLM provider path works
Legal/Business LLM semantics are visible and grounded
Market LLM interpretation is PIT-safe
LLM Final Supervisor works
at least one conflict/re-check path works
Evidence / Calculation / Verifier boundaries hold
Agent/LLM trace visible
model availability is honest
no 2025 Blind y access
CI + real-case smoke pass
reproducible runbook complete
```

Detailed five-person daily execution: [`V04_FIVE_PERSON_EXECUTION_PLAN.md`](V04_FIVE_PERSON_EXECUTION_PLAN.md).  
Detailed acceptance: [`COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`](COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md).
