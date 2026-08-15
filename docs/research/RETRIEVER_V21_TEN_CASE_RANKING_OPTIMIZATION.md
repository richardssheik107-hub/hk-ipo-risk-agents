# Retriever V2.1 Ten-Case Ranking Optimization

## Status

```text
RETRIEVER_V21_BEATS_V1_TEN_CASE = false
V2.1 registration = not performed
production default = unchanged
2025 blind = not accessed
```

This was an evaluation-only `PDF -> Parser -> Retriever -> Evidence -> STOP`
experiment. No Agent, LLM, Verifier, Supervisor, Predictor, Workflow, Service,
ReportGenerator or UI component was executed or changed.

## Provenance and splits

- Product baseline: `main@532ece133ff770cebd174abd64c15efda38989e4`
- Expert-annotation source: `annotation/gpt-expert-results@4ba86a4ebbb3033b6c9966d07f5351afa18dc206`
- Development: `00368`, `01167`, `01408`
- Historical regression: `01961`
- Locked implementation validation: `01942`, `02057`, `02135`, `02263`, `02599`, `00013`
- Formal annotations: 10 cases, 143 Evidence objects, 116 required Evidence objects
- PDFs: 10 original prospectuses; hashes and page counts matched the catalog

The released PR #45 four-case baseline was reproduced exactly before V2.1
work began:

| Candidate | Required@1 | @3 | @5 | @10 | @20 |
|---|---:|---:|---:|---:|---:|
| V1 | 8.51% | 31.91% | 40.43% | 48.94% | 57.45% |
| V2 | 8.51% | 27.66% | 38.30% | 55.32% | 63.83% |

## Diagnosis and ablation

The three-case development ablation isolated the source of the V2 trade-off.

| Variant | Required@1 | @3 | @5 | @10 | @20 | Completion@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | 8.11% | 32.43% | 43.24% | 54.05% | 64.86% | 37.50% | 0.2362 |
| V2 direct only | 10.81% | 35.14% | 43.24% | 51.35% | 59.46% | 37.50% | 0.2578 |
| V2 direct/current fusion | 10.81% | 35.14% | 43.24% | 51.35% | 59.46% | 37.50% | 0.2578 |
| V2 + neighbour | 10.81% | 35.14% | 43.24% | 51.35% | 59.46% | 37.50% | 0.2578 |
| Full V2 | 8.11% | 29.73% | 40.54% | 62.16% | 72.97% | 33.33% | 0.2402 |
| Direct family-RRF | 2.70% | 27.03% | 43.24% | 48.65% | 59.46% | 37.50% | 0.1917 |
| V2.1 | 2.70% | 35.14% | 54.05% | 56.76% | 70.27% | 54.17% | 0.2264 |

The evidence supports a ranking-dilution diagnosis: V2's second-round and
multi-query candidates improved the tail while displacing useful direct/V1
head candidates. Family-capping alone was insufficient; lexicographic head
guards were the material intervention. No query expansion was used.

## V2.1 design

- Family-capped reciprocal-rank fusion with `K=60`.
- Static issuer-independent `HIGH / MEDIUM / BROAD` specificity.
- Lexicographic tiers before RRF score.
- V1 head anchor, including a stronger Business anchor.
- Neighbour-only pages excluded from Top 3 and capped at one Top-5 slot.
- Completeness-round-only pages kept in the tail unless they carry a
  high-specificity direct signal.
- Legal boilerplate deterministically demoted unless transaction or current-
  status context overrides it.
- Candidate universe contains the V1 Top 20 and V2.1 direct candidates.
- Stable page/chunk tie-breaking and complete query/family provenance.

The implementation is deliberately absent from `ComponentRegistry`.

## Freeze

The development policy was frozen without a corrective iteration:

```text
generic_development_correction_count = 0
query_changed_from_v2 = false
freeze_manifest_sha256 = ff92d4ccaca11ee6480e1bd1fc504c3eba4b3d0e7817a2812f5aa4ffb4317886
v21_source_sha256 = e7c1214feb398b9e0e8263b5b598b1ce6288a2d1b0e3c7851ec522fbcd11412e
ranking_policy_sha256 = 09e33593a711b9d6103bc375852de5701b8fcede4160e3cc8f559dbc314964d3
```

After the freeze, V1, V2, V2.1, the query-family mapping, specificity policy
and ranking policy were not changed.

## Split results

### Historical regression — 01961

| Candidate | Required@1 | @3 | @5 | @10 | @20 | Completion@5 |
|---|---:|---:|---:|---:|---:|---:|
| V1 | 10.00% | 30.00% | 30.00% | 30.00% | 30.00% | 25.00% |
| V2 | 10.00% | 20.00% | 30.00% | 30.00% | 30.00% | 25.00% |
| V2.1 | 0.00% | 20.00% | 30.00% | 30.00% | 30.00% | 25.00% |

Historical Required@3 failed the non-regression gate.

### Six-case locked implementation validation

| Candidate | Required@1 | @3 | @5 | @10 | @20 | Completion@5 |
|---|---:|---:|---:|---:|---:|---:|
| V1 | 18.84% | 36.23% | 42.03% | 50.72% | 56.52% | 37.50% |
| V2 | 18.84% | 33.33% | 37.68% | 47.83% | 56.52% | 33.33% |
| V2.1 | 18.84% | 31.88% | 43.48% | 50.72% | 56.52% | 43.75% |

V2.1 improved Required@5 and Completion@5, but Required@3 regressed.

### All ten cases

| Candidate | Required@1 | @3 | @5 | @10 | @20 | Completion@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | 14.66% | 34.48% | 41.38% | 50.00% | 56.90% | 36.25% | 0.2669 |
| V2 | 14.66% | 31.03% | 37.93% | 50.86% | 59.48% | 32.50% | 0.2616 |
| V2.1 | 12.07% | 31.90% | 45.69% | 50.86% | 58.62% | 45.00% | 0.2495 |

## Domain and risk breakdown

Required Recall by domain:

| Domain / candidate | @3 | @5 | @20 |
|---|---:|---:|---:|
| Financial V1 | 47.95% | 53.42% | 65.75% |
| Financial V2.1 | 39.73% | 54.79% | 64.38% |
| Legal V1 | 16.67% | 30.00% | 53.33% |
| Legal V2.1 | 23.33% | 36.67% | 53.33% |
| Business V1 | 0.00% | 0.00% | 15.38% |
| Business V2.1 | 7.69% | 15.38% | 38.46% |

V2.1 Required@5 / @20 by risk:

| Risk | Required count | @5 | @20 |
|---|---:|---:|---:|
| cash_runway | 20 | 80.00% | 95.00% |
| continuous_loss | 11 | 45.45% | 45.45% |
| revenue_growth | 11 | 18.18% | 27.27% |
| customer_concentration | 15 | 46.67% | 66.67% |
| supplier_concentration | 16 | 62.50% | 62.50% |
| redemption_rights | 16 | 31.25% | 37.50% |
| material_litigation_compliance | 14 | 42.86% | 71.43% |
| precommercial_product | 13 | 15.38% | 38.46% |

## Source-authority breakdown

V2.1 Required@5 / @20:

| Source authority | Count | @5 | @20 |
|---|---:|---:|---:|
| accountants_report | 45 | 51.11% | 62.22% |
| audited_financial_statement | 7 | 28.57% | 28.57% |
| business_section | 30 | 56.67% | 70.00% |
| corporate_structure | 5 | 0.00% | 0.00% |
| financial_information | 5 | 20.00% | 40.00% |
| legal_disclosure | 16 | 37.50% | 62.50% |
| pre_ipo_investment | 8 | 50.00% | 62.50% |

## Head recovery and regressions

V2.1 recovered all five observed V1-Top-5/V2-displaced required Evidence
records back into Top 5. However, three new locked-set head regressions were
observed:

| Case | Risk | Gold page | V1 rank | V2 rank | V2.1 rank |
|---|---|---:|---:|---:|---:|
| 02263 | customer_concentration | 165 | 3 | 5 | 6 |
| 02599 | cash_runway | 610 | 2 | 2 | 6 |
| 02599 | cash_runway | 612 | 3 | 3 | 7 |

## Deep-gain retention

Across all ten cases, five required Evidence records were V2 tail gains over
V1; V2.1 retained two at Top 20 (40%). On development alone this was 2/4
(50%). These are very small discrete samples, but the result is materially
below the 90% target and is reported as a limitation rather than tuned away.

## Ranking provenance

- Candidate-universe regressions: `0`.
- Top-3 occupancy: direct 208, round-2 23, boilerplate 4, neighbour 4.
- Top-5 occupancy: direct 323, round-2 46, boilerplate 10, neighbour 14.
- Mean query multiplicity: 1.938.
- Mean query-family multiplicity: 1.027.

The low family multiplicity confirms that the family cap removed most
same-family synonym stacking. Legal boilerplate occupied 10 all-case Top-5
slots; because the V1 audit does not expose an equivalent provenance flag, a
strict like-for-like occupancy delta is not available.

## Success gate

| Gate | Result |
|---|---|
| Development Required@3/@5/@20 >= V1 | PASS |
| V2 deep-gain retention >=90%, or explain tiny-sample discreteness | FAIL (40%; small sample disclosed) |
| 01961 Required@3 >= V1 | FAIL |
| 01961 Required@5 >= V1 | PASS |
| Locked Required@3 >= V1 | FAIL |
| Locked Required@5 >= V1 | PASS |
| Locked Completion@5 >= V1 | PASS |
| All-10 Legal Required@5 >= V1 | PASS |
| Legal boilerplate Top-5 not clearly worse | INCONCLUSIVE; no equivalent V1 flag |
| All-10 Business Required@20 >= V1 | PASS |
| No candidate-universe regression | PASS |
| Production default unchanged | PASS |
| Safety/regression tests | see validation section |
| 2025 blind not accessed | PASS |

Therefore:

```text
RETRIEVER_V21_BEATS_V1_TEN_CASE = false
```

## Procedural isolation limitation

Before ranking-policy freeze, the six locked annotation files were imported
and parsed for schema, identity, evidence-count and page-range integrity. Their
content was not used for query expansion, policy selection or ranking changes,
and the frozen implementation was unchanged after the formal locked run.
Nevertheless, this earlier integrity inspection means the run does not meet
the strictest interpretation of “locked Gold never opened before freeze.” The
six-case numbers are therefore labelled **locked implementation validation**,
not a fully blind research estimate. A future experiment needs a separate
custodian/process that withholds the annotation contents until after freeze.

## Recommendation

Do not register or promote V2.1. A V2.2 study should focus on head calibration
for financial multi-page evidence, especially cash-runway and concentration,
while preserving the observed Legal and Business improvements. It must use a
new, genuinely withheld validation split and should include a comparable
boilerplate provenance baseline for V1.

## Validation

- V2.1 targeted tests: `14 passed`.
- Full suite with project LLM overrides cleared: `985 passed`.
- The first full-suite invocation inherited a workstation-level
  `IPO_RISK_CONFIG` / LLM-provider override and produced 15 unrelated
  configuration failures (`970 passed`). Re-running in the repository default
  environment passed completely; no repository config was changed.
- `python scripts/validate_project.py`: passed (`completed`, 3 verified,
  1 pending).
- `python scripts/validate_competition_data.py`: passed.
- `python -m compileall -q app src scripts`: passed.
- `git diff --check`: passed.
- Candidate is not registered and the production registry is unchanged.
- No PDF, ZIP, cache, binary, credential or local absolute path is included in
  the committed diff.

## Artifacts

Committed research artifacts are limited to implementation, evaluator,
runner, tests, this report, and the six formal annotation inputs already
present on the annotation branch. Detailed raw audits and the freeze manifest
remain under ignored `reports/retriever_v21_ten_case/`.
