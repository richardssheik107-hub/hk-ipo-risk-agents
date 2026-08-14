# 0368.HK Parser Preservation Audit

## Scope

This Phase 0.6B.2 diagnostic measures whether the current
`PyMuPDFDocumentParser` preserves the content of the 17 Evidence records in the
formal `gpt_expert_v1.1` first-pass annotation for `ipo_2020_00368`.

The measured path was strictly:

```text
original prospectus PDF
-> PyMuPDF page.get_text("text")
-> one non-blank DocumentChunk per physical page
-> deterministic comparison with Expert Evidence
```

No Retriever, LLM, Agent, Verifier, Supervisor, Human Golden, market outcome or
2025 blind data was used. The production Parser was not changed.

## Input provenance

- Case: `ipo_2020_00368`
- Stock: `0368.HK`
- Annotation version: `gpt_expert_v1.1`
- Annotation SHA-256:
  `92e9d6be1fd3a40da0f61e41bdd0522e0e3f27a8d9414086fc1327fb3abd2520`
- Prospectus SHA-256:
  `642a84775c107ebbc4a7534f88b2aba6399410937933d678b223feb342977a82`
- Physical PDF pages: `420`
- Non-blank parser chunks: `418`
- Parser page errors: `0`

The PDF path was resolved from the catalog manifest and verified by SHA-256. No
local absolute path or PDF binary is stored in this report.

## Results

| Metric | Result |
| --- | ---: |
| Total Evidence | 17 |
| Required Evidence | 13 |
| Page Preservation Rate | 100.00% |
| Normalized Exact-text Match Rate | 82.35% |
| Core Text Preservation Rate | 100.00% |
| Numeric Preservation Rate | 100.00% |
| Required Evidence PASS Rate | 76.92% |
| Required PASS-or-PARTIAL Rate | 100.00% |
| Table Evidence | 11 |
| Table Fully Recoverable Rate | 72.73% |
| Table At-least-partially Recoverable Rate | 100.00% |
| Diagram Evidence | 1 |
| PASS / PARTIAL / FAIL | 13 / 4 / 0 |

`Required Evidence PASS Rate` is intentionally stricter than
`Required PASS-or-PARTIAL Rate`: the three required supplier-table records retain
their text and all numbers, but flattened reading order prevents a FULL table
structure claim.

## PARTIAL Evidence

| Risk | Page | Why |
| --- | ---: | --- |
| `supplier_concentration` | 140 | `READING_ORDER_DISTORTED`, `TABLE_STRUCTURE_PARTIAL` |
| `supplier_concentration` | 141 | `READING_ORDER_DISTORTED`, `TABLE_STRUCTURE_PARTIAL` |
| `supplier_concentration` | 142 | `READING_ORDER_DISTORTED`, `TABLE_STRUCTURE_PARTIAL` |
| `redemption_rights` | 95 | `DIAGRAM_RELATIONSHIP_LOST`; all labels and four `100%` values remain present |

There were no failed Evidence records, missing Evidence pages or missing numeric
facts. Fourteen records required only whitespace/layout normalization before an
exact match. This is recorded as `NORMALIZATION_ONLY_DIFFERENCE`, not a content
loss.

## Decision

```text
0368_DIAGNOSTIC = PASS
PARSER_DECISION = KEEP_CURRENT_PARSER_FOR_RETRIEVAL_EXPERIMENTS
RECOMMEND_RETRIEVER_AUDIT = true
TABLE_AWARE_ENHANCEMENT = FUTURE_CANDIDATE
```

The financial values are stable, and customer/supplier table content remains at
least partially recoverable from flattened text. The current Parser does not
preserve diagram relationships and should not be described as table-aware.

This single-case result does not establish production readiness. Expansion to a
diverse 10-case Parser audit requires separate approval.

## Reproduction

```powershell
$env:PYTHONPATH = "src"
python scripts/run_parser_preservation_audit.py `
  --case-id ipo_2020_00368 `
  --annotation <path-to-expert_annotation_v1.json> `
  --pdf-root <authorized-prospectus-root>
```

Detailed JSON and CSV are generated locally under
`reports/parser_preservation/ipo_2020_00368/` and remain ignored runtime
artifacts because the JSON preserves source Evidence excerpts.
