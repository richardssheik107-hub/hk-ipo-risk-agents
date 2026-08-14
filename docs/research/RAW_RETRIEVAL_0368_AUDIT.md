# 0368.HK Isolated Raw Retriever Audit

## Scope and isolation

This Phase 0.6B.3 diagnostic measures only:

```text
original prospectus PDF
-> current PyMuPDFDocumentParser
-> current KeywordDocumentRetriever
-> ranked pages
-> gpt_expert_v1.1 Evidence-page comparison
```

No LLM, Agent, Verifier, Supervisor, Predictor, Human Golden, market outcome or
2025 blind data was used. No production Parser, Retriever, Query Family or Agent
file was changed.

The configured v0.3 offline and AI runtimes both select `retriever: keyword`.
`ComponentRegistry` maps that name to `KeywordDocumentRetriever`. The measured
Retriever is deterministic keyword/query-family scoring; it has no embedding,
vector database, semantic search, learned reranker or LLM retrieval.

## Input provenance

- Case: `ipo_2020_00368`
- Stock: `0368.HK`
- Annotation: `gpt_expert_v1.1`
- Annotation SHA-256:
  `e80444879eca8d38cbf41b20d15c81da09976f580acf2cd2956d28e7d614e0b6`
- Prospectus SHA-256:
  `642a84775c107ebbc4a7534f88b2aba6399410937933d678b223feb342977a82`
- Physical PDF pages: `420`
- Non-blank parser chunks: `418`
- Parser page errors: `0`
- Parser regression against the current 17 Evidence records: `false`

The PDF was resolved from the catalog manifest and hash-verified. No PDF binary,
local absolute path, full prospectus page or Expert exact text is committed.

## Production-query discipline

The audit uses the fixed requests already emitted by the released v0.3 Agents.
It does not use Gold text, Gold pages, issuer names or case-specific terms as
queries. A contract test checks that the evaluation query plan remains identical
to the frozen Financial, Legal and Business Agent requests.

For a single-query risk, `@K` is the ordinary ranked prefix. Financial query
families reproduce the Agent's ordered unique/capped composition, generalized
from its production cap of 5 to each measured K. Cash runway and Business use
the production parallel-query shape; their risk-level `@K` is therefore the
deduplicated union of each fixed query's own Top-K, not a claim that the union
contains only K pages. Per-query rankings and short excerpts remain in ignored
local reports.

## Overall raw metrics

Ground truth contains 17 Evidence records, 13 required records, 13 primary
records and 14 unique physical pages.

| Raw Retriever metric | @1 | @3 | @5 | @10 | @20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Evidence Recall | 11.76% | 17.65% | 35.29% | 35.29% | 41.18% |
| Primary Evidence Recall | 15.38% | 23.08% | 38.46% | 38.46% | 46.15% |
| Required Evidence Recall | 15.38% | 23.08% | 38.46% | 38.46% | 46.15% |
| Unique Gold Page Recall | 14.29% | 21.43% | 42.86% | 42.86% | 42.86% |
| Any-valid Risk Hit Rate | 12.50% | 25.00% | 50.00% | 50.00% | 62.50% |
| Required Evidence Completion Rate | 12.50% | 12.50% | 37.50% | 37.50% | 50.00% |

`supporting_only` records are included in overall/any-valid metrics but excluded
from required denominators. Repeated physical pages, such as page 309 supporting
multiple risks, count once in unique-page metrics and separately at Evidence
record level.

## Risk-level results

| Risk | Required Gold pages | Top-5 retrieved pages | First valid rank | First K with all required | Result / failure |
| --- | --- | --- | ---: | ---: | --- |
| `cash_runway` | 314, 316 | 316, 314, 15, 214, 213, 323, 350 | 1 | 1 | PASS |
| `continuous_loss` | 309 | 352, 351, 242, 309, 17 | 4 | 5 | PASS |
| `revenue_growth` | 309 | 118, 208, 212, 319, 204 | 14 | 20 | PARTIAL — RANKING_MISS / TOPK_CUTOFF |
| `customer_concentration` | 136, 309 | 133, 137, 119, 138, 11 | — | — | FAIL — RETRIEVAL_MISS / QUERY_FAMILY_GAP |
| `supplier_concentration` | 140, 141, 142 | 139, 11, 140, 20, 25 | 3 | — | PARTIAL — pages 141/142 RETRIEVAL_MISS / QUERY_FAMILY_GAP |
| `redemption_rights` | 93, 94 | 367, 376, 381, 260, 268 | — | — | FAIL — RETRIEVAL_MISS / QUERY_FAMILY_GAP |
| `material_litigation_compliance` | 165 | 17, 415, 53, 165, 162 | 4 | 5 | PASS; supporting page 166 misses Top-20 |
| `precommercial_product` | 97 | empty | — | — | FAIL — RETRIEVAL_MISS / EMPTY_RESULT / QUERY_FAMILY_GAP |

Top-20 production-composed pages are:

- `cash_runway`: 316, 314, 15, 214, 213, 323, 350, 355, 242, 217, 16,
  227, 310, 321, 330, 216, 333, 334, 347, 21, 157, 249;
- `continuous_loss`: 352, 351, 242, 309, 17, 16, 14, 209, 313, 13, 193, 198;
- `revenue_growth`: 118, 208, 212, 319, 204, 214, 233, 237, 238, 251,
  13, 198, 335, 309, 314, 321, 324, 327, 337, 412;
- `customer_concentration`: 133, 137, 119, 138, 11, 41, 100, 131, 329,
  23, 75, 134, 172, 335, 401;
- `supplier_concentration`: 139, 11, 140, 20, 25, 101, 156, 401;
- `redemption_rights`: 367, 376, 381, 260, 268;
- `material_litigation_compliance`: 17, 415, 53, 165, 162, 414, 152,
  241, 167, 174, 179, 180, 189, 203, 248, 324, 382, 383, 385, 390;
- `precommercial_product`: empty.

The customer/supplier continuation-table misses remain Retriever misses in this
audit: the earlier Parser audit proved that page text and numbers exist, and
table flattening does not reduce the retrieval denominator. Likewise, the
redemption diagram relationship on page 95 is not required for a page-level hit.

## Failure taxonomy

Evidence-level primary outcomes and diagnostic flags are counted separately:

| Code | Count |
| --- | ---: |
| `NONE` | 6 |
| `RANKING_MISS` | 1 |
| `RETRIEVAL_MISS` | 10 |
| `TOPK_CUTOFF` | 1 |
| `QUERY_FAMILY_GAP` | 10 |
| `EMPTY_RESULT` | 2 |
| `NO_QUERY_EXECUTED` | 0 |
| `PARSER_REGRESSION` | 0 |

`QUERY_FAMILY_GAP` is a post-retrieval diagnostic only: a Top-20 miss receives
the flag when neither the existing production query nor its current family
aliases covers the Gold excerpt's core lexical concept. Gold text never affects
the query or rank.

## Domain view

Required Recall@20 by domain is:

- Financial: 5/9 = 55.56%;
- Legal: 1/3 = 33.33%;
- Business: 0/1 = 0.00%.

This single construction-company case is insufficient for a production domain
benchmark, but the different failure shapes support testing domain-specific
retrieval rather than assuming one shared static query strategy is adequate.

## Research answers and decision

1. **Is the earlier low Evidence recall mainly a Retriever issue?** The current
   Parser preserves every Gold page/core text and has no regression, while raw
   required recall is only 46.15% at 20. The current query/candidate retrieval is
   therefore a major bottleneck. This audit alone does not exclude additional
   downstream Agent or Verifier loss.
2. **Does Top-20 find most Gold Evidence?** No. It finds 6/13 required records
   and 7/17 total records.
3. **Is this mainly ranking?** No. Only one Evidence record is a Top-5 ranking
   miss that appears by Top-20; ten records remain Top-20 retrieval misses.
4. **Which domain is weakest?** Business is weakest on this case, followed by
   Legal, then Financial.
5. **Is domain/Agent-specific retrieval justified?** The result supplies
   directional evidence for it, subject to multi-case confirmation.
6. **What is next?** Required Recall@20 is below the diagnostic 70% boundary, so
   the next approved study should be `QUERY_FAMILY_AND_DOMAIN_RETRIEVAL_DESIGN`,
   not Agent Extraction Audit and not immediate score tuning.

The historical end-to-end Evidence Recall@3 near 18.75% is not directly
comparable: it may mix retrieval, candidate generation and downstream survival.
The isolated raw Retriever Required Recall@3 is 23.08%; this is a decomposition,
not an improvement claim, because the Retriever was not changed.

## Frozen flags

```text
CASE = ipo_2020_00368
ANNOTATION_VERSION = gpt_expert_v1.1
RAW_RETRIEVER_AUDIT_COMPLETED = true
PARSER_USED = true
RETRIEVER_USED = true
LLM_USED = false
AGENT_USED = false
VERIFIER_USED = false
SUPERVISOR_USED = false
HUMAN_GOLDEN_USED = false
MARKET_OUTCOME_USED = false
2025_BLIND_ACCESSED = false
PRODUCTION_PARSER_CHANGED = false
PRODUCTION_RETRIEVER_CHANGED = false
QUERY_FAMILY_CHANGED = false
AGENT_CHANGED = false
VERIFIER_CHANGED = false
SUPERVISOR_CHANGED = false
NEXT_STEP = QUERY_FAMILY_AND_DOMAIN_RETRIEVAL_DESIGN
```

## Reproduction

```powershell
$env:PYTHONPATH = "src"
python scripts/run_raw_retrieval_audit.py `
  --case-id ipo_2020_00368 `
  --annotation <path-to-latest-gpt_expert_v1.1-json> `
  --pdf-root <authorized-prospectus-root>
```

Detailed JSON, CSV, summary and query-ranked short excerpts are generated under
`reports/raw_retrieval/ipo_2020_00368/` and remain ignored runtime artifacts.
