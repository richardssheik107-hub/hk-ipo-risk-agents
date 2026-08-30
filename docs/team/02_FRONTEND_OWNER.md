# Person 2 — Frontend / Product Owner — CLOSED

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Final status: **G5 PASS / PRODUCT UI CLOSED**

## Final responsibility

The frontend track is complete for the competition release. No additional feature development is planned for v1.0.0.

The judge-facing product is designed around one question: can a reviewer quickly understand **what the risk is, why it matters, where the Evidence is, and why the system's conclusion is trustworthy**.

## Final supported modes

```text
Offline Demo Replay
Historical Governed IPO
Fresh New-IPO Analysis
```

All modes preserve runtime truth. `AVAILABLE / PARTIAL / UNAVAILABLE / ERROR` are backend states; the UI does not invent Market, Model or Evidence values.

## Final product surfaces

- risk overview;
- risk explanation + original Evidence;
- Market-X and frozen Model/SHAP state;
- conclusion-formation / agent trace;
- expert review and report;
- Evidence screenshot / physical-page navigation;
- single-case and batch outputs;
- standard and judge-facing Streamlit entrypoints.

## Launchers

```text
Windows standard: START_DEMO.bat
Windows judge:    START_JUDGE_DEMO.bat
Unix standard:    ./start_demo.sh
Unix judge:       ./start_judge_demo.sh
```

Launchers run preflight checks and fail closed instead of showing a stale or half-working checkout.

## G5 truth

Machine source:

```text
reports/final_status/product_acceptance.json
```

Final product acceptance:

```text
status = pass
truthful_channel_states = true
Offline Demo Replay = pass
Historical Governed IPO = pass
Fresh New-IPO Analysis = pass
```

## Governance

Frontend code must not:

- change Retriever / Agent / Risk / Evidence / Verifier semantics;
- manufacture Market/Model/Evidence values;
- turn model errors into a low-risk interpretation;
- edit Gold or Validation/Blind outcomes;
- hide a replay as if it were a live run;
- display uncalibrated model scores as probabilities.

Evidence original text remains in its source language. Judge-facing explanations default to clear Simplified Chinese.

## Post-release rule

Only fatal launch/rendering defects or truthful-presentation bugs may be fixed in the competition release line. New product features belong to a later version.
