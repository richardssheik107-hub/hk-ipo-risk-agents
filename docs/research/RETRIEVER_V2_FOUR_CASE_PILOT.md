# Retriever V2 Four-Case Pilot

## Decision

`RETRIEVER_V2_BEATS_V1 = false`

The V2 candidate improves deeper retrieval coverage but does not improve the
short ranking that the current product depends on. It therefore remains a
research-only candidate and is **not** registered, configured, or selected as
the production default.

The four-case micro results are:

| Required Evidence Recall | V1 | V2 | Delta |
| --- | ---: | ---: | ---: |
| @1 | 8.51% | 8.51% | 0.00 pp |
| @3 | 31.91% | 27.66% | -4.26 pp |
| @5 | 40.43% | 38.30% | -2.13 pp |
| @10 | 48.94% | 55.32% | +6.38 pp |
| @20 | 57.45% | 63.83% | +6.38 pp |

This is a negative result for the proposed V2 ranking at Top-3/Top-5, not a
failed experiment. It establishes that domain queries, neighbour pages and a
bounded second retrieval round can recover more evidence at deeper K, while
their current fusion weights still displace useful V1 pages near the top.

## Scope and isolation

The executed chain was strictly:

```text
Original prospectus PDF
-> released PyMuPDF parser
-> production KeywordDocumentRetriever (V1)
   or unregistered DomainAwareRetrieverV2 candidate
-> evaluation-only metrics
-> stop
```

No LLM, Agent, Verifier, Supervisor, Predictor, Workflow or Service was called.
No public Retriever Protocol or public Pydantic Schema changed. The existing
`KeywordDocumentRetriever` remains the configured production implementation.

The evaluation-only `ExpertRiskAnnotation.expected_level` nullable fix from
commit `20d1662` was carried into this branch so the preserved 1167.HK
`needs_review` rows validate. It does not alter runtime/public schemas.

## Input provenance

Base branch:

`eval/raw-retriever-audit@9635fc902bb32f7ab8eddc48bdbf485607a7f116`

Expert-result source:

`annotation/gpt-expert-results@74978fcbd7f4e26779e1ac46a4673dea32aff680`

| Set | Case | Stock | Annotation SHA-256 | Parsed non-empty pages | Parser errors |
| --- | --- | --- | --- | ---: | ---: |
| Development | `ipo_2020_00368` | 0368.HK | `e80444879eca8d38cbf41b20d15c81da09976f580acf2cd2956d28e7d614e0b6` | 418 | 0 |
| Development | `ipo_2020_01167` | 1167.HK | `3ffcdc17808fdd3c7e3528d928d6353eb2693b55812c9164d44b67b9aa4f3e29` | 519 | 0 |
| Development | `ipo_2020_01408` | 1408.HK | `170eb64044dca10dbb9e0266ea638f913278b91194e1ee3e74d4b4e03aaf3df1` | 503 | 0 |
| Locked holdout | `ipo_2020_01961` | 1961.HK | `106a8b3cdd74930aaf997c237f8f5f73a9a60571861668a018bece2af8e04178` | 598 | 0 |

The PDFs stayed local and were resolved by catalog filename plus SHA-256. They
are not part of the branch. Physical PDF page 471 of 1961.HK was also rendered
and visually checked: it is the accountants-report consolidated cash-flow
statement, matching the annotation's physical-page semantics.

The four annotations contain 61 Evidence rows: 47 required and 37 primary.
These are external GPT expert first-pass annotations, not formal human Golden.

## Holdout discipline

1961.HK was designated before implementation as the only pilot holdout.

Before its annotation content was inspected, the development run wrote a
freeze manifest with:

```text
candidate source SHA-256:
4ff86be134ec88de2d62be5d381c9d7a8f45d689cd748a0cd0ed279430fcebe0

query plan SHA-256:
5f7dcdf37a7e1670f98f023f7746614641d3e56e025bb081f597fe971887e4ce

holdout_gold_opened = false
blind_2025_accessed = false
```

The holdout command verified both hashes before loading 1961.HK. No V2 source
or query-plan change occurred after reveal. 2025 blind data was not accessed.

## Metric semantics

All `Recall@K` values use one global ranking per risk:

1. execute the frozen risk queries;
2. construct one deterministic composed/global ranking;
3. deduplicate physical pages;
4. truncate that global ranking to K;
5. compare against Gold.

The evaluator never treats the union of each query's individual Top-K as a
single global Top-K. A regression contract explicitly protects this rule.

Metrics reported separately are:

- all Evidence Recall@1/3/5/10/20;
- primary Evidence Recall@1/3/5/10/20;
- required Evidence Recall@1/3/5/10/20;
- unique physical Gold-page Recall@1/3/5/10/20;
- any-valid-Evidence risk hit rate;
- all-required-Evidence completion rate;
- first valid hit rank and first complete K;
- micro, macro-case, domain, risk and source-authority slices.

## Aggregate A/B results

### Four-case micro metrics

| Metric | Version | @1 | @3 | @5 | @10 | @20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Evidence recall | V1 | 9.84% | 32.79% | 40.98% | 50.82% | 57.38% |
| Evidence recall | V2 | 9.84% | 27.87% | 37.70% | 54.10% | 63.93% |
| Primary recall | V1 | 2.70% | 24.32% | 35.14% | 43.24% | 51.35% |
| Primary recall | V2 | 2.70% | 18.92% | 32.43% | 51.35% | 59.46% |
| Required recall | V1 | 8.51% | 31.91% | 40.43% | 48.94% | 57.45% |
| Required recall | V2 | 8.51% | 27.66% | 38.30% | 55.32% | 63.83% |
| Unique-page recall | V1 | 8.33% | 35.42% | 45.83% | 58.33% | 62.50% |
| Unique-page recall | V2 | 8.33% | 29.17% | 41.67% | 62.50% | 66.67% |
| Any-valid risk hit | V1 | 12.50% | 37.50% | 46.88% | 59.38% | 65.62% |
| Any-valid risk hit | V2 | 12.50% | 31.25% | 43.75% | 59.38% | 71.88% |
| Required completion | V1 | 0.00% | 21.88% | 34.38% | 43.75% | 53.12% |
| Required completion | V2 | 0.00% | 18.75% | 31.25% | 46.88% | 56.25% |

### Development versus holdout

| Slice | Metric | V1 @3 | V2 @3 | V1 @5 | V2 @5 | V1 @20 | V2 @20 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3-case development | Required recall | 32.43% | 29.73% | 43.24% | 40.54% | 64.86% | 72.97% |
| 3-case development | Required completion | 20.83% | 20.83% | 37.50% | 33.33% | 62.50% | 66.67% |
| 1961 holdout | Required recall | 30.00% | 20.00% | 30.00% | 30.00% | 30.00% | 30.00% |
| 1961 holdout | Required completion | 25.00% | 12.50% | 25.00% | 25.00% | 25.00% | 25.00% |

The holdout does not support promotion: V2 loses one required hit at Top-3 and
only catches up at Top-5. Its deeper recall is unchanged on this one case.

### Required recall by domain

| Domain | V1 @3 | V2 @3 | V1 @5 | V2 @5 | V1 @20 | V2 @20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Financial | 42.42% | 36.36% | 48.48% | 48.48% | 60.61% | 72.73% |
| Legal | 11.11% | 11.11% | 33.33% | 22.22% | 55.56% | 55.56% |
| Business | 0.00% | 0.00% | 0.00% | 0.00% | 40.00% | 20.00% |

The observed deep-recall gain is Financial-only. Legal does not improve and
Business regresses. A single shared fusion policy is therefore not justified.

### Required recall by risk

Values are `@3 / @5 / @20`.

| Risk | V1 | V2 |
| --- | --- | --- |
| cash_runway | 100.00% / 100.00% / 100.00% | 100.00% / 100.00% / 100.00% |
| continuous_loss | 0.00% / 50.00% / 50.00% | 0.00% / 25.00% / 50.00% |
| revenue_growth | 0.00% / 0.00% / 75.00% | 0.00% / 0.00% / 75.00% |
| customer_concentration | 28.57% / 28.57% / 42.86% | 14.29% / 42.86% / 85.71% |
| supplier_concentration | 40.00% / 40.00% / 40.00% | 30.00% / 40.00% / 50.00% |
| redemption_rights | 0.00% / 20.00% / 40.00% | 0.00% / 20.00% / 40.00% |
| material_litigation_compliance | 25.00% / 50.00% / 75.00% | 25.00% / 25.00% / 75.00% |
| precommercial_product | 0.00% / 0.00% / 40.00% | 0.00% / 0.00% / 20.00% |

Customer-concentration completeness benefits from supplemental financial-table
queries and neighbour evidence. That gain is not shared by Legal or Business.

## Source-authority result

Counts below are `Gold rows / hits@3 / hits@5 / hits@20`.

| Source authority | V1 | V2 |
| --- | --- | --- |
| accountants_report | 22 / 10 / 12 / 15 | 22 / 9 / 11 / 16 |
| business_section | 18 / 7 / 7 / 9 | 18 / 6 / 7 / 10 |
| corporate_structure | 3 / 0 / 0 / 0 | 3 / 0 / 0 / 0 |
| financial_information | 6 / 0 / 0 / 2 | 6 / 0 / 1 / 3 |
| legal_disclosure | 8 / 2 / 4 / 6 | 8 / 1 / 2 / 7 |
| pre_ipo_investment | 4 / 1 / 2 / 3 | 4 / 1 / 2 / 3 |

The candidate improves deeper financial-information and legal-disclosure
coverage but harms their early ranks. Corporate-structure evidence remains a
complete gap and needs a genuinely separate Legal search strategy.

## Failure taxonomy

The evaluator records a primary failure plus non-exclusive secondary flags.

| Failure/flag | V1 | V2 |
| --- | ---: | ---: |
| NONE | 25 | 23 |
| RANKING_MISS | 10 | 16 |
| RETRIEVAL_MISS | 26 | 22 |
| TOPK_CUTOFF | 10 | 16 |
| QUERY_FAMILY_GAP | 23 | 18 |
| EMPTY_RESULT | 2 | 0 |
| QUERY_TOO_NARROW | 2 | 0 |
| QUERY_TOO_BROAD | 23 | 33 |
| DUPLICATE_PAGE | 20 | 27 |
| NEIGHBOUR_PAGE_MISSING | 8 | 7 |
| WRONG_SOURCE_AUTHORITY | 0 | 0 |
| PARSER_REGRESSION | 0 | 0 |
| NO_QUERY_EXECUTED | 0 | 0 |

V2 closes some empty/narrow/family-gap failures but creates more broad-query,
duplicate-page and ranking-cutoff pressure. That is the main reason deeper
recall rises while Top-3/Top-5 does not.

## V2 candidate design

The unregistered candidate uses:

- fixed risk/domain query plans in Simplified Chinese, Traditional Chinese and English;
- released `KeywordDocumentRetriever` as the only lexical backend;
- one deterministic global ranking per risk;
- weighted global rank fusion that preserves sequential versus parallel query semantics;
- physical neighbour expansion limited by risk plan;
- at most one fixed completeness-driven second round;
- stable Evidence IDs and metadata with risk, domain, matched queries, query rounds,
  seed pages, neighbour flag, missing signal groups and query-plan hash.

It does not use embeddings, a vector database, BM25 packages, OCR, LLMs,
issuer-specific aliases, stock codes, document IDs, known pages or Evidence IDs.

## Quality gates and limitations

- Production default changed: **No**.
- Public interface changed: **No**.
- Parser changed: **No**.
- Agent/Verifier/Workflow/Service changed: **No**.
- 2025 blind accessed: **No**.
- PDFs committed: **No**.
- Holdout altered after reveal: **No**.

Validation completed on the frozen candidate:

- Retriever/evaluation contracts: **47 passed**.
- Full suite with repository-default settings: **971 passed**.
- `validate_project.py`: **passed** (`completed`, `verified=3`, `pending=1`).
- `validate_competition_data.py`: **passed**.
- `compileall app src scripts`: **passed**.
- All four preserved annotation bundles: **valid**.
- `git diff --check`: **passed**.

The first full-suite invocation inherited local `IPO_RISK_*` overrides for an
external LLM provider that is absent from this older evaluation baseline and
therefore produced 15 configuration failures. No repository file was changed
to hide them. The suite was rerun in a child process with those external
overrides removed, which exercises the repository-default configuration and
produced the 971-pass result above.

Limitations:

1. Only four 2020 prospectuses and one holdout are included.
2. The reference set is GPT expert first-pass, not formal human Golden.
3. The pilot is too small for statistical significance.
4. Physical-page recall does not measure excerpt-level semantic correctness.
5. `WRONG_SOURCE_AUTHORITY` remains zero because the current parser/retriever
   metadata does not provide a sufficiently reliable authority classifier;
   the separate authority slice is reported instead of inventing this flag.
6. V2 is slower than V1 because it executes multiple deterministic queries and
   one optional second round.

## Recommendation

Do not replace V1.

The next research iteration should split ranking policies by domain rather than
tuning one shared fusion rule:

1. keep the released V1 ranking as a short-K safety baseline;
2. test Financial supplemental evidence as a second-stage completeness pool;
3. design explicit Legal corporate-structure/lifecycle retrieval;
4. redesign Business positive and negative-fact retrieval before adding more
   neighbour expansion;
5. evaluate on more locked holdouts before any production registration.
