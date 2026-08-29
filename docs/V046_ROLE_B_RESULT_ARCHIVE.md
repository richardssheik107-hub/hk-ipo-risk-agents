# Role-B Fixed-10 Result Archive and M1/M2 Forensics

## Status

```text
archive_status = COMPLETE
official_fixed10_iterations = 4
latest_forensic_packet = forensic_011
validation_opened = false
blind_2025_outcome_accessed = false
```

This document indexes the governance-safe artifacts retained from the four
fixed-10 Role-B runs and the subsequent end-to-end M1/M2 forensic audit. The
archive preserves reported metrics, case completion state, benchmark rows,
hashes, and stage-level diagnostics. It intentionally excludes prospectus
PDFs, raw Evidence text, complete model responses, agent journals, caches,
credentials, and local absolute paths.

## Fixed-10 iteration history

All four rounds used the same frozen ten-case subset. Every round completed
10/10 cases with a real external LLM, reported zero failed cases, kept
Validation closed, and did not access 2025 Blind outcomes.

| Iteration | Runtime Git revision | M1 | M2 | Recall@1 | Recall@3 | Recall@5 | Dominant failure |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `iter_001` | `1c41860db41597b14937f2e16eb2e9d963b1527d` | 0/30 (0.00%) | 2/48 (4.17%) | 2.08% | 4.17% | 4.17% | semantic extraction miss (23) |
| `iter_002` | `23ec108943b5b8b7f42414121f898fd972cc27ad` | 3/30 (10.00%) | 4/48 (8.33%) | 6.25% | 8.33% | 8.33% | semantic extraction miss (22) |
| `iter_003` | `23ec108943b5b8b7f42414121f898fd972cc27ad` | 4/30 (13.33%) | 6/48 (12.50%) | 6.25% | 10.42% | 12.50% | semantic extraction miss (21) |
| `iter_004` | `5f1d5d8fe90adbf93e72a4ffec5eed174d9cf781` | 7/30 (23.33%) | 9/48 (18.75%) | 12.50% | 16.67% | 18.75% | semantic extraction miss (16) |

The fixed subset hash is
`5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a`.
The Existing-Gold source manifest hash is
`fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c`.

Each iteration directory contains exactly the following safe result set:

- `iteration_context.json`
- `iteration_summary.json`
- `failure_focus.json`
- `case_statuses.json`
- `evaluation/document_benchmark_summary.json`
- `evaluation/risk_benchmark.csv`
- `evaluation/evidence_benchmark.csv`

## Current forensic packet

The current detailed packet is stored under
`reports/frozen/v046_role_b_m1_m2_forensics/forensic_011/`.

Its audited identity is:

```text
analysis_base = main@65fb2ea4e3969583c20ff2f68eeff6905b97169e
authoritative_runtime_run = main_candidate_real
runtime_artifact_git_revision = 8ae09505b3b31ad88e6d5dc2b1f3faea526475aa
role_b_runtime_tree_matches_analysis_base = true
fixed10_subset_hash = 5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a
existing_gold_manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
provider = openai_responses
model = ark-code-latest
```

The forensic decomposition reports:

```text
M1 = 8/30 = 26.67%
M2 = 11/48 = 22.92%
Risk trace coverage = 30/30 PROVEN
Evidence trace coverage = 48/48 PROVEN
largest first-proven root cause (retrieval candidate miss) = 6 M1 units / 16 M2 units
recommended first single-module Fixer = financial adapter
maximum non-additive affected scope = 5 M1 units / 14 M2 units
```

The packet is diagnostic evidence, not a tuning result. No new LLM call was
made for the forensic audit, no Validation data was opened, and no 2025 Blind
outcome was accessed. Historical iteration results and the forensic packet
have distinct code identities and must not be treated as a controlled A/B
comparison.

## Validation

The diagnostic implementation was validated on its analysis base with:

```text
targeted tests = 10 passed
full pytest = 2122 passed, 2 warnings
compileall = PASS
validate_project = PASS
validate_competition_data = PASS
validate_competition_runtime = PASS
git diff --check = PASS
```

## Governance boundary

This archive does not claim that M1/M2 release targets are met. It records the
observed quality and root-cause evidence without changing Gold, prompts,
Retriever policy, Agent rules, Verifier behavior, frozen artifacts, Validation,
or 2025 Blind data.

## Historical v0.4.5 GLM-5.3 benchmark

```text
status = MEASURED_FAIL
source_branch = feat/v045-role-b-glm53-benchmark
source_commit = 905ffb3
source_pr = #186
semantic_calls = 30
structured_contract_valid = 2/30
M1 = FAIL
M2 = FAIL
offline_baseline_outperformance = NOT_PROVEN
```

This is historical negative experimental data and is not part of the current
v0.4.6 fixed-10 results. It must not be interpreted as evidence that GLM-5.3 is
permanently unusable; it records only that the provider/model/config/runtime
combination tested at that time did not satisfy the structured-output contract.

The legacy harness is intentionally excluded from runtime. The current
implementation remains the v0.4.6 Role-B diagnostic/gated workflow.
