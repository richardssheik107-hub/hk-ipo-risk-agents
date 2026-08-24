# ROLE B — PR-D DOCUMENT QA RESULT:

## PASS

Role B has verified the frozen PR-A Production Document-X handoff at transport,
manifest, aggregate-binding, case, schema, numeric, missingness, zero-fill, and
Production/Oracle-isolation levels. The PR-D Document-X input blocker is
removed. The package does not contain authoritative snapshots or Production
analysis, so the separate PR-G Evidence/Explanation gate remains PARTIAL.

```text
PR-D DOCUMENT-X INPUT QA:             PASS
PR-G EXPLANATION READINESS:           PARTIAL

Evidence bulk supplied:               NO
Evidence content audit:               NOT RUN
Physical-page linkage sample:         NOT RUN
Calculation/Verifier real sample:      NOT RUN

2025 blind outcome accessed:           NO
Frozen Parser/Retriever/Agent changed: NO
```

## 1. Package transport and extraction

Supplied package: `Role_B_PR_A_Production_DocumentX_438.zip`.

| Check | Expected | Actual | Result |
|---|---:|---:|---|
| ZIP SHA-256 | `c88cbb2545b75ac71b94e6499695a750c7aa039c94c05021e331e7d2c6ea5229` | exact match | PASS |
| ZIP size | small handoff | 540,021 bytes | PASS |
| Member count | 442 | 442 | PASS |
| Production JSON | 438 | 438 | PASS |
| Manifest JSON | 2 | 2 | PASS |
| README | 1 | 1 | PASS |
| `SHA256SUMS.txt` | 1 | 1 | PASS |
| Absolute/traversal paths | 0 | 0 | PASS |
| Duplicate member paths | 0 | 0 | PASS |

The archive was extracted once into the approved ignored runtime area outside
the repository. The extracted payload is 2,546,474 bytes. No ZIP copy, PDF,
second Production artifact set, or tracked runtime artifact was created.

## 2. Binary SHA256SUMS verification

`SHA256SUMS.txt` was parsed as a relative-path manifest and every referenced
file was hashed in binary mode.

```text
Checksum entries:               441
Files checked:                  441
Invalid checksum lines:         0
Duplicate checksum entries:     0
Missing checksum entries:       0
Unexpected checksum entries:    0
Hash mismatches:                0
```

The 441 checked files are the 438 Production JSON files, two manifests, and the
README. `SHA256SUMS.txt` does not self-hash.

## 3. Frozen binding

The packaged manifests are byte-identical to their committed frozen copies:

| Manifest | Binary SHA-256 | Matches repository |
|---|---|---:|
| `v04_pr_a_document_materialization_manifest.json` | `1a3a1e07d886e8b38b6839fa060172dd0e1ef237cd62eff61334118a1ff93483` | YES |
| `v04_pr_d_input_binding_manifest.json` | `ea303748eeb14b7d572f06256b4de018b7f349e294db86adf7b4e3ec921f3f5c` | YES |

Validated declarations:

```text
source_git_revision:                  13e0281f5e65a970caaf1255e56d08597e1ead70
official_case_count:                  438
production_materialized_count:        438
production_feature_count:             438
document_feature_dimension:           100
production_failure_count:             0
silent_drop_count:                    0
blind_2025_accessed:                  false
determinism_passed:                   true
production_feature_mismatch_count:    0
```

The aggregate was recomputed with the repository's existing
`pr_d_input_binding._component_identity` implementation. It sorts validated
entries by internal `case_id` and hashes their canonical JSON identity; the
Role-B auditor does not implement a competing aggregate algorithm.

```text
Expected artifact-set hash:
9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3

Recomputed artifact-set hash:
9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3

Binding: VERIFIED
```

## 4. Full 438-case Production Document-X audit

The audit streamed the JSON files one at a time and retained only aggregate
counts and bounded failure IDs. Every artifact was checked using the real
fields `feature_names`, `feature_values`, and `feature_schema_version`.

| Check | Result |
|---|---:|
| JSON readable | 438 / 438 |
| Filename equals `case_id` | 438 / 438 |
| Unique case IDs | 438 |
| Duplicate / missing / orphan | 0 / 0 / 0 |
| Schema | `v04_document_features_v1` |
| Feature names/values dimension | 100 / 100 |
| Canonical feature order | 438 / 438 |
| Feature manifest hash | 438 / 438 |
| Per-artifact content hash | 438 / 438 |
| `content_hash` present | 438 / 438 |
| `snapshot_hash` present | 438 / 438 |
| NaN | 0 |
| Positive / negative Infinity | 0 / 0 |
| Invalid numeric strings | 0 |
| Unexpected nulls | 0 |
| Unexpected extra fields | 0 |

Legitimate nulls were not treated as failures. In this schema, an unverified
risk intentionally has null score/level/calculation fields, and aggregate
max/mean scores are null when no verified score exists. The audit rejects nulls
only where the frozen feature semantics require a value.

## 5. Zero-fill and missingness audit

For each of the eight governed risk groups, the auditor checked the six-state
one-hot group, the adjacent missing indicator, verified-only score and ordinal,
calculation-success semantics, Evidence count, and corresponding aggregate
counts. It also reconciled verified max/mean scores and the total missing-risk
count.

```text
All-zero rows:                    0
Invalid state groups:             0
Missingness contradictions:       0
Suspicious zero-fill cases:       0
```

Ordinary zeros such as a valid Evidence count of zero were preserved and were
not classified as leakage or silent fill.

## 6. Production / Oracle isolation

All JSON keys were inspected recursively. No Production artifact contained a
forbidden Gold/Oracle field, including `gold`, `oracle`, `annotation`, `expert`,
`exact_text`, `evidence_role`, `source_authority`, `retrieval_label`, or
`locked_label`. The strict top-level artifact contract also found zero
unexpected fields.

```text
Forbidden field names:           0
Affected cases:                  0
PRODUCTION_ORACLE_LEAKAGE:        PASS
```

This is a data-level finding for all supplied Production Document-X artifacts,
in addition to the earlier code-path isolation review. It does not infer a
leak merely because Oracle artifacts exist elsewhere in the project.

## 7. Gate decision

### Gate 1 — PR-D Document-X Input QA

**PASS.** Transport, checksums, frozen binding, 438/438 case coverage,
schema/order/dimension, finite numeric values, zero-fill semantics, and
Gold/Oracle field isolation all passed. PR-D may safely consume this exact
frozen Production Document-X set.

### Gate 2 — PR-G Evidence / Explanation Readiness

**PARTIAL.** The package contains `snapshot_hash` provenance, but not the
authoritative snapshot bulk, Production analysis bulk, Evidence text, or PDFs.
Consequently the following remain explicitly NOT RUN:

- Evidence text sampling;
- one-based physical-page linkage against real results;
- Calculation-to-Evidence linkage sampling;
- Verifier and Agent provenance sampling.

The audit-only `DocumentExplanationRecordProposal` remains a viable minimal
read-only projection, but a public PR-G Schema and real Evidence-bulk audit are
separate downstream work. This limitation does not invalidate Gate 1.

## 8. Issues and handoff

| Issue | Severity | Blocks PR-D | Owner | Evidence |
|---|---|---:|---|---|
| Snapshot/Production-analysis bulk not supplied | Medium | No | A — Pipeline | Package inventory contains Document-X and manifests only; PR-G Evidence sampling is NOT RUN |
| Public Document Explanation Schema is not frozen | Medium | No | E — Product | Audit-only proposal exists; protected public Schema was unchanged |
| PR-D validator hardening for non-finite/additive fields remains advisable | Low | No for this verified bulk | D — Modeling | Role-B external audit and negative tests fail closed on these mutations |

## 9. Validation

```text
Role-B audit tests:                       16 passed
PR-A/PR-D/Document targeted regression:  165 passed in 49.35s
Full pytest:                              NOT RUN
PDF-heavy benchmark:                     NOT RUN
Formal PR-A/PR-D regeneration:            NOT RUN
Compileall / git diff --check:            PASS
Ruff:                                     NOT RUN (module not installed)
```

The first Role-B-only invocation had 13 pytest setup errors because its
task-specific temporary parent directory had not yet been created; no test
assertion failed. After creating that directory, the unchanged command passed
16/16. The broader targeted run then passed 165/165.

## 10. Change boundary

Only the Role-B auditor, its tests, this report, and ignored small Role-B JSON
reports were changed. No Parser, Retriever, Agent, prompt, risk rule, Verifier,
PR-D builder, production API, or public Schema was modified. No 2025 blind
outcome was accessed.

The branch was updated from the latest `origin/main` by an ordinary conflict-free
merge. No rebase, force push, task push, or PR creation was performed.
