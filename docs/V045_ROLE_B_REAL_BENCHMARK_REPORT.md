# ROLE B — OFFLINE GOVERNED DEVELOPMENT BENCHMARK:

## FAIL

The governed input/runtime Gate passed: all ten allowlisted Development PDFs were
streamed one at a time from the nested source ZIP, matched the frozen catalog
SHA-256, size and physical-page count, and completed the non-mock offline Document
pipeline. The measured Risk/Evidence performance Gate failed.

```text
PDFs requested:                 10
PDFs located:                   10
SHA verified:                   10
Page counts verified:           10
Cases analyzed:                 10
Cases evaluated:                10
Offline governed cases:         10
Real LLM cases:                  0

Risk Precision:              0.0%
Risk Recall:                 0.0%
Risk F1:                     0.0%

Evidence Recall@1:          20.0%
Evidence Recall@3:          20.0%
Evidence Recall@5:          20.0%
Evidence Precision@5:       NOT AVAILABLE
Physical-page correctness: 100.0%

Evidence out-of-scope:          0
Schema-invalid LLM results:     0
Needs Review:                   0
Verifier rejected:              0
Extraction failed:              0
Provider unavailable/offline:  10

Risk target >=80%:           FAIL
Evidence target >=85%:       FAIL

2024 Validation opened:       NO
2025 Blind accessed:          NO
API key accessed:             NO
Network model calls:           0
Evidence egress:                0
```

## 1. Governed streaming run

The source was the existing 6.7 GB competition ZIP beside the repository. It was
not copied or expanded. The runner processed years in the frozen order
2021 smoke → 2020 → 2022 → 2023. At any moment the task staged no more than:

```text
D:/Multi-Project/.tmp_role_b_offline_benchmark/current_year.zip
D:/Multi-Project/.tmp_role_b_offline_benchmark/current.pdf
```

The outer ZIP was opened only to stream the exact annual member. Each annual ZIP
was then opened to locate the exact catalog filename; fuzzy matching was not used.
ZIP traversal and duplicate paths are rejected. The annual ZIP was deleted after
the year and `current.pdf` after every case. The temporary directory is clean.

All PDF identities came exclusively from
`data/catalog/ipo_prospectus_manifest.csv`. All ten matched filename, byte size,
SHA-256, stock/case identity and one-based physical PDF page count. No 2024/2025
member was extracted or read.

## 2. Prediction/Gold isolation

Prediction generation read only the allowlist, catalog, frozen configuration and
current PDF. The streaming runner has no Golden or expert-annotation input. It
forced these settings without loading environment-variable secrets:

```text
runtime_mode = offline
use_mock = false
parser = pymupdf
retriever = keyword
legal_agent = v03
business_agent = v03
verifier = specialized_v03
llm_provider = unavailable
market_data_provider = unavailable
market_context = none
final_supervisor = none
```

The in-memory production result retained required Evidence text only while the
pipeline executed. The persisted JSONL is a compact projection with identifiers,
pages, ranks, calculation references and component identities; it contains no
Evidence/page text, chunks, prompt or response. Predictions were frozen before
the evaluator opened the formal Human Golden.

```text
OFFLINE GOVERNED BENCHMARK != REAL LLM BENCHMARK
```

## 3. Benchmark metrics

The evaluator reused the frozen `golden_eval.py` semantics. Non-annotated
predictions remained `UNJUDGED`; they were not converted to false positives.
Evidence Precision@5 remains unavailable because the Golden does not exhaustively
judge every predicted page.

| Risk | Golden cases | Risk Precision | Risk Recall | Risk F1 | Evidence Recall@5 |
|---|---:|---:|---:|---:|---:|
| `redemption_rights` | 4 | 0.0% | 0.0% | 0.0% | 0.0% |
| `material_litigation_compliance` | 4 | 0.0% | 0.0% | 0.0% | 0.0% |
| `precommercial_product` | 2 | 0.0% | 0.0% | 0.0% | 50.0% |

The offline provider produced one Role-B RiskItem across the ten cases:
`ipo_2020_01167/precommercial_product`, with nine bounded Evidence references.
The frozen Human Golden expects `needs_review`, while the offline Verifier placed
the item in `verified`; it therefore does not count as a correct verified-risk
prediction. Nine cases produced no Role-B RiskItem. This is a measured baseline,
not an extraction failure or an invented “no-risk” label.

All three risks tie at 0 Risk F1. On Evidence, `redemption_rights` and
`material_litigation_compliance` are weakest at Recall@5 = 0; Business reaches
50% for its two applicable page judgments. No tuning was performed after viewing
these results.

## 4. `ipo_2020_01167` governance

The case is evaluable because its formal Human-Golden rows satisfy the frozen
evaluator policy. Its supplementary expert annotation remains separately invalid:
the existing receipt has `valid: false` for three unsupported `expected_level`
values. The packet was not repaired, guessed, or supplied to prediction. Owner:
A — Pipeline/data governance; B can re-audit a corrected supplementary packet.

## 5. Required answers

1. **Were all ten PDFs found?** YES, in the exact 2020–2023 nested annual ZIPs.
2. **Did all pass SHA and page validation?** YES, 10/10 for byte size, SHA-256
   and catalog physical-page count.
3. **Which cases failed parsing/analysis?** None; 10/10 completed and cleaned.
4. **Offline metrics:** Risk Precision/Recall/F1 = 0%; Evidence Recall@5 = 20%;
   physical-page correctness = 100%; Evidence Precision@5 is not available.
5. **Weakest risk:** all three tie at Risk F1 = 0; Legal redemption and litigation
   are weakest on Evidence Recall@5 at 0.
6. **Is 1167 evaluable?** YES using the valid formal Human Golden. Its invalid
   supplementary annotation remains quarantined.
7. **Were 80% / 85% reached?** NO; both targets failed.
8. **Why is this not a real-LLM benchmark?** The provider was deliberately
   unavailable, so real LLM calls, Evidence egress and network model calls were 0.
9. **Is external-LLM authorization the only remaining step?** It is the remaining
   gate for measuring the real-LLM path, but performance is not otherwise proven:
   the offline baseline is below target. Any semantic remediation after a real-LLM
   measurement requires a separately approved, Development-only B task; this
   benchmark did not tune frozen components.

Market remains C-owned; Outcome/model remains D-owned; Final Supervisor,
Streamlit and product/submission remain E-owned. Role B changed none of them.

## 6. Artifacts

The ignored runtime bundle is intentionally small:

- `reports/v045_role_b/offline_development_analysis_results.jsonl`
- `reports/v045_role_b/offline_pdf_run_manifest.json`
- `reports/v045_role_b/document_benchmark_summary.json`
- `reports/v045_role_b/risk_benchmark.csv`
- `reports/v045_role_b/evidence_benchmark.csv`
- `reports/v045_role_b/document_benchmark_protocol.json`

No PDF, annual ZIP, Evidence body, parsed page, chunk, model, index or cache is
stored in the repository or runtime report directory.

## 7. Verification performed

```text
Formal Golden schema/catalog integrity: PASS
Offline/closure benchmark + Legal/Business/Verifier/runtime tests: 204 passed
Python compile check: PASS
git diff --check: PASS
Full pytest: NOT RUN
438-case/PDF-heavy benchmark: NOT RUN
```

Only the ten governed Development PDFs were parsed. No full dataset benchmark or
unrelated test suite was run.
