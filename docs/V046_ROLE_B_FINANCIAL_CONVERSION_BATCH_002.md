# v0.4.6 Role-B Financial Conversion Batch 002

## Identity and scope

```text
BASE_SHA                         fff23aa1db5523683db1d75179033685c9721854
branch                           fix/v046-role-b-financial-conversion-batch-002
official baseline run            forensic_012
official baseline M1             9/30 = 30.00%
official baseline M2             12/48 = 25.00%
Validation opened                false
2025 Blind accessed              false
Existing Gold modified           false
evaluator modified               false
fixed-10 modified                false
```

This batch is a Development-only Financial conversion investigation. It does
not alter the Retriever candidate generator, Existing Gold, fixed-10 cohort,
evaluator, Prompt, Legal/Business Agent, or public schema.

## Pre-change conversion audit

The post-run join over `forensic_012` contains 22 Financial positive Risk
Units across the three in-scope families:

| Risk | Units | Exact anchor hit | Agent consumed | Risk created | M1 correct |
|---|---:|---:|---:|---:|---:|
| cash runway | 5 | 4 | 4 | 0 | 0 |
| customer concentration | 8 | 7 | 6 | 3 | 3 |
| supplier concentration | 9 | 7 | 6 | 3 | 2 |

The earliest compact classifications are two consumption misses, ten
extraction-stage failures, four parser exact-text misses, and one evaluator
attribute mismatch. Counts are post-run diagnostic joins and are not added as
independent causal totals.

## Generic implementation changes

- Cash and operating-cash-flow extraction now inspect the bounded 20-item
  Financial pool, while still selecting each metric by its own label/context.
- The shared `cash_runway` query intent is accepted as a neutral pool identity;
  it no longer masquerades as a metric mismatch.
- Cash/OCF selection searches for the latest common period with matching
  document, currency, unit, and valid OCF interval. Missing fields are not
  inferred and genuine same-period conflicts remain fail-closed.
- A single Evidence object may support both cash and OCF when that same
  prospectus table contains both amounts. Calculation Evidence IDs and the
  embedded Evidence list are deduplicated, and the verifier independently
  checks both values against the retained Evidence.
- Customer/supplier Agents consume the already-retrieved bounded Top-20 pool.
  No new candidates, embedding path, or issuer-specific rule was introduced.
- Financial diagnostics now retain a compact conversion trace with extraction,
  selected fact, builder, calculation, and risk-creation state. They do not
  persist raw Gold text or long prospectus text.

## Deterministic replay

The before and after replays used the same ten Development PDFs and no external
LLM calls.

| Risk | Before facts | After facts | Before risks | After risks |
|---|---:|---:|---:|---:|
| cash runway | 0 | 3 | 0 | 3 |
| customer concentration | 6 | 6 | 3 | 3 |
| supplier concentration | 6 | 6 | 3 | 3 |

The offline evaluator changed from `M1=5/30 (16.67%)`, `M2=7/48 (14.58%)`
to `M1=5/30 (16.67%)`, `M2=9/48 (18.75%)`. Therefore M1 did not regress and
M2 recovered two Evidence units. Cash existence recall rose from zero to
`1/5`. Two other generated predictions are non-Gold-positive; they are not
called confirmed false positives because `UNJUDGED != negative` under the
frozen protocol.

Machine-readable local artifacts are under
`reports/v046_role_b/financial_conversion/`. Runtime reports and local PDFs
remain gitignored.

## Receipt portability audit

The original full-suite blocker was proven to be
`CROSS_PLATFORM_TEXT_HASH_BUG`, not committed content drift. For all three
text bindings, the frozen expected SHA-256 equals the LF-normalized content
hash while the Windows raw/CRLF hash differs:

| Binding | Expected / LF | Raw / CRLF |
|---|---|---|
| PR-F manifest | `f62eeb513d74998ace1ed2a1deb8a450d7114c73d4ab412af060faaf63fdb97a` | `617790d43acc473559b218bbb1e9107345905255fcd156ea751da7d87da21dcf` |
| PR-E manifest | `6570dc891395402ed497ad85068ae219d925733fcc5ab23dbbb8bfb8fab5170d` | `64d0ce697e0c745979eaf4df8117246a729e2a863c0eb59c86cc4a58e2526f9d` |
| Metric protocol | `c54baac00edea7917ea2231d62ce3af503d039c0eab99704d261bb86fa0514f5` | `1cb3a330f9ae18a1fcb28a9d64ae006babc69a06ac80cd6322010ce0db42cacb` |

The validator now canonicalizes newlines only for these committed UTF-8 text
bindings. Frozen expected values and all PR-E/PR-F/protocol/receipt files are
unchanged. LF/CRLF equivalence, content-mutation rejection, and the committed
receipt are covered by tests.

## Validation

```text
receipt targeted                 5 passed
Financial targeted               472 passed
compileall                       PASS
validate_project                 PASS
validate_competition_data        PASS
validate_competition_runtime     PASS
git diff --check                 PASS (line-ending warnings only)
full pytest                      2157 passed, 2 warnings
structured smoke                 3/3 PASS
```

The structured smoke used `openai_responses` / `ark-code-latest`, produced
three valid structured results, and did not open Validation or 2025 Blind.

## Formal forensic_013

The one authorized real-LLM run completed all ten cases in offline, shadow,
and gated modes with 40 journaled calls. It recorded 38/40 structured-valid
calls (95%), zero transport failures, zero scope rejections, and monotonicity
PASS.

| Metric | forensic_012 | forensic_013 | Delta |
|---|---:|---:|---:|
| gated M1 | 9/30 (30.00%) | 7/30 (23.33%) | -2 units |
| gated M2 | 12/48 (25.00%) | 12/48 (25.00%) | 0 units |
| Candidate Anchor@20 | 35/48 | 35/48 | 0 |
| Agent consumed | 30/48 | 34/48 | +4 |
| Candidate Risk created | 14/48 | 18/48 | +4 |
| consumed to Risk | 14/30 (46.67%) | 18/34 (52.94%) | +6.27pp |

Per family, M1 changed as follows: cash `0/5 -> 0/5`, customer `3/8 ->
3/8`, supplier `2/9 -> 2/9`, and redemption rights `4/8 -> 2/8`. M2 changed
as follows: cash `0/11 -> 2/11`, customer `3/13 -> 3/13`, supplier `4/13 ->
4/13`, and redemption rights `5/11 -> 3/11`. The two recovered cash Evidence
units in `ipo_2023_06682` were offset by two lost redemption-rights Evidence
units in `ipo_2020_09600` and `ipo_2023_06682`.

For the five cash-positive units, the remaining earliest failures are:

- `ipo_2020_00368`: wrong-period selection; no risk created.
- `ipo_2020_01961`: parser exact text missing; no risk created.
- `ipo_2021_02190`: numeric extraction miss; no risk created.
- `ipo_2023_01274`: conflicting same-period values; no risk created.
- `ipo_2023_06682`: risk verified at the correct status/level with matching
  Evidence, but calculation value mismatched (`9.27` versus the frozen
  expected calculation), so M1 remained incorrect.

The formal result fails the acceptance rule: M1 regressed and M2 did not
strictly improve. No post-run fix or additional forensic run was attempted.

## Current verdict

```text
BATCH002_REJECTED_REGRESSION
first remaining root = risk absent after consumed Evidence (16 M2 units)
forensic_013 = COMPLETE
Validation = false
2025 Blind = false
```

The next action is human Batch 003 direction selection. Batch 002 must not be
tuned after viewing this result, and `forensic_014` was not started.
