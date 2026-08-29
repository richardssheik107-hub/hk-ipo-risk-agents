# Role-B v0.4.6 — Parser Preservation Batch 007

## Decision

```text
BATCH_007 = REJECTED_MISCLASSIFIED_ROOT
base = 4b342ef54ff0851d3d7733fdcf8240ec64e5f592
production_change = none
```

The six units labelled `parser_text_missing` by the period-selection audit were
checked against their 11 governed Evidence pages and the fixed-journal retrieval
trace. All 11 PDF pages have a non-empty extractable text layer with numeric
tokens. No page-level Parser preservation failure was found.

## Reclassification

Three units consumed at least one governed primary Evidence page but did not
form a complete deterministic fact:

```text
ipo_2020_00368 cash_runway
ipo_2020_00368 customer_concentration
ipo_2020_01961 supplier_concentration
```

They are reclassified to `deterministic_fact_missing`.

Three units did not receive their governed Evidence page in the bounded
candidate pool consumed by the Agent:

```text
ipo_2020_01961 cash_runway
ipo_2022_06610 customer_concentration
ipo_2022_06610 supplier_concentration
```

They are reclassified to `retrieval_candidate_miss`.

The audit persisted only case/risk identifiers, page counts, hashes, stage
labels and booleans. It did not persist prospectus text, Gold text, local paths,
prompts, provider responses, or secrets.

## Governance

```text
PDF pages checked = 11
non-empty text pages = 11
parser-preservation failures = 0
deterministic-fact reclassifications = 3
retrieval-candidate reclassifications = 3
network calls = 0
runtime Gold = false
Validation opened = false
2025 Blind accessed = false
```

Parser, Retriever, production extraction, evaluator, fixed-10, Existing Gold,
Prompt, provider/model, and frozen Role-D artifacts were unchanged.

## Next root

The next active root is `deterministic_fact_missing`. Any production change must
be a bounded, generic extraction fix on already-consumed Evidence. The three
Retriever misses remain a separate queued root and must not be disguised as a
Parser correction.
