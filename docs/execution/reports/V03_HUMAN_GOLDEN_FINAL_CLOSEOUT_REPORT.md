# v0.3 Human Golden Final Closeout Report

## Governance decision

Owner permanently removed independent second review as a Financial/Business
formal-Golden requirement on 2026-08-12. Frozen policy:

```text
policy = single_named_human_review_v1
independent_second_review_required = false
double_review_preserved_when_available = true
```

This is a governance-policy change, not a claim that one review became two.
`second_reviewer` remains empty for Financial/Business and no AI reviewer was added.

## Git provenance

```text
base = PR #39 head@4c599419c27eecca1dea2e2d6bc4731e8b6ea219
branch = chore/v03-human-golden-final-closeout
Financial primary source = PR #38 / 64beab8858ee16d5d2d5de2e8515378e109d122d
Business primary source = canonical member-5 records from V3-7
Legal formal source = PR #36 / ea6f9ef87c80dc3a78e018a5794e4717ca9f56fd
```

## Human review audit

| Domain | Real rows | Primary reviewed | First reviewed | Double reviewed | Adjudicated | Unresolved | Formal promoted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Financial | 23 | 23 | 23 | 0 | 0 | 0 | 23 |
| Legal | 8 | 8 | 0 | 4 | 4 | 0 | 8 |
| Business | 3 | 3 | 3 | 0 | 0 | 0 | 3 |

Financial reviewer is `member-3`; Business reviewer is `member-5`. Legal
second-review/adjudication provenance is unchanged. Single-review rows do not require
reviewer independence; existing multi-review rows continue to require it.

## Formal evaluation

Frozen real-PDF offline evaluation used 14 real development/development-exception
cases, completed all 14, and did not access 2025 blind data. No production rule,
Retriever, threshold or Golden judgment was changed after seeing the results.

| Scope | Rows | Cases | Precision | Recall | F1 | Verified precision | Evidence R@1 | R@3 | R@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Financial | 23 | 6 | 100.00% | 10.00% | 18.18% | 100.00% | 9.09% | 18.18% | 18.18% |
| Legal | 8 | 8 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| Business | 3 | 2 | 0.00% | 0.00% | 0.00% | 0.00% | 50.00% | 50.00% | 50.00% |
| Cross-domain | 34 | 14 | 50.00% | 7.69% | 13.33% | 50.00% | 12.50% | 18.75% | 18.75% |

These values are formal under the current Human Golden policy but show substantial
model recall gaps. Target thresholds are not claimed as met. Numeric extraction
metrics are `NOT_AVAILABLE` because the canonical schema has no frozen
`gold_amount/gold_unit/gold_period` columns.

## Gate A and safety

All A01—A12 criteria are `PASS` under the current single-review policy.

```text
GATE_A_OVERALL_STATUS = PASS
OWNER_WAIVER_STATUS = SUPERSEDED_BY_SINGLE_REVIEW_POLICY
2025_BLIND_ACCESSED = false
2025_BLIND_USED_FOR_TUNING = false
PUBLIC_SCHEMA_CHANGED = false
COMPONENT_PROTOCOL_CHANGED = false
V04_MARKET_WORK = NOT_STARTED
```

## Limitations

- Financial/Business are single-human-reviewed, not independently double-reviewed.
- Formal recall and F1 are materially below project targets.
- Extraction metrics are unavailable with the current canonical columns.
- External real-LLM smoke and disposable clean-environment validation were not run.
- PR #39 and this stacked closeout PR remain unmerged; no tag or Release exists.
