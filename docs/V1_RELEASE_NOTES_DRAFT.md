# v1 Release Notes Draft

> Status: draft for final packaging / GitHub Release  
> Recommended tag while G2 remains blocked: `v1.0.0-rc1`

## Overview

HK IPO Risk Agents is an evidence-driven multi-agent Hong Kong IPO risk-analysis and market-warning system built for the competition workflow. The final product combines prospectus document intelligence, governed pre-listing market context, frozen-model inference, native SHAP explanation, conflict/re-check supervision, and a judge-facing UI.

## Final product capabilities

- Real PDF parsing with physical-page Evidence traceability;
- Financial, Legal and Business professional Agents;
- deterministic Calculation + specialized Verifier;
- Final Supervisor with conflict / re-check;
- Dynamic Market-X with PIT-safe missingness;
- frozen Role-D V2 runtime inference + native SHAP;
- Offline Demo Replay / Historical Governed IPO / Fresh New-IPO Analysis;
- judge-facing Streamlit workspace;
- Evidence screenshots, single-case report, batch report, trace/provenance;
- fail-closed runtime and release acceptance tooling.

## Final Development metrics

| Mode | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | 70/102 = 68.63% | 103/191 = 53.93% |
| Real LLM gated | 79/79 | 61/102 = 59.80% | 93/191 = 48.69% |

The repository's self-defined G2 target is M1 >=80% and M2 >=85%. The target was not reached, so the release must not claim `COMPETITION_READY=true`.

## Stable gates

```text
G0 Runtime / CI              PASS
G1 Stable final-three        PASS
G2 Document Intelligence     BLOCKED
G3 Dynamic Market-X          PASS
G4 Dynamic Model / SHAP      PASS
G5 Final Product             PASS
G6 Capability proofs         PASS
G7 Freeze / Validation / ZIP PARTIAL
```

## Validation and governance

- Existing Gold remains immutable;
- Gold does not enter runtime retrieval/prompt/agent logic;
- 2024 Validation is one-shot after freeze;
- 2025 Blind outcome is not used for optimization;
- Market missingness is not zero-filled;
- `uncalibrated_model_score` is not a probability;
- fallback/mock/unavailable states never masquerade as real-provider success;
- licensed PDFs, raw EOD/CSMAR data, raw provider journals and credentials are excluded from the public package.

## Known limitations

- G2 self-defined quality threshold was not reached;
- real-LLM gated performance is below best offline, indicating negative transfer / strict structured-contract failures in some LLM augmentation paths;
- source-edition and exact-anchor provenance still constrain part of M2;
- Market-X can honestly return PARTIAL / UNAVAILABLE outside governed coverage;
- model scores are uncalibrated and are not price predictions;
- remote LLM prose is not byte-for-byte deterministic;
- licensed data is not redistributed.

## Recommended release policy

If GitHub Release naming must preserve the repository's own readiness semantics, publish the current final package as `v1.0.0-rc1`. Promote to `v1.0.0` only if the team explicitly decides that a formal 1.0 product release does not require the internal G2 target, or if G2 is later closed without violating Validation/Blind governance.
