# ROLE B — COMPETITION DOCUMENT INTELLIGENCE RESULT:

## PARTIAL

Role B now has a deterministic, submission-shaped benchmark runner and private
Evidence-bounded semantic contracts, but the formal competition Gate cannot pass.
No governed analysis results overlap the Role-B Human Golden, no 2024 Role-B
validation set is available, and no external LLM call was authorized. Stub and
contract results are not presented as real LLM performance.

```text
Development cases:                 10
Validation cases:                   0
Real LLM cases:                     0
Stub-only benchmark cases:          0

Risk Precision:          NOT AVAILABLE
Risk Recall:             NOT AVAILABLE
Risk F1:                 NOT AVAILABLE

Evidence Recall@5:       NOT AVAILABLE (end-to-end)
Evidence Precision@5:    NOT AVAILABLE
Physical-page correctness: NOT AVAILABLE

Legal semantic chain:              PARTIAL
Business semantic chain:           PARTIAL
Disclosure Tone:                   PARTIAL

2025 blind outcome accessed:       NO
```

The frozen Retriever locked-validation reference is reported separately. Its
LTR-C Evidence Recall@5 is `0.6989247312`; this is not a current Agent or LLM
benchmark and does not satisfy the competition Evidence target by itself.

## 1. Capability matrix

| Capability | Existing | Real LLM path | Evidence validation | Verifier | Benchmark |
|---|---|---|---|---|---|
| `redemption_rights` | Formal risk code, structured fact, Builder | Yes when a provider is configured; unavailable by default | Candidate IDs normalized against bounded Evidence | `LegalRightsVerifier` | 4 formal Development judgments; no governed predictions |
| `material_litigation_compliance` | Formal risk code, classifier, structured fact, Builder | Yes when configured; deterministic negative/generic short-circuit | Candidate IDs normalized; actual/generic/negative classification retained | `LitigationComplianceVerifier` | 4 formal Development judgments; no governed predictions |
| `related_party_transaction` | Competition extension only | No production task | Private scoped fact proposal added | No registered verifier | No formal Golden |
| `core_product` | Internal candidate/fact, not a formal risk code | Optional Business cross-check | Supplied Evidence identity plus citation subset | Through `precommercial_product` only | Covered indirectly by 3 Business judgments |
| `pipeline_stage` | Internal Business field | Optional Business cross-check | Same bounded Evidence guard | Through `precommercial_product` only | No field-level Golden |
| `commercialization_status` | Deterministic-first internal fact | Optional Business cross-check | Out-of-scope citation and conflicts fail closed | `V03BusinessVerifier` | No field-level Golden |
| `product_revenue_semantics` | Distinguishes product sales from licensing/milestone/service/collaboration | Optional Business cross-check | Deterministic facts cannot be overwritten | `V03BusinessVerifier` | No exhaustive field-level Golden |
| `disclosure_tone` | Private structured contract only | Provider-neutral contract, not production-registered | Supporting Evidence IDs must be bounded | Not registered; cannot change severity | No formal Golden |

`core_product`, `pipeline_stage`, `commercialization_status`, and revenue source
semantics are structured facts or diagnostics. They are not new public risk codes.
Disclosure Tone remains report-only interpretation. Role B did not change
`src/ipo_risk/domain/risk_codes.py`, public Schema, workflow, provider registry,
Retriever, API, Final Supervisor, or Streamlit.

## 2. Existing runtime truth

### Legal

The Legal Agent has the real provider-capable chain:

```text
bounded Retriever Evidence
→ ShareholderRightsExtractor / LitigationComplianceExtractor
→ Pydantic candidate
→ deterministic normalization and Evidence-ID filtering
→ Risk Builder
→ specialized Legal Verifier
```

It distinguishes terminated rights, listing survival, restoration conditions,
actual current legal matters, generic future disclosures, explicit negatives, and
resolved/remediated matters. With no configured provider, actual semantic
extraction degrades to typed diagnostics; it is not a real LLM run.

### Business

The Business Agent is deterministic-first. It optionally makes two structured LLM
calls for commercialization and core-product facts, rejects citations outside the
Retriever result, and sends deterministic/LLM disagreements to review. Formal
production output remains only `precommercial_product`. Licensing, milestone,
R&D-service, and collaboration income do not become product-sales revenue.

The new private contract makes the intended distinctions explicit without changing
production registration:

```text
core product / candidate
pipeline stage
commercialized / pre-commercial
product-sales revenue / licensing / service / milestone / collaboration
```

Deterministic values remain authoritative during reconciliation. Any different
non-empty LLM value produces `needs_review` and a field-level conflict list.

### Related party and Disclosure Tone

`related_party_transaction` has no public RiskItem registration, Builder, Verifier,
prompt identity, or Human Golden. The added `RelatedPartyTransactionFact` is an
internal contract proposal only. A must approve a public contract and risk
registration before production use.

Disclosure Tone now has a private bounded schema for `tone_risk`, hedging language,
obfuscation signal, missing quantification, and supporting Evidence IDs. It cannot
create a RiskItem or change severity, and is not production-integrated.

## 3. Benchmark baseline and provenance

The runner reuses `src/ipo_risk/evaluation/golden_eval.py` for the existing Risk
Precision/Recall/F1 definition. It adds availability semantics so absent governed
results produce `NOT AVAILABLE`, not a misleading numeric zero.

Human Golden inventory:

| Risk code | Formal rows | Cases | Split |
|---|---:|---:|---|
| `redemption_rights` | 4 | 4 | Development |
| `material_litigation_compliance` | 4 | 4 | Development |
| `precommercial_product` | 3 | 2 | Development |
| **Total** | **11** | **10 unique** | **Development only** |

The Business positive case has two judged Evidence pages for one case/risk pair;
this explains why it has three rows but two cases. Non-Gold predictions remain
unjudged and are excluded from metric precision.

Generated lightweight artifacts:

```text
reports/v045_role_b/document_benchmark_summary.json
reports/v045_role_b/risk_benchmark.csv
reports/v045_role_b/evidence_benchmark.csv
```

The repository ignores `reports/*`; these outputs remain local and were not forced
into Git. They contain counts and metrics only, with no Evidence text, page text,
PDF, prompt, response, credential, or runtime bulk.

### Current baseline

| Metric | Result | Reason |
|---|---:|---|
| Risk Precision / Recall / F1 | NOT AVAILABLE | No overlapping governed Agent analysis JSONL |
| Macro risk average | NOT AVAILABLE | No per-risk governed predictions |
| Evidence Recall@1/3/5 end-to-end | NOT AVAILABLE | No governed Agent Evidence output |
| Evidence Precision@5 | NOT AVAILABLE | Golden is not exhaustive for irrelevant page judgments |
| Physical-page correctness | NOT AVAILABLE | No matching governed analysis/PDF matrix supplied |
| Evidence-scope validity ratio | NOT AVAILABLE | No real structured LLM outputs |
| Structured-output schema-valid ratio | NOT AVAILABLE | No real structured LLM outputs |
| Verifier ratios | NOT AVAILABLE | No governed benchmark Agent results |
| Extraction failure ratio | NOT AVAILABLE | No governed benchmark Agent results |

Frozen Retriever reference only:

| Risk code | LTR Recall@5 | LTR Recall@20 |
|---|---:|---:|
| `redemption_rights` | 63.64% | 90.91% |
| `material_litigation_compliance` | 50.00% | 83.33% |
| `precommercial_product` | 10.00% | 50.00% |
| all frozen risks | 69.89% | 89.25% |

This historical locked validation was already consumed. No Retriever algorithm,
ranking, query, keyword, BM25, table, or LTR artifact was changed in this task.

## 4. Failure matrix

Because governed Agent results are absent, semantic outcome categories cannot be
populated from real runs. The current measurable blockers are:

| Category | Count | Interpretation |
|---|---:|---|
| parser/input issue | 10 cases | Formal Golden cases have no supplied governed analysis result |
| LLM provider unavailable | 10 cases | No external LLM call was authorized/configured for this run |
| retrieval miss | NOT EVALUATED | Frozen reference is reported separately |
| invalid structured response | NOT EVALUATED | Covered by contract test only |
| Evidence out of scope | NOT EVALUATED | Covered by negative contract test only |
| semantic conflict | NOT EVALUATED | Covered by deterministic conflict test only |
| Builder insufficient facts | NOT EVALUATED | Requires governed case outputs |
| Verifier rejected | NOT EVALUATED | Requires governed case outputs |
| Gold/schema mismatch | 0 observed | Golden rows loaded under the frozen eligibility policy |
| unknown | 0 observed | No real run was classified |

## 5. Gate decisions

### Gate 1 — Baseline

PASS as an honest availability baseline. The benchmark artifacts exist and retain
`NOT AVAILABLE` wherever the source data cannot support a metric.

### Gate 2 — Failure matrix

PARTIAL. Missing governed results and external LLM authorization are proven;
case-level semantic failures are not available.

### Gate 3 — Minimal B-owned repair

One private variant was implemented:

```text
Pydantic structured fact
→ bounded Evidence scope validation
→ deterministic-authoritative reconciliation
→ conflict / needs_review
```

No case/company/product/page hardcode and no Retriever change were added.

### Gate 4 — Freeze

The private contract and benchmark version are fixed as
`v045_role_b_document_benchmark_v1`. Production promotion is not claimed.

### Gate 5 — Validation

NOT RUN. There is no Role-B 2024 Human Golden validation set, and no real LLM
authorization. Historical Retriever locked validation was already consumed and was
not reopened for tuning.

## 6. Tests and safety

```text
New bounded semantic + benchmark tests:       14 passed
Initial new-test run:                         13 passed, 1 failed
Blind guard after fix:                        14 passed
Legal/Business/Verifier/evaluation regression: 147 passed in 4.51s
Compile check:                                PASS
Full pytest:                                  NOT RUN
PDF-heavy benchmark:                          NOT RUN
External LLM calls:                           0
Model downloads:                              0
```

The initial failure showed that a 2025 case mislabeled `dataset_split=development`
could bypass the split guard. The benchmark now checks case identity before notes.
No 2025 outcome file or value was opened.

## 7. Required handoffs and ownership

| Need | Owner | Why Role B must not implement it here |
|---|---|---|
| Public `related_party_transaction` risk contract, Builder/Verifier registration | A review + B implementation | Public Schema/risk registry/workflow boundary |
| Governed real-case analysis matrix and 2024 validation allocation | A | Integration, case matrix, validation governance |
| Authorization/configuration for real external LLM runs | A/user | Data egress, cost, credential and provider policy |
| Market facts/Agent | C | Market ownership |
| Outcome/model/evaluation tables | D | Quant and outcome ownership |
| Final Supervisor, trace, UI, Human Review | E | Product/Supervisor ownership |

## 8. Answers required for the sprint

1. Legal redemption/litigation are real-provider-capable LLM paths; without a
   provider they degrade honestly. Business is deterministic-first with optional
   LLM cross-check. Related party and Disclosure Tone are not production paths.
2. Missing B-owned capabilities are production-approved related-party semantics,
   field-level Business Golden, governed real LLM runs, and a verified Disclosure
   Tone integration.
3. The 80% Risk and 85% end-to-end Evidence targets are **not established**. Risk
   metrics are unavailable; the separate frozen Retriever Recall@5 is 69.89%.
4. No real-run Evidence hallucination rate can be claimed. Contract tests reject
   empty, duplicate, and out-of-scope citations.
5. Existing Legal/Business Verifiers reject or review unsupported conclusions in
   targeted regression; no governed benchmark ratio is available yet.
6. No external LLM was called because neither data-egress authorization nor active
   provider configuration was present.
7. A approval is required before any public related-party risk or Disclosure Tone
   contract/workflow change.
8. B next needs governed Development analysis outputs plus authorized real LLM runs,
   followed by a frozen 2024 validation run if A supplies an untouched set.
9. Market work belongs to C; outcome/model work to D; Supervisor/product work to E;
   contracts, integration, validation allocation, and release belong to A.
