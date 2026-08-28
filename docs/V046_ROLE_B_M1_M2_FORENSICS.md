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

### Cash-runway trace correction

The preceding `21/48` figure is retained as the original `forensic_011`
artifact value, but it is **not a valid full fixed-10 Candidate Recall@20**.
The tracing wrapper recorded risk-pool calls with intent `cash_runway`, while
the post-run join accepted only the legacy free-text intents
`cash_flow_ending_cash` and `operating_cash_flow`. It therefore discarded all
cash-runway candidates before scoring and produced the artificial `0/11`.

A deterministic, no-LLM replay repaired that trace contract and ran the same
`RoleBFinancialHighRecallRetriever` and PyMuPDF parser used at the forensic
base (both files remain byte-identical to `65fb2ea4...`). Gold text/page was
joined only after retrieval. Across the 11 cash-runway Evidence units in five
fixed-10 Development cases, page Recall@20 is `11/11 = 100%` and exact-anchor
Recall@20 is `9/11 = 81.82%`. The two anchor misses are both in
`ipo_2020_01961`; their expected pages still rank 3 and 4. No prospectus or
Gold text, local path, Validation data, Blind data, or LLM output was persisted.

Combining the unaffected non-cash trace with this isolated replay gives a
corrected diagnostic view of `38/48 = 79.17%` expected-page Recall@20 and
`30/48 = 62.50%` exact-anchor Recall@20. This combined number is diagnostic,
not a replacement for official M1/M2. The official `M1=8/30` and `M2=11/48`
remain unchanged.

Offline and shadow are canonically equal and both score `M1=5/30`, `M2=7/48`.
Gated scores `M1=8/30`, `M2=11/48`; it reuses the same journal and performs no
extra network call. Structured-plus-scope validity is `33/35 = 94.29%`.
One independent smoke coverage gap remains: the frozen three-call smoke gate
does not separately exercise `business_precommercial_core_product_extract`.
The gate contract was not changed.

## Earliest proven root causes

The original report's claim that all 30 Risk Units and all 48 Evidence Units
had a supported earliest classification is withdrawn. Cash-runway trace rows
were filtered by the intent mismatch above, so their original earliest-stage
labels are not valid even though the final evaluator outcomes remain valid.

For the 22 incorrect M1 units, the corrected status is:

| Root cause | M1 units |
|---|---:|
| retrieval candidate miss (non-cash trace-valid units only) | 2 |
| parser text missing under exact-anchor audit | 5 |
| deterministic extraction miss | 4 |
| wrong period selection | 2 |
| retrieval ranking/top-K miss | 1 |
| builder not-applicable misclassification | 1 |
| LLM abstention with sufficient consumed Gold support | 1 |
| level mismatch | 1 |
| final Evidence not retained | 1 |
| cash-runway downstream stage not classified by this retrieval-only replay | 4 |

Of the original 16 M2 candidate-generation classifications, nine cash-runway
rows were trace-invalid. The supported non-cash candidate-generation count is
therefore seven M2 Evidence units. Parser exact-text preservation still
accounts for ten M2 units. Downstream cash-runway stage attribution requires a
full corrected pipeline trace and is intentionally not inferred from retrieval
replay alone. Together with those nine unclassified cash-runway rows, the
corrected M2 accounting still covers all 37 uncovered units without pretending
that the replay observed downstream Agent stages.

Therefore the existing evaluator label `semantic_extraction_miss` is not a
proven semantic diagnosis, but neither is the earlier claim that candidate
generation is the dominant proven failure. The corrected evidence shows that
cash-runway retrieval itself is strong; the largest currently supported M1
group is parser exact-text absence (`5` units), ahead of trace-valid non-cash
candidate generation (`2` units). These cross-metric counts must not be added
as independent failures because one upstream miss can affect both metrics.

## Recommended first Fixer

The previous recommendation to change
`src/ipo_risk/retrieval/role_b_financial_v046.py` first is withdrawn. The audit
does not justify a cash-runway candidate-recall change: all 11 expected pages
are already present in Top-20. The next investigation should preserve the
retriever and separate (a) parser exact-anchor absence, (b) cash-runway
deterministic extraction, and (c) downstream candidate/risk retention. No
Fixer should be selected until that corrected stage trace is reviewed.

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

## Batch 002 follow-up status

Financial Conversion Batch 002 is recorded separately in
`docs/V046_ROLE_B_FINANCIAL_CONVERSION_BATCH_002.md`. Its no-LLM deterministic
replay recovered two Evidence units (`M2 7/48 -> 9/48`) and generated three
cash facts/risks where the prior replay generated none, while deterministic M1
remained `5/30`. The formal `forensic_012` baseline (`M1=9/30`, `M2=12/48`)
remains authoritative.

The receipt failure was a proven Windows CRLF portability defect and was fixed
without changing any frozen expected hash or artifact. Full pytest returned to
`2157 passed` and the structured smoke passed `3/3`.

The single authorized `forensic_013` then completed. Candidate Anchor@20 stayed
`35/48`, Agent consumption rose to `34/48`, and candidate risks rose to `18/48`.
However, gated M1 regressed from `9/30` to `7/30`, while M2 stayed `12/48`.
Cash recovered two Evidence units, but redemption rights lost two M1 and two
M2 units. Batch 002 is therefore `BATCH002_REJECTED_REGRESSION`; no post-result
code adjustment or `forensic_014` is permitted.
