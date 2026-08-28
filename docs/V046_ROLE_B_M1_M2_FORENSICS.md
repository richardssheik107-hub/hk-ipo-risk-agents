# v0.4.6 Role-B M1/M2 Forensics

## Scope and identity

This is a post-run, Existing-Gold-only diagnostic. It does not change runtime
decisions, the evaluator, fixed-10 membership, Prompt/Schema identity, or any
Gold record.

```text
BASE_SHA                         65fb2ea4e3969583c20ff2f68eeff6905b97169e
forensic run                    forensic_011
authoritative runtime run       main_candidate_real
artifact git revision           8ae09505b3b31ad88e6d5dc2b1f3faea526475aa
fixed-10 hash                   5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a
Existing-Gold manifest hash     fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
provider                        openai_responses
model                           ark-code-latest
transport                       responses
Validation opened               false
2025 Blind outcome accessed     false
```

The Role-B runtime tree used by the artifact is byte-identical to the Role-B
runtime tree at `BASE_SHA`. The previously documented `iter_004` result
(`M1=7/30`, `M2=9/48`) remains valid historical evidence, but it has a different
code identity and is not mixed with this report. The latest identity-compatible
local run is therefore the authoritative baseline below.

## Official baseline

| Metric | Numerator | Denominator | Result |
|---|---:|---:|---:|
| M1 | 8 | 30 | 26.67% |
| M2 | 11 | 48 | 22.92% |

Per-family M1 is `cash_runway 0/5`, `customer_concentration 3/8`,
`redemption_rights 3/8`, and `supplier_concentration 2/9`. Per-family M2 is
`cash_runway 0/11`, `customer_concentration 3/13`, `redemption_rights 4/11`,
and `supplier_concentration 4/13`.

## Stage evidence

The cumulative M1 waterfall is:

```text
30 Gold-positive Risk Units
→ 13 final risks present
→ 10 final-positive
→ 10 status matched
→ 9 level matched
→ 9 calculation matched
→ 8 Evidence matched
→ 8 M1 correct
```

The cumulative M2 waterfall is:

```text
48 Gold Evidence Units
→ 38 expected-page anchors preserved by the frozen PyMuPDF parser
→ 21 exact anchors in candidate Top-20
→ 20 exact anchors consumed by the Agent
→ 13 corresponding candidate risks created
→ 12 final-positive risks retained
→ 12 Evidence bindings retained
→ 11 pages matched
→ 11 text anchors matched
→ 11 M2 covered
```

Parser expected-page and any-page preservation are both `38/48 = 79.17%`.
There is no supported systematic page offset: all 38 located anchors occur at
offset zero. Five anchors have multiple parser matches.

Candidate Recall@20 is `21/48 = 43.75%`. By family it is `0/11` for cash
runway, `7/13` for customer concentration, `7/11` for redemption rights, and
`7/13` for supplier concentration. The financial high-recall adapter does not
apply to redemption rights; the latter still uses the ordinary keyword path.

Offline and shadow are canonically equal and both score `M1=5/30`, `M2=7/48`.
Gated scores `M1=8/30`, `M2=11/48`; it reuses the same journal and performs no
extra network call. Structured-plus-scope validity is `33/35 = 94.29%`.
One independent smoke coverage gap remains: the frozen three-call smoke gate
does not separately exercise `business_precommercial_core_product_extract`.
The gate contract was not changed.

## Earliest proven root causes

All 30 Risk Units and all 48 Evidence Units have a directly supported earliest
classification (`PROVEN=100%`, `INFERRED=0`, `UNAVAILABLE=0`). This does not
mean every internal semantic field is observable: raw LLM semantics and
per-candidate reconciliation events are intentionally not persisted. It means
the first stage needed to explain each official pass/fail is observable before
those gaps.

For the 22 incorrect M1 units, the primary roots are:

| Root cause | M1 units |
|---|---:|
| retrieval candidate miss | 6 |
| parser text missing under exact-anchor audit | 5 |
| deterministic extraction miss | 4 |
| wrong period selection | 2 |
| retrieval ranking/top-K miss | 1 |
| builder not-applicable misclassification | 1 |
| LLM abstention with sufficient consumed Gold support | 1 |
| level mismatch | 1 |
| final Evidence not retained | 1 |

For the 37 uncovered M2 units, `16` fail first at candidate generation, `10`
at parser exact-text preservation, `7` after the corresponding risk remains
absent, and one each at ranking/top-K, snippet truncation, rejected-risk
binding, and final page matching.

Therefore the existing evaluator label `semantic_extraction_miss` is not a
proven semantic diagnosis. The most common directly proven first failure is
candidate generation: it affects six M1 Risk Units and sixteen M2 Evidence
Units. These counts must not be added as independent failures because one
upstream miss can affect both metrics.

## Recommended first Fixer

Only one next module is recommended:
`src/ipo_risk/retrieval/role_b_financial_v046.py`. The smallest acceptable
change is a bounded, issuer-agnostic financial candidate-recall fix followed by
the same fixed-10 regression. It has a mechanical ceiling of five M1 Risk Units
and fourteen M2 Evidence Units within the dominant root-cause group; those
cross-metric counts are not additive. The two redemption-rights Evidence misses
and one redemption-rights M1 miss are deferred rather than combining Legal and
Financial retrieval changes. The Fixer must not use Gold text/page at runtime
and must preserve candidate-noise, canonical-output, and Validation/Blind
guards. Parser, extraction, Prompt, reconciliation, and Verifier changes are
also deferred until this single Fixer is reviewed.

## Known limits

- No new real-LLM run was required; the existing identity-compatible journal
  and run artifacts provide the required coverage.
- Raw LLM response bodies and full Prompt text were not read or persisted.
- No per-candidate durable reconciliation event exists; it was not needed to
  establish the earlier root for any current official failure.
- This report does not claim M1/M2 improvement, target attainment, or
  `COMPETITION_READY`.

Detailed matrices remain local and gitignored under
`reports/v046_role_b/forensics/forensic_011/`.
