# Role-B v0.4.6 — Legacy Cash Statement Batch 008

## Decision

```text
BATCH_008 = ACCEPTED_DETERMINISTIC_GAIN
base = 25a5a37e049006a00aca5c904b742986971d5cdb
production_commit = a602e409da8f10343ec6ba4ddcd5fbd77280f046
campaign_status = PAUSED_FOR_OWNER_REPLAN
```

The accepted change is a bounded, issuer-agnostic compatibility fix for legacy
Hong Kong financial statements. It recognizes Chinese-word years and dates,
an explicit Notes column, and traditional/simplified operating-cash-flow row
wording. A leading Notes reference is removed only when the statement has an
explicit Notes header and the exact `period_count + 1` value shape. Every other
column mismatch remains fail-closed.

No issuer, stock code, case ID, physical page, Evidence ID, Gold text, or
case-specific rule was added.

## Fixed-journal result

The canonical Development-only replay used the same immutable journal as
Batches 004 and 005:

```text
fixed10_hash = 5758b9f0b38fe0dabffade07d1da850938406b98ebe021dc65c93e806a1f3b6a
gold_manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
journal_hash = 8d5cb474aaf6db3dcc504b9b7f926ac5948834709d9798dd2bf11252e0dce5e2
network_calls = 0
```

| Mode | Metric | Batch 005 | Batch 008 | Change |
|---|---|---:|---:|---:|
| offline | M1 | 8/30 | 9/30 | +1 |
| offline | M2 | 13/48 | 15/48 | +2 |
| gated | M1 | 12/30 | 13/30 | +1 |
| gated | M2 | 18/48 | 20/48 | +2 |

The complete gated per-risk result is:

```text
cash_runway             M1 2/5   M2 4/11
customer_concentration  M1 4/8   M2 5/13
supplier_concentration  M1 3/9   M2 6/13
redemption_rights       M1 4/8   M2 5/11
```

Only cash runway changed. The other three families are byte-for-byte stable at
the benchmark-unit level. Three explicit control cases also retained identical
offline and gated M1/M2 counts before and after the change.

## Root-cause refinement

The consumed cash statement for the recovered unit contained the governed
cash and operating-cash-flow facts, but the old extractor could not bind its
Chinese-word periods and treated the Notes reference as a fourth observation.
The new generic grammar closes that sub-root.

The other Batch 007 reclassifications remain separate:

- one customer unit is a retrieval-candidate miss rather than an extraction
  failure;
- one supplier unit contains a ranked concentration table and remains a
  deterministic table-aggregation gap;
- the three previously queued retrieval misses remain retrieval work.

No Parser or Retriever change was made in this batch.

## Validation

```text
targeted tests                  179 passed
full pytest                     2212 passed, 3 warnings
compileall                      PASS
validate_project               PASS
validate_competition_data      PASS
validate_competition_runtime   PASS
git diff --check               PASS
Validation opened              false
2025 Blind accessed            false
Existing Gold modified         false
```

No fresh provider checkpoint was executed. The owner requested a stop after
the fixed-journal gate so that all experiment records could be uploaded and
the next campaign could be replanned. This must not be described as a missing
or failed fresh run.

## Stop point

```text
ROLE_B_CAMPAIGN = PAUSED_FOR_OWNER_REPLAN
NEXT_BATCH = NOT_STARTED
```

The remaining gaps are not authorized for automatic continuation from this
commit.
