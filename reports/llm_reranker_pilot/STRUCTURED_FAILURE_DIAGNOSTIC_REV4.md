# Phase 0.6C Structured Failure Diagnostic — Revision 4

## Safety snapshot

- `gold_loaded=false`
- `blind_2025_accessed=false`
- Freeze revision: `4`
- Provider/model: `openai_responses / ark-code-latest`
- Sanitized cache currently present: `15/80` (`12 completed`, `3 failed`)
- Remaining calls: `65`
- No further real-LLM call was made for this diagnostic.

The cache count is larger than the earlier 8-item progress snapshot because the
already-running sequential process finished additional calls before termination.
No Expert annotation was opened.

## Failure 1

- Case/risk: `ipo_2020_00368 / customer_concentration`
- Candidate count: `20`
- Candidate-set SHA-256: `7eb31be0341a1f9a7a6037ac8cf94436839d574268a425220b6bbfc5a2f4cf88`
- Prompt: `rerank_customer_concentration / llm_evidence_reranker_v1`
- Cached failure kind: `validation`
- Fallback: `stage1_union_order`
- Attempt count: `UNKNOWN_WITH_CURRENT_LOGGING` (at least one API call)
- Infrastructure failure: `true`
- Taxonomy: `O. OTHER`, narrowed to either candidate-coverage validation
  (`H/I/J`) or frozen-facet validation (`K`).
- Root cause: the Provider returned a Pydantic-valid bundle, after which the
  deterministic `rerank()` validation raised `ValueError`. The runner collapsed
  coverage mismatch and unknown facet into the same sanitized `validation` code,
  so the exact subtype cannot be recovered.
- Batch atomic validation: `true`. The entire 20-candidate batch fell back.
- Valid versus invalid judgment count: `UNKNOWN_WITH_CURRENT_LOGGING`.

## Failure 2

- Case/risk: `ipo_2020_00368 / redemption_rights`
- Candidate count: `5`
- Candidate-set SHA-256: `cc9d19b331ab1d3d9c10fb8b75ed094ad9da0d81fa7e4189577a47391dd0ce11`
- Prompt: `rerank_redemption_rights / llm_evidence_reranker_v1`
- Cached failure kind: `response_validation`
- Fallback: `stage1_union_order`
- Attempt count: `UNKNOWN_WITH_CURRENT_LOGGING` (at least one API call)
- Infrastructure failure: `true`
- Taxonomy: one of `B/C/D/E/F/G/L/M`; current cache cannot distinguish a
  missing function call, malformed arguments, or Pydantic failure.
- Root cause: failure occurred inside the Responses adapter before a validated
  bundle reached deterministic reranking. The adapter intentionally discarded
  the raw response and did not persist a sanitized Pydantic error path.
- Batch atomic validation: `true`. The entire 5-candidate batch fell back.
- Valid versus invalid judgment count: `UNKNOWN_WITH_CURRENT_LOGGING`.

## Shared pattern

Both are infrastructure/structured-contract failures, not demonstrated semantic
instruction failures. They are not identical layers: Failure 1 occurred after
bundle validation in deterministic coverage/facet checks; Failure 2 occurred
inside the Provider adapter's structured-output validation.

## Structured-output architecture

- `STRUCTURED_OUTPUT_MODE=HYBRID`
- The Responses API receives an API-native forced function tool with a strict
  JSON Schema. Returned function arguments are then parsed and validated again
  with Pydantic.
- Raw response available: `false`.
- Failure response hash available: `false` in the current Responses adapter.

## Schema complexity

Each judgment has 11 named fields, including constrained enums and a variable
facet list. The largest failed call expected roughly `20 × 11 = 220` candidate
fields plus the bundle wrapper. The redemption call expected roughly `5 × 11 =
55`. This is a structural count, not a token estimate.

`SCHEMA_COMPLEXITY_RISK=HIGH` for full 20-candidate calls because one invalid
member invalidates the complete bundle and several fields are constrained enums.

## Batch fragility

- `BATCH_ATOMIC_VALIDATION=true`
- One missing, duplicated, unknown-ID, or unknown-facet judgment can discard the
  complete case/risk batch.
- `PARTIAL_RECOVERY_POSSIBLE=true`, but whether it is purely engineering-safe
  cannot be proven from the discarded payload.
- Adding partial recovery would not change ranking semantics if valid members
  retain their frozen judgments and only invalid/missing members fall back, but
  it would change batch failure mechanics and therefore requires a new freeze.

## Facet enum fragility

`FACET_ENUM_FRAGILITY=MEDIUM`.

Generic likely collisions include:

1. `ending_cash` versus `cash_balance`
2. `operating_cash_flow` versus `net_cash_used`
3. `termination` versus `waiver`
4. `licence_permit` versus `regulatory_approval`
5. `product_sales` versus `commercial_revenue`

These are generic terminology examples only and were not derived from Gold.

## Retry behavior

Transport retries are bounded, but structured-output/Pydantic failures are
classified non-recoverable and are not retried. The failure cache does not retain
attempt metadata, so exact counts and whether transport retries preceded an
eventual structured failure are unknown.

## Recommendation

`CONTINUE_REVISION_4`

## Diagnostic replay result

The two failures were replayed exactly once in an isolated
`diagnostic_replay/` directory after adding sanitized instrumentation. Prompt,
facets, candidates, excerpts, tier policy, model and temperature behavior were
unchanged. Neither replay was written to the official cache or counted as an
official benchmark call.

### customer_concentration

- Status: `completed`
- Attempts: `1`
- Expected/actual candidates: `20/20`
- Missing/unknown/duplicate IDs: `0/0/0`
- Unknown facets: `0`
- Pydantic errors: `0`
- Response hash: `51dff1a673b8b75f9824c12feba883c0c9ef0f689cc1fb9e7c70f1c836f8ac8a`
- Parsed payload hash: `97302b9482ed59b45d471b44c3e3154ae235684c10356e0b909935458f123f47`

### redemption_rights

- Status: `completed`
- Attempts: `1`
- Expected/actual candidates: `5/5`
- Missing/unknown/duplicate IDs: `0/0/0`
- Unknown facets: `0`
- Pydantic errors: `0`
- Response hash: `9c43b9d1074ac8b6f0e9a041fe8fa60308f7975ee505f587ab4ea7ea4b529f23`
- Parsed payload hash: `41eb11f9ef8d0aeccf5bda8d5cd9dfa635a37d339209b508b09af0f1585264ed`

The two authorized failures were not reproducible under identical semantic
inputs, and their replay found no candidate-completeness, facet, adapter parsing
or deterministic post-validation defect. On that evidence alone they are
consistent with intermittent structured-output failures.

The third official failure, `ipo_2020_01167 /
material_litigation_compliance`, was subsequently replayed once under the same
isolation rules. It also completed in one attempt with `20/20` candidate
coverage, zero missing/unknown/duplicate IDs, zero unknown facets and zero
Pydantic errors. Its response and parsed-payload hashes are respectively:

- `a3eb12268d5128e48058a760e7046e06ccc95ba88bb0f88414efb9bdd10020f3`
- `c52fe9fd968b363c66e6af5596c0b3e2d72728f09c436445d91a6d818f985114`

All three failures were therefore non-reproducible and no deterministic adapter,
coverage, facet or post-validation defect was observed. The three official
fallbacks remain untouched as real Revision-4 reliability costs.

A previously terminated judge child process was found still running and
continued to append official cache files during diagnosis. It was explicitly
stopped and all post-baseline additions were removed one path at a time, restoring
the 15-item baseline. No Gold had been loaded. Revision 4 may continue from that
restored baseline without changing prompt, schema, candidates or ranking.
