# Oracle Document Modeling Pipeline

This is an evaluation-only research path, never production runtime:

`current pass1 + explicit audit overrides -> EffectiveRiskGoldView -> expert_oracle_document_features_v1 -> Market X + raw 5D outcome -> model`

It does not read PDFs or call a retriever, LLM, agent, verifier, supervisor, or
the production `v04_document_features_v1` builder.  Oracle features contain
only structured risk states, confidence, evidence counts, and calculation
availability: not reasoning, evidence text, company text, a fabricated score,
or post-listing knowledge.

Audit precedence is field-level. Current `pass1` is always the base. A
self-contained audit entry with an explicit `resolved_state` overrides only its
named risk; a stale audit never restores its historical pass1. Artifacts retain
the base/audit hashes, applied risks and deterministic effective hash.

## Local batch commands (PowerShell)

Run from the repository root with the project virtual environment and
`$env:PYTHONPATH='src'`.

1. Index: `python scripts/index_oracle_gold.py --output-dir reports/oracle_gold_index`.
   Outputs inventory JSON/CSV and failure CSV; it reads annotations only.
2. Oracle X: `python scripts/build_oracle_document_features.py --all-eligible --output-dir reports/oracle_document_features --resume`.
   Outputs one feature artifact per case plus failure report. Resume reuses only
   identical content hashes; changed provenance is a conflict, never overwrite.
3. Modeling dataset: pending market snapshot and outcome materialisation. It
   must retain raw 5D returns separately from any owner-frozen binary target,
   use development/validation chronological splits, and export 2025 X without y.
4. Baseline: pending dataset materialisation. It will compare document-only,
   market-only and combined inputs with preprocessing fitted on development only.

The intended comparison is Oracle vs pipeline V1/V2/V2+LLM under the same
Market X, y, split and model, to decompose document-pipeline error from signal
or target limitations.
