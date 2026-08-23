# ROLE B — PR-D DOCUMENT QA RESULT:

## BLOCKED

**Phase 2 disposition: `BULK_NOT_FOUND`.**

```text
Frozen bulk located:             NO
Bulk location:                   expected reports/v04_pr_a_full_13e0281/; absent
Bulk binding:                    NOT AVAILABLE
Production Document-X scanned:   0 / 438
Snapshots scanned:               0 / 438
Production analysis scanned:     0 / 438
NaN/Inf:                         NOT RUN
Forbidden Gold/Oracle fields:    NOT RUN
Evidence samples:                0
Evidence linkage passed:         0
Evidence provenance:             NOT RUN
PR-D compatibility:              PASS (metadata/code contract)
Explanation readiness:           PARTIAL
2025 blind outcome accessed:      NO
```

### Phase 2 bulk-location evidence

The PR-A completion report binds the runtime to source revision
`13e0281f5e65a970caaf1255e56d08597e1ead70` and names the canonical ignored
output root `reports/v04_pr_a_full_13e0281/`. The runbook and launch scripts
confirm the expected children `production_features/`,
`production_document/snapshots/`, `production_analysis/cases/`,
`execution_context.json`, `coverage_summary.json`, and
`determinism_report.json`.

Read-only, name-directed checks of the repository, its `reports/` tree,
`D:/Multi-Project/`, the explicit runbook locations, relevant environment
variables, and matching PowerShell history found no bulk root or archive. No
PDF content was read.

GitHub metadata for the frozen revision was also checked without downloading:

| Workflow run | Head SHA binding | Artifact metadata | Disposition |
|---|---|---|---|
| `32388465519` (`phase2`) | exact | `expert-annotation-phase2`, 6,123 bytes, not expired, SHA-256 `3a995406109c71afcbf7f77e81e2d3beb3aa505ad720c4df37233ab7000752cd` | annotation queue, not Production bulk |
| `32388465507` (`tests`) | exact | zero artifacts | no bulk |

Releases `v0.1`, `v0.2`, and `v0.3` have zero release assets; there is no
PR-A/v0.4 release asset. Git LFS has no tracked bulk path. Consequently no
candidate exists for a frozen-binding or content scan, and the small unrelated
artifact was not downloaded.

Phase 2 targeted validation completed with **143 passed in 47.65s**. This
covered the Role-B auditor, PR-A/PR-D orchestration and binding, canonical
Document materialization/schema, and Document Agent contracts. Archive tests
were not added because no archive implementation was needed; PDF-heavy
benchmarks and formal materialization were not run.

The frozen metadata contract and PR-D code path pass the Document-side static
review, but this checkout does not contain the ignored PR-A Production
Document-X, snapshot, or Production analysis bulk artifacts. Therefore the
required per-artifact finite-value / silent-zero-fill / forbidden-field scan and
a real Production Evidence sample could not be executed. This report does not
substitute frozen counts for those missing content checks.

```text
Official cases:                 438
Production Document-X:          438 (frozen binding)
Unique case IDs:                438 (frozen case-set binding)
Missing:                        0 (frozen case-set binding)
Orphan:                         0 (frozen case-set binding)
Duplicate:                      0 (binding builder rejects duplicates)

Schema:                         v04_document_features_v1
Feature dimension:              100
Feature order valid:            YES

Production / Oracle leakage:    NO

PR-D compatibility:             PASS

Evidence provenance:            NOT RUN (real bulk unavailable)

Explanation readiness:          PARTIAL

2025 blind outcome accessed:    NO
```

## Scope and evidence

The audit read only the official catalog, committed freeze/binding manifests,
Document feature/schema code, PR-D join/projection code, and tests. It did not
read PDFs, Expert Gold, Oracle feature payloads, or any 2025 outcome.

The deterministic metadata audit is stored at
`reports/v04_role_b/pr_d_document_contract_audit.json`. It independently
recomputed the official catalog identities and obtained:

```text
official count                 438
official unique case IDs       438
case-set hash                  f268fe544fc2607b8cacec7b7b51e9fe668b7fcd0e956202a66b7bef530ad90d
identity-set hash              9b8e1e3e1677d1d613dade66931b00a9793b38636d8f7e7a0e86a76c47e30976
Document manifest hash         241d34ab0311c6d24b1685e01385a4bd69c404a759dbe37e9f2825ce7b404be4
Document feature-order hash    5d60a81d4ac29b80c7d12b34d3f5c70d3f1a3c0c762c2cf9419f38999f7af415
Production artifact-set hash   9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3
```

The recomputed official case/identity hashes exactly match the frozen
`v04_pr_d_input_binding_v1` Production/Market/Outcome hashes. The PR-A freeze
also declares 438 Production Document-X, zero failures, zero silent drops, and
no Blind access. These facts validate coverage identity, but not the currently
unavailable individual values.

## Production Document-X contract

The live schema freezes 100 ordered positions: 88 risk-state/value positions
and 12 aggregates. Non-verified score/level/calculation positions are nullable;
the six-state one-hot values and explicit `missing` indicator prevent absence
from becoming a safe zero. PR-D validates the schema version, manifest hash,
feature order, value width, and artifact content hash before accepting a
Production block.

The new audit additionally fails closed on:

- non-finite or non-numeric values;
- non-verified score/level/calculation zero-fill;
- invalid state one-hot or missing indicators;
- missing `snapshot_hash` and identity provenance;
- filename/case identity mismatch;
- duplicate, missing, or orphan cases;
- Gold/Oracle-derived Production keys.

These value-level checks are implemented and fixture-tested but are **NOT RUN**
against the frozen 438-case bulk because that ignored runtime directory is not
present on this machine.

## PRODUCTION_ORACLE_LEAKAGE:

## PASS

No real Gold/Oracle field flow into Production Document-X or the Production
model matrices was found.

The Production path is:

```text
IPOAnalysisResult
-> V03DocumentRiskSnapshot
-> vectorize_document_snapshot
-> Production Document-X
-> production_document_block
-> P / PM projections
```

`run_v04_pr_a.py` invokes `build_oracle_document_features` only in the separate
`run_oracle` branch and writes it under `oracle_features`. PR-D validates Oracle
with `oracle_document_block`, requires `evaluation_only=true`, and only projects
O/OM from the explicit `oracle_intersection` cohort. P and PM select only the
Production component. Co-location of the two optional inputs is not treated as
leakage.

## PR-D Document compatibility

Document-side compatibility is **PASS** at contract/code level:

- the join compares case_id, stock_code, cohort year, listing date, and split;
- missing Production/Core artifacts fail closed;
- unavailable PR-C targets are explicit exclusions, not zero-imputed rows;
- Production schema/version/hash/order are exact;
- duplicate and unordered dataset rows are rejected;
- Core is a required first 30-position group;
- Production is a distinct 100-position group;
- PM is explicitly Core 30 then Production 100;
- optional Extended is not silently inserted into the historical order;
- Oracle remains a separate evaluation-only component/cohort;
- Blind rows are rejected by target, canonical record, dataset, and matrix
  contracts.

Formal PR-D materialization was not run.

## Evidence provenance

The Production runtime schema is structurally capable of the required trace:

```text
case_id
-> source_analysis_id
-> RiskItem (risk_code, conclusion, level/score, verifier status, agent)
-> Evidence (document/chunk, one-based physical page, text, source, bbox)
-> Calculation (formula, inputs, result, unit, evidence_ids)
```

The parser explicitly maps zero-based PDF indexes to one-based physical pages.
RiskItem retains Evidence and Calculation; Calculation retains Evidence IDs;
Verifier status and missing states remain explicit. Production Document-X itself
is deliberately numeric: it retains counts/state plus `snapshot_hash`, while the
snapshot retains `source_analysis_id` and `source_risk_id`. PR-G must resolve the
original Production result through that chain and must not use Expert Gold to
fill missing Evidence.

This is marked **FAIL for the strict current Gate** only because no real
Production analysis/snapshot sample was available for end-to-end link
verification. It is not a finding that the schema fabricates or loses physical
page semantics.

## Document Explanation readiness

Status: **PARTIAL**. Existing fields support a lossless read-only projection,
but there is no frozen public PR-G `DocumentExplanationRecord` schema yet.

Minimal proposal (no public Schema was changed here):

| Proposed field | Existing Production source |
|---|---|
| `case_id` | governed case identity / snapshot |
| `risk_code` | `RiskItem.risk_code` |
| `risk_level` | `RiskItem.level` |
| `summary` | `RiskItem.conclusion` |
| `evidence_pages` | `RiskItem.evidence[].page` |
| `evidence_previews` | bounded preview of `Evidence.text` |
| `calculation_summary` | `Calculation` formula/result/unit/success |
| `verifier_status` | `RiskItem.verification_status` |
| `missingness` | emitted state or canonical not-emitted/unavailable state |
| `provenance` | analysis/risk/agent/Evidence/Calculation identities |

`DocumentExplanationRecordProposal` and `build_explanation_records` live only
in the audit script. The conversion is pure, reads only `IPOAnalysisResult`,
preserves physical pages, calculation-to-Evidence linkage, verifier state, and
explicit not-emitted rows, and rejects duplicate final risks. Promoting this to
a protected public Schema requires a separate E/Product-led review.

## Issues

| Issue | Severity | Blocks PR-D | Owner | Evidence |
|---|---|---|---|---|
| Frozen PR-A Production/snapshot/analysis bulk is absent, so value and Evidence sampling are NOT RUN | High | Yes (Role-B Gate) | A — Pipeline | Name-directed local search and frozen-revision GitHub metadata found no suitable bulk/archive; audit disposition is `BULK_NOT_FOUND` |
| Existing PR-D Production block validation does not itself reject non-finite values, silent zero-fill, or forbidden additive Gold/Oracle keys | High | Yes until actual bulk passes the added audit or equivalent validation is integrated | D — Modeling | `production_document_block` validates hash/schema/order but uses permissive numeric tuples and ignores extra artifact fields; new negative tests cover all three cases |
| PR-D canonical record retains per-case artifact hash but not snapshot/source-risk IDs directly; downstream Evidence lookup still depends on retained PR-A artifacts | Medium | No for modeling; yes for standalone PR-G explanation | D — Modeling | `V04CanonicalFeatureBlock` contains schema/manifest/artifact hashes and values; source analysis/risk lineage remains in upstream snapshot/result |
| Public PR-G Document Explanation schema is not frozen | Medium | No | E — Product | Audit-only proposal and pure conversion tests are ready; protected Schema remains unchanged |

## Tests

```text
New Role-B audit tests:                  8 passed
Targeted PR-A/PR-D/Document regression: 149 passed
Full pytest:                             1362 passed
Ruff:                                    NOT RUN (module not installed)
PDF parsing / 438-case regeneration:     NOT RUN (prohibited)
Formal PR-D materialization:             NOT RUN (out of scope)
Real bulk value/Evidence audit:          NOT RUN (artifacts unavailable)
```

The full suite was run with pytest cache disabled and task temporary files under
`.tmp_v04_role_b_document_qa/`.

## PASS Gate

```text
A  Frozen coverage binding matches official catalog      PASS
B  No duplicate/missing/orphan in frozen case binding     PASS
C  Schema/dimension/order                                 PASS
D  No demonstrated Oracle/Gold leakage                    PASS
E  PR-D consumes Production Document-X correctly          PASS
F  Provenance structurally traceable                      PASS (sample NOT RUN)
G  Real Production Evidence retrieval                     BLOCKED
H  Explanation proposal is explicit/non-blocking          PASS
I  2025 blind outcome access                              PASS (NO access)
J  Frozen Retriever/Agent logic unchanged                 PASS
K  Tests                                                  PASS
L  Temporary directory cleanup                            PASS
```

Because Gate G and the actual-content portion of A/C/F cannot be independently
executed in this checkout, the truthful final result is **BLOCKED**, not PASS.

## Git and disk state

Final Git/disk/temporary cleanup values are reported in the task handoff after
the last cleanup check. No commit, push, remote write, merge, rebase, or PR was
performed.
