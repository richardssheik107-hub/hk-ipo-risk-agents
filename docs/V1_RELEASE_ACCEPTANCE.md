# v1.0.0 Release Acceptance — Final Competition Product Truth

> Release: `v1.0.0`  
> Release date: `2026-08-30`  
> Runtime freeze: `ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Metric protocol: `v045_competition_metric_protocol_v2_existing_gold_only`  
> Product release decision: **APPROVED**  
> Internal `COMPETITION_READY`: **FALSE — G2 remains below the self-defined threshold**

This document is the v1.0.0 release source of truth. It replaces `V0.4_RELEASE_ACCEPTANCE.md` as the live release-status document.

## 1. Release semantics

Two statements are intentionally separated:

```text
v1.0.0 product release = APPROVED
COMPETITION_READY under internal gates = FALSE
```

The first means the competition product is feature-complete, frozen and ready to package/submit with known limitations. The second remains false because the project's own Document Intelligence target was not achieved.

No threshold, evaluator or Gold record is changed to make the release green.

## 2. Final ALL79 Development truth

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

Formal real-provider facts:

```text
real_llm_cases = 79/79
provider = openai_responses
model = ark-code-latest
G2 M1 threshold = 80%
G2 M2 threshold = 85%
G2 status = BLOCKED
```

The offline result is a separate engineering reference and must never replace the real-LLM gated result in claims that require a provider-backed run.

Machine-readable source:

```text
reports/v045_role_b/document_benchmark_summary.json
```

## 3. Gate table at v1.0.0

| Gate | Status | Release interpretation |
|---|---|---|
| G0 Runtime / contracts / CI | PASS | release baseline healthy |
| G1 Stable final-three baseline | PASS | canonical demo/regression baseline protected |
| G2 ALL79 Document Intelligence | **BLOCKED** | known research/quality limitation |
| G3 Dynamic Market-X | PASS | governed historical + dynamic PIT runtime |
| G4 Dynamic Model / SHAP | PASS | frozen V2 inference + native SHAP |
| G5 Final Frontend / Product | PASS | truthful Demo/Historical/Fresh modes |
| G6 Capability demonstrations | PASS | 8/8 hash-bound qualitative proofs |
| G7 Freeze / Validation / package | **PARTIAL** | runtime freeze complete; local one-shot Validation/package actions remain |

## 4. Frozen product capabilities

- real PDF parser and physical-page Evidence;
- Financial / Legal / Business agents;
- deterministic Calculation and specialized Verifier;
- Document Supervisor and Final Supervisor;
- conflict detection / bounded re-check;
- Dynamic Market-X with explicit `AVAILABLE / PARTIAL / UNAVAILABLE` semantics;
- Frozen Role-D V2 model with native SHAP;
- Offline Demo Replay;
- Historical Governed IPO;
- Fresh New-IPO Analysis;
- judge-facing UI;
- Evidence screenshot / trace / single-case / batch report;
- API/UI capability surface.

## 5. Frozen identities

Runtime freeze evidence:

```text
reports/final_status/final_freeze_manifest.json
```

Key identities include:

```text
Role-B benchmark commit = dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b
Runtime freeze main = ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a
Role-B provider = openai_responses
Role-B model = ark-code-latest
Role-D V2 model SHA-256 = 320e810e85dcdb7e6caa40f9ef2b20157005e7a1d1af38ad7d586dd0feee72e2
Model score semantics = uncalibrated_model_score
Market missingness = missing_is_not_zero
```

Release-document and packaging changes after the runtime freeze are allowed only if they do not alter the frozen runtime identity.

## 6. Product acceptance

G5 and G6 are represented by:

```text
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

They establish:

```text
Offline Demo Replay = PASS
Historical Governed IPO = PASS
Fresh New-IPO Analysis = PASS
truthful channel states = true
capability demonstrations = 8/8 PASS
```

Capability demonstrations without Existing Gold are qualitative proof and are not added to M1/M2.

## 7. Known limitations accepted for v1.0.0

1. G2 is below the internal M1/M2 target.
2. Real-LLM gated output is worse than the selected offline path on the final Development measurement.
3. Source-edition / exact-anchor provenance still limits some Evidence coverage.
4. Dynamic Market-X may honestly degrade outside governed PIT coverage.
5. The Role-D V2 signal is uncalibrated and remains a triage signal rather than a probability forecast.
6. Remote LLM prose is not byte-for-byte deterministic.
7. Licensed PDFs, raw market data and secrets are intentionally absent from the public release.

## 8. Governance retained in v1.0.0

- Existing Gold immutable;
- `UNJUDGED != negative`;
- Gold never enters runtime Retriever / Prompt / Agent;
- no issuer/stock/case/page/Gold-text hardcoding;
- no fabricated Evidence;
- exact numeric claims require deterministic support;
- Market PIT-safe, missing != zero;
- model score != probability;
- fallback != real-provider success;
- 2025 Blind outcomes not used for optimization;
- no secrets, licensed PDFs, raw EOD or raw provider journals in the public/submission package.

## 9. Remaining governed submission actions

These do not reopen product development:

```text
one-shot ALL19 2024 Existing-Gold Validation
→ one_shot_validation_receipt.json
→ final G5/G6 rehash on exact submission tree
→ fresh-clone verification
→ security / provenance / licensing / path audit
→ final artifact index
→ secure submission ZIP + SHA256SUMS
→ competition PPT / script / recording if required
```

Validation results must not drive post-freeze Retriever, Prompt, Agent, Verifier, threshold, model or evaluator changes.

## 10. v1.0.0 acceptance decision

**APPROVE v1.0.0 as the final competition submission product release with the above known limitations.**

Do not claim:

```text
G2 PASS
COMPETITION_READY=true
offline score as real-LLM score
model score as a probability
full availability when a governed channel is partial/unavailable
```

The release is complete as a product version; competition packaging and one-shot Validation remain governed operational follow-up tasks.
