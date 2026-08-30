# Role-B v0.4.6 — All-Rounds Safe Results Bundle

This directory is the repository-safe index of local Role-B experiment rounds.
It preserves completed runs and incomplete/preflight-only attempts rather than
silently dropping unsuccessful work.

Files:

- `all_rounds_manifest.json`: complete summary-level JSON and SHA-256 inventory;
- `all_rounds_metrics.csv`: compact per-run metric/status table.

`all_rounds_metrics.csv` is the round-level source of truth inside this research
archive. Historical `best_checkpoint.json` files are controller snapshots and
may lag later accepted or rejected runs. For the released v1.0.0 result, use
`reports/v045_role_b/document_benchmark_summary.json` and the live release
documents instead of inferring the final score from this archive.

The source report tree is intentionally not copied. It contains approximately
6.4 GiB of licensed PDFs, parser/runtime caches, complete analysis payloads,
private LLM journals, and local execution details. None of those are valid Git
artifacts.

The exporter rejects raw prompts/responses, Evidence/exact text, API key values,
Authorization values, local home paths, prospectus paths, PDFs, and caches. A
`preflight_only` row means the attempt existed but did not produce a governed
primary result; it must not be interpreted as a successful benchmark.

Regenerate from the local ignored report tree with:

```powershell
python scripts/export_v046_role_b_safe_results.py
```

This bundle does not modify Existing Gold, does not open Validation, and does
not access 2025 Blind outcomes.

The frozen-protocol source-binding ceiling derived from this research line is
documented separately in
`docs/research/V046_ROLE_B_M1_REACHABILITY_PROOF.md`.
