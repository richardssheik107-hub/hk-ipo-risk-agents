# Role-B v0.4.6 — Ranked Table Evidence Batch 010

## Decision

```text
BATCH_010 = ACCEPTED_MONOTONIC_GAIN
BEST_KNOWN_GOOD = 1d73c5157048d7ea8d322ec4fe938f71cefa3301
next = Development40 numeric extraction / risk conversion funnel
```

Batch 009 proved that directly converting a readable ranked concentration
table into a clean policy fact can suppress an existing pending risk. Batch
010 keeps that decision path reverted. Instead, it recovers only a strict,
complete rank-1-to-5 row-order view of the same physical page and attaches
those already-retrieved pages to an existing concentration risk.

The detector requires five ordered ranks, amount/percentage pairs, a reported
total whose percentage agrees with the five rows within printed rounding, a
period label, and an unambiguous customer/supplier vocabulary. It receives no
case, issuer, stock, page, Evidence ID, or Gold input.

## Comparable result

All fixed10 gated measurements use the same Development-only subset and the
same immutable 40-record journal. Wider-set measurements are zero-network
offline runs.

| Scope | Before M1 | After M1 | Before M2 | After M2 |
|---|---:|---:|---:|---:|
| fixed10 gated | 14/30 | **15/30** | 21/48 | **24/48** |
| fixed10 offline | 9/30 | **10/30** | 15/48 | **18/48** |
| Development20 offline | 13/50 | **14/50** | 25/98 | **28/98** |

The three recovered Evidence units are the real supplier ranked-table pages
for the audited 0368 Development case. The risk remains `pending /
needs_review / medium`; its score, level, verification status, calculation,
and policy decision are unchanged. The single M1 gain comes from parsing the
already-supported Chinese-word reporting date as a real narrative period.
The extra ten Development cases stayed flat, so they did not hide a wider-set
regression.

## Validation

```text
targeted Role-B tests = 120 passed
full pytest = 2304 passed, 2 skipped, 3 warnings
validate_project = PASS
validate_competition_data = PASS
validate_competition_runtime = PASS
compileall = PASS
git diff --check = PASS
fixed10 = 10/10 completed
Development20 = 20/20 completed
fixed journal records = 40
network calls = 0
```

The first full-suite pass exposed a Windows checkout line-ending mismatch in
the pre-existing frozen PR-F four-file handoff. Normalizing the worktree bytes
to the committed LF blobs made the three byte-hash tests pass; no frozen file
content or checksum was changed or committed.

## Governance

```text
Existing Gold modified = false
runtime received Gold = false
Validation opened = false
2025 Blind accessed = false
external provider calls = 0
PDF/runtime/cache committed = false
issuer/case/stock/page special case = false
```

Fixed10 and Development20 remain diagnostic Development subsets, not the final
competition gate. The next governed expansion is Development40, followed by
ALL79 only after the next generic extraction/conversion root is accepted.
