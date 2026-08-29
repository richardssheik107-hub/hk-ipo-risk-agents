# Role-B v0.4.6 — Wide Sprint Batch 009

## Decision

```text
BATCH_009 = PARTIAL_ACCEPT
BEST_KNOWN_GOOD = bd09c320f12a0ab9de51c0743ddb0bbc00b06346
accepted = generalized Legal lifecycle recognition
rejected = direct ranked concentration-table extraction
campaign = PAUSED_FOR_OWNER_REPLAN_AFTER_BATCH009
```

The branch was rebased onto `main@9758e4c4154aada4c308fa0a5bf86e23d3d2d948`.
Batch008's accepted legacy cash-statement behavior was transplanted as
`ee86fd7`. The Legal lifecycle fix is the independent commit `bd09c32`.

## Comparable fixed-journal result

All measurements use the same Development-only fixed10 and immutable local
journal. No remote provider call was made.

| Checkpoint | Offline M1 | Offline M2 | Gated M1 | Gated M2 |
|---|---:|---:|---:|---:|
| latest-main Batch008 floor | 9/30 | 15/48 | 13/30 | 20/48 |
| accepted Legal lifecycle | 9/30 | 15/48 | **14/30** | **21/48** |
| ranked-table candidate | 9/30 | 15/48 | 14/30 | 21/48 |

The accepted Legal change raises `redemption_rights` from 4/8 to 5/8 M1 and
recovers one Evidence unit. It recognizes generic Chinese/English restoration
wording and preserves Builder-declared lifecycle uncertainty instead of
converting it to a historical hard rejection. It does not convert uncertainty
to a positive conclusion.

## Rejected ranked-table hypothesis

A narrow grammar was tested for tables that contain the correct counterparty
and denominator, an explicit rank header, a complete ordered 1–5 block, and a
reported total. On the real 0368.HK Parser output it read customer 45.7/97.0
and latest supplier 11.5/24.9 correctly. Targeted tests passed 105/105.

The canonical fixed-journal run did not improve M1 or M2 and reduced supplier
existence F1 from 0.875 to 0.80. The entire production/test candidate was
therefore reverted. No ranked-table code remains in the accepted checkpoint.
Any later attempt needs stronger candidate-context gating and must prove that
the extracted table is the governed risk fact, rather than merely a readable
table.

## Remaining funnel

- Retrieval candidate generation remains the largest proven first-failure
  layer in `forensic_011` (6 M1 and 16 M2 units).
- One audited redemption Evidence page remains at rank 18, outside the Legal
  Agent's bounded 10-item consumption window. A future fix should improve
  transaction/lifecycle co-occurrence ranking rather than broadly increasing
  the limit.
- Legal status recovery exposed remaining exact page/anchor Evidence-binding
  misses; M2 must be addressed independently from risk existence.
- Numeric extraction and fixed-vs-fresh LLM Evidence variance remain open.

## Validation

```text
Legal targeted tests = 24 passed
combined Role-B targeted tests after rebase = 203 passed
ranked-table candidate tests = 105 passed (candidate later reverted)
compileall = PASS
validate_project = PASS
validate_competition_data = PASS
validate_competition_runtime = PASS
git diff --check = PASS after accepted code
```

Full pytest at the accepted code SHA produced `2291 passed, 3 failed, 3
warnings`. The three failures are outside Role-B: on Windows, Git checks out a
frozen PR-F JSON with CRLF bytes while its receipt binds the LF byte hash. No
PR-F artifact or checksum was modified. This limitation remains explicit and
is not relabeled as PASS.

## Governance

```text
Existing Gold modified = false
runtime received Gold = false
Validation opened = false
2025 Blind accessed = false
fresh provider calls in Batch009 = 0
PDF/raw provider response/cache committed = false
issuer/stock/case/page hardcode = false
```

Large local runtime directories remain excluded from Git. The committed
machine-readable artifacts contain only bounded metrics, hashes, decisions and
root-cause labels.
