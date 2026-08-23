# v0.4 PR-A Completion Report

> Status: **PR-A = COMPLETE / FROZEN**
> Materialization source revision: `13e0281f5e65a970caaf1255e56d08597e1ead70`
> Frozen feature schema: `v04_document_features_v1`
> Historical-state note: downstream milestone statements describe the PR-A freeze time; current program status is tracked in `ROADMAP.md`.

## 1. Objective and outcome

PR-A converted the official 2020–2024 IPO prospectus universe into an auditable, reproducible Document-X asset. The execution completed the A2 deterministic pilot, the subsequent three-case disconnected readiness proof, A3 full materialization and A6 full determinism verification without accessing 2025 blind outcomes.

| Item | Frozen result |
| --- | ---: |
| Official cases | 438 |
| Production analyses | 438 / 438 |
| Authoritative snapshots | 438 / 438 |
| Production feature vectors | 438 / 438 |
| Document feature dimension | 100 |
| Production failures | 0 |
| Silent drops | 0 |
| Oracle materialized | 60 |
| No reviewed Gold | 378 |
| Production ∩ Oracle | 60 |
| 2025 blind accessed | No |

The machine-readable freeze record is [`../reports/frozen/v04_pr_a_document_materialization_manifest.json`](../reports/frozen/v04_pr_a_document_materialization_manifest.json).

## 2. Determinism and coverage-hash lifecycle

The A3 first-run coverage hash was:

```text
47a15689789640f7abdf465b124f64742d96d8f4cb2a86b0a9d92107bf82dc42
```

The canonical A6 resumed-state hash, reproduced by the second A6 check, was:

```text
3b8201ea69f31804a7b99096d8392d3e32ca1bc60557dbf90e8050671eda2201
```

The transition is intentional rather than data drift. Across all 438 rows, `production_analysis_status` changed from `completed` to `skipped` because resume avoided re-analysis, and `production_snapshot_status` changed from `created` to `reused` because the authoritative snapshots already existed. Production and Oracle feature mismatch counts remained zero; the A6 report checked all 438 cases with `coverage_hash_ok=true`, `mismatch_count=0` and `passed=true`.

## 3. Provenance and artifact policy

`13e0281f...` is the committed source revision that produced the materialized artifacts. This report and the freeze manifest are committed later and do not redefine that source provenance.

The canonical bulk runtime artifacts remain local and ignored under `reports/v04_pr_a_full_13e0281/`; they are not committed to Git. The runtime execution context contains a local absolute configuration path, so external artifact packaging requires redaction while preserving hashes and source provenance:

```text
LOCAL_PATH_REDACTION_REQUIRED_BEFORE_EXTERNAL_ARTIFACT_PACKAGING = YES
```

## 4. Validation

- PR-A targeted tests: `17 passed`;
- frozen full suite: `1285 passed`, `2 warnings`;
- A6 checked cases: `438`;
- Production feature mismatches: `0`;
- Oracle feature mismatches: `0`;
- source hash mismatches: `0`;
- prior GitHub Actions checks on the materialization revision: green.

## 5. Next milestone at freeze time

PR-A was frozen and released PR-B — Market-X Core + Governed EOD Store as the
next formal milestone. PR-B subsequently completed and froze; this historical
PR-A report does not attempt to restate later Gate outcomes.
