# v0.4 PR-D Canonical Dataset Completion Report

> Status: **COMPLETE / FROZEN**
> Formal run date: 2026-08-23
> Source main: `a1385dba65c10654bdd2f452adee4e30c7f614a0`

## 1. Formal materialization result

PR-D joined the frozen Production Document-X, Market-X Core and PR-C Outcome
sets after validating `v04_pr_d_input_binding_v1`. No upstream artifact,
threshold, split or feature contract was changed.

| Gate | Result |
| --- | ---: |
| Official upstream cases | 438 |
| Production model-ready | 424 |
| Explicit target exclusions | 14 |
| Development model-ready | 354 |
| Validation model-ready | 70 |
| Missing base price | 12 |
| No eligible session | 2 |
| Generation failures | 0 |
| Silent drops | 0 |
| Identity mismatches | 0 |
| Schema / feature-order drift | 0 |
| Input-binding drift | 0 |

The 14 unavailable targets remain explicit exclusions. No missing outcome was
converted to zero or to a negative class.

## 2. Frozen input provenance

| Input | Count | Aggregate identity |
| --- | ---: | --- |
| PR-A Production Document-X | 438 | `9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3` |
| PR-B Market-X Core | 438 | `6803424877560945de61a6647863365c4e91b786bc9f12f1451da4a25c3b2eb6` |
| PR-C Outcome | 438 | `1f0ab1f8314a322abcaf4c88feead02e6cd114b478234b36388c27e33dc7ad90` |

- PR-C target-set hash: `5e0dedc8d207c8e73ca6439efb72f463c6b6f276c1c6c48e3ad7a989ad1533f4`
- official identity-set hash: `9b8e1e3e1677d1d613dade66931b00a9793b38636d8f7e7a0e86a76c47e30976`
- PR-D binding manifest hash: `fca62fe4598f1f39adb9450c9b3e1bcecf45b0a968bc07cb46eaac3d8db1ab56`
- joined source-manifest hash: `f95858fb8a0cdcd34697bccee07dab6517446d75b77703c1e69d19de53b6b8a7`
- coverage hash: `a8e1c21b02b21b99bcbe91192744f8c88c174585cd79101d91b310637046d98b`

## 3. Canonical datasets

| Dataset | Rows | Canonical content hash |
| --- | ---: | --- |
| Full Production / Development | 354 | `11ffc4c04facacd23e5c554d4154d3cc8bec8d62d65d6278e012ba698a9a356d` |
| Full Production / Validation | 70 | `8842928b61fe13b8161009aea74a71850efecc327e295a6e6c3d151121bc83b4` |
| Historical Oracle v1 / Development intersection | 55 | `356b8cb264db9ea0c5399bff59e9c2c4e9ad4060c2020a09f201df881eb6d95c` |

Canonical schema: `v04_canonical_modeling_dataset_v1`. Production matrices
retain 30 Market positions, 100 Production Document positions and 130 PM
positions. Identity fields, target fields, Evidence IDs and pages are not in
the feature-name arrays.

The small authoritative freeze record is:
`reports/frozen/v04_pr_d_canonical_dataset_manifest.json`, with self-freeze
hash `f6900c707187c23c5d01fa98fc8d9d21d040ce2c3ffa0a2a6340a0947f78e80d`.
Bulk datasets and matrices remain local runtime artifacts and are not committed.

## 4. Reproducibility and governance

- first governed materialization: PASS (`1.718 s`);
- same-provenance `--resume`: PASS (`2.005 s`);
- row order, case set, feature order, values, targets, exclusions and hashes:
  unchanged;
- changed provenance/content: fail-closed contract covered by automated tests;
- 2025 Blind y accessed: **NO**.

Oracle v1 remains the immutable, evaluation-only PR-A historical snapshot: 60
materialized, 55 currently outcome-eligible Development rows and no Validation
rows. Three Oracle identity mismatches are explicitly excluded from the Oracle
intersection without blocking the Production cohort. Oracle v2 remains planned
and **NOT FROZEN**.

## 5. Validation

- PR-D targeted / canonical / Oracle tests: `26 passed`;
- full pytest: `1354 passed`, 2 warnings;
- `validate_project`: PASS under explicit Mock configuration;
- `validate_competition_data`: PASS;
- `compileall`: PASS;
- `git diff --check`: PASS.

## 6. Gate decision

```text
PR-D COMPLETE / FROZEN
PR-E FORMAL BASELINE UNBLOCKED / NOT STARTED
2025 BLIND Y ACCESSED = FALSE
```
