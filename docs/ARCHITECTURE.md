# Architecture — v1.0.0 Frozen Runtime

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Architecture status: **FROZEN FOR COMPETITION RELEASE**

## 1. Production analysis path

```text
IPOAnalysisRequest
      ↓
Prospectus Parser
      ↓ DocumentChunk(page, text, bbox)
Retriever
      ↓ bounded Evidence
Financial ─┬─ Legal ─┬─ Business
           └─────────┘
                 ↓
              Verifier
                 ↓
        Document Supervisor
                 ↓
Governed MarketContext + Skills
                 ↓
Frozen Model inference + native SHAP
                 ↓
Conflict Detection
                 ↓
bounded Targeted Re-check
                 ↓
Final Supervisor
+ deterministic fallback
                 ↓
Trace + Evidence / Screenshot + Report / UI / API
```

Evaluation and release governance sit outside the runtime path: M1/M2/M3/M5, frozen identity, one-shot Validation, audits and package generation.

## 2. Document / Role-B boundary

Parser owns physical page identity; page/text/bbox come from the parser/Evidence layer. UI does not guess Evidence coordinates.

Financial is deterministic-first. Legal / Business consume bounded Evidence and are constrained by Pydantic response schemas plus Evidence-scope guards.

Final ALL79 Development checkpoint:

```text
real-LLM gated M1 = 61/102 = 59.80%
real-LLM gated M2 = 93/191 = 48.69%
best offline M1 = 70/102 = 68.63%
best offline M2 = 103/191 = 53.93%
real_llm_cases = 79/79
```

The real LLM path does not beat the selected offline path and the internal G2 threshold is not met. The release keeps the strict Evidence/schema contract and freezes the measured limitation instead of loosening guards for score.

## 3. Market runtime — closed / G3 PASS

### Historical governed path

```text
438 governed Market-X Core artifacts
→ GovernedPRBMarketContextProvider
→ schema / identity / hash / PIT provenance validation
→ MarketContext
```

### Dynamic PIT path

```text
case identity
→ governed frozen artifact available?
   ├─ yes → validated frozen load
   └─ no  → Dynamic PIT Market-X
             → governed pre-listing history
             → feature builder
             → schema / identity / provenance / cutoff validation
→ MarketContext
```

Final strict audit facts include 562 governed cases, 0 integrity violations, 438 frozen-path cases, 124 Dynamic PIT cases and a Model handoff of 550 bound / 12 not-projectable.

New IPOs do not have to produce every number. Insufficient governed history results in explicit `PARTIAL / UNAVAILABLE` states. Missing values are never silently zero-filled.

## 4. Model runtime — closed / G4 PASS

### Stable final-three compatibility

```text
receipt-bound final-three handoff
→ governed frozen result
```

This remains a stable compatibility/demo path.

### Generalized frozen inference

```text
governed feature vector
+ models/role_d_v2 frozen model
+ feature manifest
+ alert policy
→ runtime inference (no retraining)
→ uncalibrated_model_score
→ native pred_contrib / SHAP
→ ModelSignal
```

`PROMOTE_V2` is effective. Generalized inference is implemented and audited; it is no longer an open architecture target.

Strict audit facts:

```text
governed cases = 562
inference available = 540
available outside per-case handoff = 537
inference error = 0
degenerate SHAP = 0
published parity = 70/70
mismatch = 0
```

Frozen model SHA-256:

```text
320e810e85dcdb7e6caa40f9ef2b20157005e7a1d1af38ad7d586dd0feee72e2
```

The model is an uncalibrated triage signal, not a probability forecast.

## 5. Supervision / conflict / trace

Final Supervisor only consumes supplied in-scope Risk, Evidence, Conflict, Recheck, MarketContext and ModelSignal. It cannot mint new Evidence or market numbers.

Deterministic verified-risk severity floors remain authoritative.

Regression baseline:

```text
E1 = 3/3
M3 = 1.0 x 3
recheck = 17/17
seven-stage = 21/21
```

`unresolved + recheck executed` is a valid governed state, not a workflow crash.

## 6. Evidence architecture

```text
Evidence ID
→ source PDF identity/hash
→ physical page
→ bounded text / provenance
→ unique localisation or truthful fallback
→ screenshot
→ screenshot manifest / hash
```

Canonical final-three screenshot baseline remains 17/17 precise.

No UI path may fabricate bbox/page or replace an unavailable Evidence localisation with another item's coordinates.

## 7. Product surfaces — G5 PASS

v1.0.0 supports:

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

Standard and judge-facing Streamlit surfaces consume runtime schema/state/provenance; they do not recompute or invent Document/Market/Model values.

Issuer lookup may assist user input, while formal downstream joins remain governed by case/stock/listing identities rather than fuzzy company-name matching alone.

## 8. Frozen stable baseline

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
Evidence screenshots = 17/17 precise
seven-stage = 21/21
canonical replay = 66 files
G3/G4/G5/G6 = PASS
main tests / Role D runtime / Team demo runtime = PASS
```

## 9. Remaining work is not architecture development

After v1.0.0, only competition-submission operations remain:

```text
one-shot Validation
final artifact/hash rebinding
fresh clone
security / licensing / provenance audit
secure package
PPT / defense / recording
```

G2 remains a frozen known limitation. Any new algorithmic/generalization work belongs to a post-competition release and must not silently rewrite the v1.0.0 frozen architecture or benchmark identity.
