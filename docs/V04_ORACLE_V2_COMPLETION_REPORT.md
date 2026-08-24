# v0.4 Oracle v2 Refresh Completion Report

> Status: **COMPLETE / FROZEN / A FINAL SIGN-OFF PASSED**
> Date: 2026-08-23
> Source revision: `7acbe3c6b3eb0a8939e09e8ae84306bcdfc5fb75`
> Historical-state note: merge / next-action statements describe the completion-time handoff; current program status is tracked in `ROADMAP.md`.

## 1. Scope and decision

This refresh creates a separately versioned, evaluation-only Oracle v2
sidecar from the current Expert Annotation inventory. It does not overwrite
the immutable PR-A Oracle v1 snapshot, modify Production Document-X, enter the
product runtime, train a PR-E model, or access 2025 blind outcomes.

Role A has completed the final review. The result is reproducibly
materialized, bound to the frozen PR-A Production and PR-C Outcome inputs, and
approved as the Oracle v2 freeze carried by this PR. Formal PR-E training had
not started at this freeze point.

## 2. Frozen contract

```text
schema_version        expert_oracle_document_features_v2
policy_version        oracle_gold_policy_v2
feature_count         142
evaluation_only       true
production_consumable false
```

The 142 feature names and ordering retain the historical Oracle feature
semantics, but v2 has its own schema, policy, manifest and content hashes.

## 3. Annotation inventory and audit policy

```text
inventory entries       101
valid annotations       100
invalid legacy entry      1
audit overlays           87
stale audit overlays     17
```

The invalid entry is the historical non-canonical `real_case_001` path. Its
annotation declares `ipo_2024_02410`; the canonical case directory is present
separately and is the only version eligible for v2 materialization.

Audit overlays are applied only when their recorded source annotation hash
matches the current pass-1 annotation after universal-newline normalization.
This makes the provenance decision identical on LF and CRLF checkouts. The 17
stale overlays are retained in the inventory and reported as `stale_not_applied`;
they are never silently applied to changed annotations. This is a conservative
provenance rule, not a new human judgment.

## 4. Official identity reconciliation

Production PR-A artifacts are authoritative for `case_id`, `document_id`,
stock code, cohort year, listing date and dataset split. Annotation metadata is
recorded for audit but cannot redefine the official cohort.

```text
identity reconciled     98
identity unresolved      0
non-official cases       2
```

Explicit non-official cases:

- `ipo_2024_00805`
- `ipo_2024_02613`

All 98 official materialized annotations were rebound to the authoritative
Production identity. This is expected because historical annotation metadata
did not carry the complete official listing identity.

The refresh verifies the complete frozen upstream contract before any
materialization. The verified binding covers all 438 official cases and the
actual PR-A Production and PR-C Outcome bulk artifact contents, rather than
trusting declared manifest strings alone.

```text
PR-D input-binding manifest  fca62fe4598f1f39adb9450c9b3e1bcecf45b0a968bc07cb46eaac3d8db1ab56
PR-A Production artifact set 9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3
PR-C Outcome artifact set    1f0ab1f8314a322abcaf4c88feead02e6cd114b478234b36388c27e33dc7ad90
official identity set        9b8e1e3e1677d1d613dade66931b00a9793b38636d8f7e7a0e86a76c47e30976
verified upstream binding    962b6da0de504ed5b33a25f2e46e6b545326dfea188b6c0f099374a632850794
```

## 5. Materialization and outcome eligibility

```text
materialized Oracle v2       98
strict usable                96
Development usable           77
Validation usable            19
outcome unavailable           2
```

The two feature artifacts retained with explicit unavailable outcome status
are:

- `ipo_2020_02599`: `missing_base_price`
- `ipo_2020_06688`: `no_eligible_session`

They are not treated as negative outcomes and are excluded from the strict PR-E
usable cohort.

## 6. Reproducibility

The committed implementation revision was used for a clean full
materialization and a same-provenance `--resume` verification.

```text
checked artifacts       98
mismatches               0
same-provenance resume   PASS
```

Canonical hashes:

```text
annotation inventory  50ca1079fabcdff678e5fa23a769bdb6f47da08284498a9a5dd94388c8787eee
official identity set 844b82179208d117e923262c64662f220dffd8abde66265c9614280daabd1af4
case set              4b9f95dd534051f4e0175a29be1ee520e8deb1ec76f672bd03b7595da407f87d
strict usable set     486a0c7d3977deacb5e3247e184064e96a684dbfdf8ef951b9df6cd32ce4da0f
feature manifest      99eeb0366a50b11b94f6e92820b6f1ef8535d5979ca6266d2af4f78618b40c11
artifact set          e73dd7f478fd4c421f6794cfa0c7808403cfb5d57dd0678eae1146aaeeff09d6
status set            83f4c0e84481b6a14ebe191663911dee473bd0c141f9bea2d8cf3568fa1cd7e2
freeze manifest       ddb175f48b7e8134c90c674e44d6173337dc2ea10e9eece103f70ae902e80294
```

The committed freeze manifest is the small manifest at
`reports/frozen/v04_oracle_v2_manifest.json`. The 98 generated feature files
and runtime output directories remain local, ignored and reproducible; they
are not repository payload.

## 7. Validation

```text
Oracle v2 / binding tests      51 passed
full pytest                    1390 passed, 2 warnings
validate_project               PASS (Mock: completed, verified=3, pending=1)
validate_competition_data      PASS
compileall                     PASS
git diff --check               PASS
```

Tests cover immutable Oracle v1 contract regression, deterministic inventory,
authoritative identity reconciliation, explicit exclusions, stale-audit
handling, schema/content corruption, fail-closed blind and duplicate cases,
same-provenance resume, provenance conflict and artifact-set determinism.

## 8. Isolation and safety

```text
Oracle v1 modified                 false
Production runtime wiring changed false
Public Schema / Protocol changed  false
2025 blind y accessed             false
PR-E model training started       false
bulk runtime artifacts committed  false
```

Oracle v2 remains a research sidecar. Production Agent, Retriever, Service,
Workflow and model-ready PR-D inputs do not import or consume it.

An earlier PR CI run exposed and rejected a non-portable test dependency on
ignored local PR-A/PR-C bulk artifacts and CRLF-sensitive source hashing. The
implementation normalizes JSON line endings and the tests construct their own
official identity/outcome inputs. P0 hardening then added fail-closed binding
to the frozen PR-A/PR-C bulk contents and PR-D governance anchors. The final
hashes above were regenerated from committed revision `7acbe3c...`; the Oracle
artifact-set hash remained unchanged, proving the hardening changed provenance
enforcement rather than Oracle feature semantics.

## 9. Final verdict

```text
ORACLE_V2_REFRESH = COMPLETE
ORACLE_V2_REPRODUCIBILITY = PASS
ORACLE_V2_PRODUCTION_ISOLATION = PASS
ORACLE_V2_UPSTREAM_BINDING = PASS
ORACLE_V2_A_FINAL_SIGN_OFF = PASS
ORACLE_V2_FREEZE_STATUS = COMPLETE_FROZEN
PR_E_FORMAL_TRAINING = NOT_STARTED
2025_BLIND_Y_ACCESSED = NO
```

At completion time the next action was to merge the reviewed Oracle v2 freeze
to `main`; that merge subsequently completed. The current formal Gate is PR-E,
which consumes this frozen v2 sidecar under a separate baseline task. This
completion report itself does not claim any PR-E measured result.
