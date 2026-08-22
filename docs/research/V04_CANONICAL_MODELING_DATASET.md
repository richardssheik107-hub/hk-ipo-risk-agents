# V04 PR-D — Canonical Model-ready Dataset Contract

> Status: **ENGINEERING PREPARATION / BLOCKED BY FORMAL PR-C FREEZE**  
> Owner: **D — Quant / ML Research**  
> Review: **A — identity / provenance / reproducibility / Blind Gate**

## Scope

PR-D introduces an additive canonical contract. It does not mutate the
historical document-only `v04_modeling_dataset_v1` or the historical
100-Document + 20-Extended join.

```text
dataset: v04_canonical_modeling_dataset_v1
matrix:  v04_canonical_model_matrix_v1
```

The required Core-first order is:

```text
Market Core       30 positions, required
Market Extended   20 positions, optional only when governed sources exist
Production Doc   100 positions, required
Oracle Doc       evaluation-only, Oracle intersection only
```

## Formal inputs

The CLI accepts only frozen upstream artifacts:

```text
PR-A Production Document-X / Oracle X
PR-B Market-X Core
PR-C FiveDayOutcomeTarget
PR-A / PR-B / PR-C reviewed freeze manifests
```

The three freeze manifests are hashed into one `source_manifest_hash`. Any X/y
identity mismatch, artifact tampering, manifest drift, unavailable target,
2025 Blind row, or unpassed upstream Gate fails closed.

## Cohorts

```text
Full Production Cohort      all cases with Production X + Core X + available y
Oracle Intersection Cohort  same requirements plus Oracle X
```

Unavailable outcomes remain in PR-D coverage with an explicit exclusion reason;
they are never zero-imputed or silently dropped.

## Fair comparison matrices

The canonical builder projects:

```text
M   Market Core (+ governed Extended when explicitly enabled)
P   Production Document
O   Oracle Document, Oracle intersection only
PM  Market then Production Document
OM  Market then Oracle Document, Oracle intersection only
```

Every feature name is component-prefixed. IDs, stock codes, document IDs,
Evidence IDs, Gold pages and target-derived values are provenance only and never
enter X.

The currently materialized 60-case Oracle inventory is Development-only. PR-D
therefore creates the fair five-group Oracle-intersection matrices only for
Development and records 2024 Oracle Validation as
`unavailable_no_reviewed_gold`. Full Production 2024 Validation remains
available. This limitation must not be hidden by borrowing Development rows or
using Production X as Oracle X.

## Time governance

Development and Validation are materialized separately. A PR-C target schema
cannot contain Blind, and PR-D adds a second Blind rejection. The PR-D CLI has no
2025 outcome option.

## Canonical implementation

```text
src/ipo_risk/schemas/canonical_modeling.py
src/ipo_risk/modeling/canonical_dataset.py
scripts/run_v04_pr_d.py
tests/unit/test_v04_canonical_modeling_dataset.py
```

Formal execution begins only after the PR-C freeze manifest exists:

```bash
python scripts/run_v04_pr_d.py \
  --pr-a-dir <PR_A_RUNTIME_DIR> \
  --pr-b-dir <PR_B_RUNTIME_DIR> \
  --pr-c-dir <PR_C_RUNTIME_DIR> \
  --pr-a-freeze-manifest reports/frozen/v04_pr_a_document_materialization_manifest.json \
  --pr-b-freeze-manifest reports/frozen/v04_pr_b_market_x_core_manifest.json \
  --pr-c-freeze-manifest reports/frozen/v04_pr_c_5d_outcome_manifest.json \
  --output-dir reports/v04_pr_d
```

Until the real PR-C Gate passes, this implementation is preparation and must not
be described as a completed PR-D materialization.
