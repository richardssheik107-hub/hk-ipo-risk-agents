# Expert Annotation Phase 2b

Phase 2b handles only the 51 `P0_POSITIVE_OR_NEEDS_REVIEW` records produced by
Phase 2.

## Safety

- `pass1/expert_annotation_v1.json` is immutable.
- No result is promoted to `final/`.
- Evidence text and reasoning are not rewritten.
- Phase 2b normalizes existing structured facts before considering any prose
  extraction.
- Cross-period level disagreement and zero-denominator cases remain policy
  review; the code does not invent an aggregation rule.

## Output

Each affected Case receives:

`expert_results/<case_id>/audit/structured_input_backfill_v1.json`

The artifact records:

- source pass1 SHA-256;
- original P0 finding;
- cited Evidence page/source references;
- canonical calculation inputs;
- normalization source fields;
- deterministic re-audit status;
- proposed replacement only when the backfilled facts make a hard conflict
  deterministic.

Run:

```bash
python scripts/run_expert_annotation_phase2b.py
```

Machine-readable summaries are written under
`reports/annotation_audit/phase2b/`.
