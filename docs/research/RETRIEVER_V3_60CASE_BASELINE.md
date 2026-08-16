# Retriever V3 — 60-Case Gold-Driven Baseline

## Status

`PHASE = R3-A1`

This phase builds the evaluation and data-governance foundation for a future
high-recall Stage-1 Retriever. It deliberately **does not** change the production
Retriever, Parser, Agent, Verifier, Supervisor, Predictor, public Schema, or LLM
runtime.

The immediate research question is:

> Across the 60 audited Expert Annotation cases, how much Required Evidence is
> already covered by V1, V2 and V2.1, how complementary are their candidate
> universes, and which failure types should determine the next recall lane?

The 10-case Revision-4 LLM experiment already established positive semantic
reranking value, while Stage-1 Required Recall@20 remained the ceiling. R3-A1
therefore optimizes **measurement of candidate coverage before any new ranking
rule is tuned**.

## 1. Frozen 60-case split

Source scope:

- `expert_golden_100_v1`
- task indices `1..60`
- 2020: 20 cases
- 2021: 20 cases
- 2022: 20 cases

Frozen split:

- development: **50 cases**
- locked implementation validation: **10 cases**

The ten cases previously used in the V1/V2/V2.1/LLM retrieval experiments remain
in development. Cases manually discussed during the recent annotation-quality
audit are also excluded from the locked set.

The locked set is selected by a deterministic case-ID hash within fixed year
quotas:

- 2020: 3
- 2021: 3
- 2022: 4

Authoritative manifest:

`configs/retriever_v3_split_manifest.json`

### Important lock semantics

This is **not claimed to be cryptographically blind** because the Expert
annotation files already exist in the repository. The lock is an engineering and
research-governance control:

- default full Retriever evaluation runs development only;
- locked metrics require `--unlock-locked`;
- preflight exports no locked Evidence text;
- the locked set must not be used to tune query terms, weights, hard guards,
  microchunk parameters, BM25 settings, dense-model choices, or LTR features.

Results from the locked set should therefore be described as **locked
implementation validation**, not as a never-observed external blind test.

## 2. Audited Retrieval Gold contract

`src/ipo_risk/evaluation/retriever_v3_dataset.py` builds retrieval supervision
from:

1. immutable `expert_results/<case>/pass1/expert_annotation_v1.json` Evidence;
2. `audit/deterministic_corrections_v1.json` for corrected financial risk-state
   metadata where present;
3. `audit/financial_resolution_v1.json` for final Phase-2c financial review-state
   metadata where present.

The audit overlays do **not** rewrite Evidence page or exact text.

Each normalized Evidence row contains:

- `case_id`
- `stock_code`
- `document_id`
- `risk_code`
- physical `page`
- `exact_text`
- `evidence_role`
- `requirement`
- `source_authority`
- confidence
- retrieval split
- audited risk state
- state provenance
- a stable `row_id`

Initial ranking grade:

- grade 3: `required + primary`
- grade 2: other `required`
- grade 1: `alternative` or `supporting_only`

These grades are future LTR supervision metadata. R3-A1 does not train a model.

## 3. Existing Retriever inventory

### V1 — `KeywordDocumentRetriever`

Primary features already available:

- normalized exact-query match
- multilingual aliases
- query-family context
- preferred/discouraged section text signals
- financial-table heuristic
- structured-table-row signal when available
- audited-statement neighborhood for cash-flow evidence
- summary/note/negative-context demotion
- deterministic relevance score
- stable page/chunk provenance

V1 remains the production deterministic baseline.

### V2 — `DomainAwareRetrieverV2`

Adds:

- risk-specific multi-query plans
- sequential or parallel composition
- candidate-depth expansion
- physical-neighbor expansion
- completeness checks
- one second-round retrieval pass
- deterministic fusion provenance

The 10-case research result showed deeper candidate coverage in some domains but
weaker head ranking than V1.

### V2.1 — `DomainAwareRetrieverV21`

Adds:

- query-family identities
- query specificity tiers
- family-capped reciprocal-rank fusion
- V1 head anchors
- Legal boilerplate demotion
- Business V1-head fallback
- neighbor/round-2 head guards
- candidate-universe diagnostics

V2.1 is still research-only.

### Stage-2 LLM reranker

The frozen 10-case Revision-4 experiment showed positive incremental semantic
ordering over the Stage-1 union, but could not improve evidence that never
entered the candidate pool. It remains a downstream reranker candidate, not the
focus of R3-A1.

## 4. What R3-A1 measures

For each of the 50 development cases and all eight risks, the full run saves up to
100 pages from each existing variant:

- V1
- V2
- V2.1

Metrics:

- Required Evidence Recall@1/3/5/10/20/50/100
- Required unique-page Recall@K
- Required Completion@K
- MRR
- per-risk metrics

Complementarity is measured without inventing a new production ordering:

- V1 ∪ V2 candidate coverage at equal source depth
- V1 ∪ V2 ∪ V2.1 candidate coverage at equal source depth
- V1-only unique Gold
- V2-only unique Gold
- V2.1-only unique Gold
- V2 marginal gain over V1
- V2.1 marginal gain over V1∪V2

A `union@source_depth=50` value is a **candidate coverage ceiling**, not
`Recall@50` of a newly ranked Retriever.

## 5. Failure taxonomy

Every Required Gold page receives a post-freeze diagnostic.

Primary class:

- `NONE`
- `RANKING_ONLY_MISS`: present within an existing variant Top100 but outside all
  variant Top20s
- `QUERY_COVERAGE_MISS`: absent from all three Top100 candidate sets

Secondary diagnostics may include:

- `PARSER_PAGE_MISSING`
- `PARSER_TEXT_MISMATCH`
- `TABLE_FRAGMENTATION`
- `NEIGHBOR_PAGE_MISS`
- `LEXICAL_VARIATION`
- `SOURCE_AUTHORITY_HEURISTIC_MISS`
- `BOILERPLATE_DISPLACEMENT`

Gold exact text is used only **after candidate ranking is frozen** for diagnostic
classification. It never changes candidate generation or ranking.

## 6. Hard-negative dataset

For later Learning-to-Rank work, R3-A1 exports highly ranked pages that are not
Gold for the current `case × risk`.

Each hard negative stores:

- case/risk
- retriever variant
- candidate rank
- physical page
- deterministic score
- generic authority hint
- negative tier (`top5`, `top20`, `top50`)
- bounded evidence excerpt

These rows are future training candidates, not automatically adjudicated
semantic negatives. A non-Gold page can still contain useful evidence not selected
by the expert, so later LTR work should distinguish sampled hard negatives from
formal human-negative judgments.

## 7. Evidence-pattern mining

Preflight can run without prospectus PDFs and summarizes development Gold by:

- risk
- source authority
- evidence role
- requirement
- percentage signal
- currency signal
- numeric density
- year density
- table-like signal
- exact-text length

This report is used to decide which **new recall lane** deserves implementation.
It must not be converted into issuer/page-specific production rules.

## 8. Candidate freeze firewall

The full ranking command follows this order:

```text
split manifest + source catalog
        ↓
exact PDF SHA-256 resolution
        ↓
Parser
        ↓
V1 / V2 / V2.1 Top100
        ↓
candidate ranking SHA-256 freeze
        ↓
only now load Expert Evidence Gold
        ↓
evaluate / diagnose
```

This ensures Gold is not read by the ranking path.

## 9. Commands

Repository-only preflight:

```bash
python scripts/run_retriever_v3_baseline.py preflight
```

Development full run when the original 50 PDFs are available locally:

```bash
python scripts/run_retriever_v3_baseline.py run \
  --split development \
  --pdf-root /path/to/prospectuses
```

Locked implementation validation after the Retriever V3 design is frozen:

```bash
python scripts/run_retriever_v3_baseline.py run \
  --split locked_validation \
  --unlock-locked \
  --pdf-root /path/to/prospectuses
```

PDFs are matched to cases by the frozen catalog SHA-256, not by a guessed
filename.

## 10. Output contract

Preflight:

```text
reports/retriever_v3/preflight/
  gold_dataset_manifest.json
  development_gold_evidence.csv
  development_evidence_patterns.json
  locked_validation_manifest.json
```

Full development/locked run:

```text
reports/retriever_v3/<split>/
  candidate_freeze_manifest.json
  run_manifest.json
  metrics.json
  per_risk_metrics.csv
  unique_coverage.json
  failure_taxonomy.csv
  hard_negatives.jsonl
  candidate_rankings.jsonl
  evidence_patterns.json
  summary.md
```

Detailed reports remain research artifacts and are not production runtime input.

## 11. Decision gates for the next phase

Do not add BM25, microchunks, dense retrieval or LTR merely because they are
available.

Use R3-A1 results to choose the next intervention.

### Candidate-generation gate

Primary target:

`V1 ∪ V2 ∪ V2.1 Required-page coverage at source depth 50`

Interpretation:

- high coverage but low Top20 recall → ranking/LTR problem;
- low coverage with lexical-variation misses → sparse/BM25 and possibly dense lane;
- low coverage with table fragmentation → table/microchunk lane;
- authority displacement → authority/section lane;
- neighbor misses → microchunk/neighbor strategy.

A working development target for the next stage is **≥85% Required candidate
coverage at a practical candidate budget**. This is a development target, not a
claimed result.

### LTR gate

Only train a lightweight ranker after candidate coverage is high enough that
ranking, rather than retrieval coverage, is the dominant error.

Likely future features include:

- V1/V2/V2.1 ranks and scores
- exact/alias hits
- query-family multiplicity
- family RRF
- specificity tier
- V1 head anchor
- neighbor/round-2 provenance
- table/numeric signals
- predicted source authority
- boilerplate signals
- later BM25/dense scores

Company must be the grouping unit for cross-validation; risks from the same IPO
must never be split between train and validation folds.

## 12. Scope and safety

R3-A1 changes:

- evaluation code
- research script
- frozen split config
- tests
- CI preflight
- research documentation

R3-A1 does not change:

- production `KeywordDocumentRetriever`
- V2/V2.1 research implementations
- query-family vocabulary
- Parser
- public Schema
- Agent
- Verifier
- Supervisor
- Predictor
- Workflow/Service
- LLM prompts/provider
- market model
- pass1 Expert annotations
- Phase-2c audit overlays

No new dependency is introduced.
