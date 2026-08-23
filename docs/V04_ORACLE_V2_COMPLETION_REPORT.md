# v0.4 Oracle v2 Refresh Completion Report

> Status: **FREEZE CANDIDATE / READY FOR A FINAL SIGN-OFF**
> Date: 2026-08-23
> Source revision: `330d2c455f6f4cc339997973d1b946f1804068b5`

## 1. Scope and decision

This refresh creates a separately versioned, evaluation-only Oracle v2
sidecar from the current Expert Annotation inventory. It does not overwrite
the immutable PR-A Oracle v1 snapshot, modify Production Document-X, enter the
product runtime, train a PR-E model, or access 2025 blind outcomes.

The result is reproducibly materialized and is ready for Role A final review.
It is not described as frozen on `main` until that review and merge complete.

## 2. Frozen candidate contract

```text
schema_version       expert_oracle_document_features_v2
policy_version       oracle_gold_policy_v2
feature_count        142
evaluation_only      true
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
stale audit overlays     74
```

The invalid entry is the historical non-canonical `real_case_001` path. Its
annotation declares `ipo_2024_02410`; the canonical case directory is present
separately and is the only version eligible for v2 materialization.

Audit overlays are applied only when their recorded source annotation hash
matches the current pass-1 annotation. The 74 stale overlays are retained in
the inventory and reported as `stale_not_applied`; they are never silently
applied to changed annotations. This is a conservative provenance rule, not a
new human judgment.

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

They are not treated as negative outcomes and are excluded from the strict
PR-E usable cohort.

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
annotation inventory  c70badc2f61e8691ef8f1fceffa3284c46035a1fd09b008abc7af0d1003fcaaa
official identity set 844b82179208d117e923262c64662f220dffd8abde66265c9614280daabd1af4
case set              4b9f95dd534051f4e0175a29be1ee520e8deb1ec76f672bd03b7595da407f87d
strict usable set     486a0c7d3977deacb5e3247e184064e96a684dbfdf8ef951b9df6cd32ce4da0f
feature manifest      99eeb0366a50b11b94f6e92820b6f1ef8535d5979ca6266d2af4f78618b40c11
artifact set          1d3f9e309da659aed4ba846dca225f9f488b54ced6bbfa9ab3f04fe8ff5ef991
status set            83f4c0e84481b6a14ebe191663911dee473bd0c141f9bea2d8cf3568fa1cd7e2
freeze candidate      a0c222164d393c9a4ca67a2c36a3f79f14a1dd50f2e9fe918a5ddf5415afd8ef
```

The committed freeze candidate is the small manifest at
`reports/frozen/v04_oracle_v2_manifest.json`. The 98 generated feature files
and runtime output directories remain local, ignored and reproducible; they
are not repository payload.

## 7. Validation

```text
Oracle v2 targeted tests       29 passed
full pytest                    1373 passed, 2 warnings
validate_project               PASS (Mock: completed, verified=3, pending=1)
validate_competition_data      PASS
compileall                     PASS
git diff --check               PASS
```

Tests cover immutable Oracle v1 regression, deterministic inventory,
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

## 9. Final verdict

```text
ORACLE_V2_REFRESH = COMPLETE
ORACLE_V2_REPRODUCIBILITY = PASS
ORACLE_V2_PRODUCTION_ISOLATION = PASS
ORACLE_V2_FREEZE_STATUS = FREEZE_CANDIDATE_READY_FOR_A_FINAL_SIGN_OFF
PR_E_FORMAL_TRAINING = NOT_STARTED
2025_BLIND_Y_ACCESSED = NO
```

Next action: Role A reviews the implementation, frozen candidate manifest,
stale-audit policy and CI. Only after approval and merge may Oracle v2 be
called frozen on `main` and consumed by formal PR-E diagnostics.
