# Role-B ALL79 final evidence receipt

This directory is the repository-safe export of local run `finaldayA_bundle10_real_all79_001`.

## Frozen results

| Measurement | Cases | M1 | M2 | Real LLM cases |
|---|---:|---:|---:|---:|
| Real-LLM gated | 79 | 61/102 = 59.80% | 93/191 = 48.69% | 79 |
| Deterministic offline (selected) | 79 | 70/102 = 68.63% | 103/191 = 53.93% | 0 |

The official thresholds are M1 >= 80% and M2 >= 85%. They are **not met**.
The real-LLM candidate was not promoted because it removed correct deterministic
risks and Evidence. `best_iteration.json` therefore selects `offline`.

The parent directory keeps the formal real-LLM benchmark handoff expected by
the release audit. This directory adds the offline comparator, call-quality
metadata, hash-only request/response provenance, M1/M2 waterfalls, monotonicity
decision, per-case completion hashes, and execution identity.

The call manifest contains 316 logical task records representing 323 network
attempts. Request IDs, provider responses, and successful structured payloads
are represented only by SHA-256 digests; their raw values are not included.

## Deliberately excluded

- prospectus PDFs and licensed source data;
- full per-case analysis results and runtime caches;
- raw prompts, raw provider responses, private LLM journal records, and keys;
- Evidence/exact text and local absolute paths;
- Validation and 2025 Blind inputs or outcomes.

`run_manifest.json` and `SHA256SUMS.txt` bind every exported file. Regenerate
with `scripts/export_v046_role_b_all79_release.py` from the ignored local run.
