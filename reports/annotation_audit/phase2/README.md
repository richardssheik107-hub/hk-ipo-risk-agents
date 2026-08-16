# Expert Annotation Phase 2

Phase 2 applies only deterministic corrections that are already implied by the
frozen annotation protocol. It never overwrites
`expert_results/ipo_*/pass1/expert_annotation_v1.json` and it does not promote
anything to `final/`.

## Deterministic correction artifacts

Seven Phase-1 hard conflicts are materialized as six versioned files:

`expert_results/<case_id>/audit/deterministic_corrections_v1.json`

Each artifact records the source pass1 SHA-256, original label fields,
replacement label fields, deterministic details, and an explicit
`promoted_to_final=false` safety marker. Evidence text and original reasoning are
not rewritten by this phase.

## Policy ambiguity split

The 33 Phase-1 policy ambiguities are split conservatively:

- 23 `BOUND_PROOF_DETERMINISTICALLY_RESOLVED`: formal concentration bounds
  explicitly exclude both frozen medium thresholds, so the existing
  `not_applicable` label is confirmed without coercing a strict inequality into
  equality.
- 2 `BOUND_PROOF_THRESHOLD_REVIEW`: the structured bound does not fully exclude
  the frozen threshold under the no-inference rule.
- 6 `CONTINUOUS_LOSS_COMPARABILITY_REVIEW`: mixed or unknown period types remain
  policy review.
- 2 `CONCENTRATION_PERIOD_SELECTION_REVIEW`: latest-period versus any-period
  policy remains unfrozen.

The implementation intentionally keeps the bound resolver conservative. A
single-counterparty bound without explicit aggregate/cardinality structure is not
silently multiplied into a top-five bound.

## Insufficient-input split

The 142 `INSUFFICIENT_INPUT` records are not treated as 142 annotation errors.
They are structured-input backfill work:

- 51 loss-period fact backfills;
- 37 comparable-revenue value backfills;
- 26 customer-ratio backfills;
- 25 supplier-ratio backfills;
- 3 cash-runway input backfills.

All 142 already have structurally valid cited Evidence because Phase 1 validates
Evidence before reaching the financial recomputation checks. Phase 2 therefore
routes them to `EXISTING_EVIDENCE_BACKFILL`, not automatic relabeling.

Priority is:

- `P0_POSITIVE_OR_NEEDS_REVIEW`: 51 records;
- `P1_REJECTED_LABEL_BACKFILL`: 91 records.

The Phase-2 runner writes machine-readable files to this directory:

- `phase2_summary.json`
- `correction_manifest.csv`
- `policy_resolution_queue.csv`
- `insufficient_input_backfill_queue.csv`

Generated reports are CI artifacts; only this governance README and the six
versioned deterministic correction artifacts are committed.
