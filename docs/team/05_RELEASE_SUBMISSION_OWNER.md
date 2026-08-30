# Person 5 — Release / Submission Owner — v1.0.0 Operations

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final status：**PRODUCT RELEASED / SUBMISSION OPERATIONS REMAIN**

## 1. Role after v1.0.0

Algorithm and product feature development are closed. The release owner is responsible only for governed competition-submission operations:

```text
one-shot Validation
→ final hash rebinding
→ clean clone
→ security / licensing / provenance audit
→ artifact index
→ secure package
→ defense materials
```

## 2. Final truth that must not change

```text
Best offline ALL79
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

The internal G2 target was not met. G2 must remain BLOCKED unless a future version legitimately changes the measured product under a new benchmark identity. v1.0.0 does not claim G2 PASS.

## 3. Final gate state

```text
G0 Runtime / contracts / CI     PASS
G1 Stable final-three           PASS
G2 Document Intelligence        BLOCKED
G3 Dynamic Market-X             PASS
G4 Dynamic Model / SHAP         PASS
G5 Final Frontend / Product     PASS
G6 Capability demonstrations    PASS
G7 Validation / package         PARTIAL
```

Live source:

```text
docs/V1_RELEASE_ACCEPTANCE.md
docs/FINAL_SUBMISSION_STATUS.md
reports/final_status/submission_closeout_status.json
```

## 4. One-shot Validation

Run exactly once on the frozen identity in the authorized environment. Write:

```text
reports/final_status/one_shot_validation_receipt.json
```

Required semantics:

```text
one_shot = true
post_hoc_tuning = false
blind_2025_y_accessed = false
```

Validation results may be recorded and discussed, but may not be used to tune Retriever, Prompt, Agent, Verifier, thresholds, model or evaluator.

## 5. Final exact-tree rehash

After the final submission tree is fixed:

```bash
python scripts/check_final_product_capabilities.py
```

Confirm G5/G6 artifacts match the exact tree. This is hash/provenance maintenance, not feature work.

## 6. Fresh clone

Clone the remote release/main tree into a second clean directory without copying local environment state. Run install, validators, clone-ready checks, demo verification and frontend smoke.

Do not copy:

```text
.env
credentials
PDFs
raw EOD / CSMAR
local cache
raw provider journals
private Validation working files
```

## 7. Security / licensing / path audit

Reject from the public/submission package:

- API keys / tokens / private keys;
- licensed prospectus PDFs;
- raw licensed market data;
- restricted normalized CSMAR files;
- raw LLM/provider journals;
- absolute local paths;
- caches, temp files and failed experiments;
- Blind outcomes;
- unauthorized model/data artifacts.

## 8. Final artifact index

Create one index with:

```text
logical path
owner
gate
required / optional
exists
size
SHA-256
allowed_in_submission
rejection reason
```

## 9. Final package

Use the competition platform's exact submission requirements. Typical allowed deliverables include source, configs, final docs, metric summaries, frozen manifests, governed audit summaries, reports, approved screenshots/replay assets, artifact index and SHA256SUMS.

Do not upload the entire repository `reports/` directory blindly.

## 10. Defense materials

Prepare:

- final PPT;
- defense script;
- Q&A memo;
- demo recording/video if required;
- key Evidence screenshots;
- offline replay backup path;
- one-page architecture / product-flow summary.

## 11. Completion rule

The v1.0.0 product release is complete. Person 5 remains responsible only for the external/local submission steps that cannot be completed by repository edits alone.

No release operation may weaken the frozen metric, Evidence, PIT, model or governance contracts.
