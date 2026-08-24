# v0.4 PR-H Full E2E Integration Report

## Verdict

```text
PR-H implementation status = PARTIAL
PR-H formal gate = BLOCKED
PR-H COMPLETE / FROZEN = NO
v0.4.3 BASELINE E2E FREEZE = NOT CREATED
```

PR-G remains `COMPLETE / FROZEN`. PR-H is still the current formal gate.
The governed Market-X runtime and sanitized-model runtime wiring are implemented
and contract-tested, but the local assets required for the formal 3–5 real-IPO
matrix are not present. No frozen upstream pipeline was rerun to manufacture
them.

## Baseline

- source main: `169ca53fbdc430667c925484ef9e792eab0ab42e`
- working branch: `feature/v04-pr-h-full-e2e`
- PR-G frozen manifest:
  `reports/frozen/v04_pr_g_final_supervision_manifest.json`
- 2025 Blind outcome access: `false`

## Implemented runtime boundaries

### Governed Market-X

The v0.4 configurations now use a PR-B Core product projection instead of the
legacy v0.2 `MarketSnapshot` as the formal market-context source. The provider:

- resolves an exact official case from stock code and listing date;
- validates PR-B schema, policy, feature manifest, official bridge provenance,
  dataset split, content hash and the lossless raw/vector projection;
- exposes all 15 raw Core observations with explicit units and provenance;
- preserves unavailable values with a missing reason and never zero-fills them;
- never consumes mock market numbers as governed product data.

The checked-in PR-B Core is the available governed product source. Main also
contains the v0.4 C source manifests and readiness audit proving 438/438 HSI and
HKEX-turnover feature availability. Their ignored normalized files are not
present in this workspace, so PR-H cannot yet consume or claim those Extended
observations at runtime. Production industry returns remain intentionally
unavailable because the static classification mapping is not PIT-safe.

### Frozen model runtime

The workflow now has an opt-in internal model-projection node. It is built only
when `IPO_RISK_PR_F_RUN_DIR` points to a local sanitized handoff (or the strictly
verified developer-compatible full runtime). It uses the official catalog
`case_id`, preserves `uncalibrated_model_score`, exposes no probability field,
and never trains, scores or recalculates SHAP.

No path is committed in configuration. Invalid sanitized content fails closed
and cannot fall back to another source.

## Real-case execution

The only locally available governed prospectus was `ipo_2024_02410` / `2410.HK`.
Its PDF bytes match the existing PR-G freeze provenance.

```text
analysis status             completed
report sections             13
document channel            available
market channel              available
model channel               disabled
rule channel                available
market observations         15 / 15 available
Evidence references         2 / 2 resolved
creates new risk            false
probability claimed         false
2025 Blind y accessed       false
```

The Market-X feature manifest is
`c2f4a1699e2bf9149f24cb35ea32dbc4851c017001ec509a0eaccd93720d729d`.
The case artifact content hash is
`8bc00e3404f750582018e8b48a21062772d8ad8c31b558083bc160825baab1c5`.

Two independent executions used a request identity deterministically bound to
the official case, listing date and prospectus SHA-256. Their Final Supervisor
content hashes were identical:

```text
611b1bd59d5d686a41bc8d1fa513f8082f67461fecd4194ba168a15c93df9257
```

## Formal blockers

1. No local `model_results.json` from the frozen PR-F execution and no generated
   sanitized PR-F product handoff were found. Rerunning or reconstructing PR-F
   is forbidden, so no real per-case score/SHAP can be asserted.
2. Only one governed real prospectus PDF is present; PR-H requires 3–5 real
   validation cases.
3. Consequently, the required 3–5 case matrix with Document / Market / Model /
   Rule all available cannot be executed.

Required owner action: restore the original frozen PR-F runtime directory (or a
previously generated, hash-bound sanitized handoff) and provide at least three
matching real 2024 prospectus PDFs. The source must match the committed PR-F
`model_result_hash`; no upstream rerun or tuning is allowed.

## Safety and interface audit

- 2025 Blind y accessed: `false`
- upstream PR-A–PR-F rerun: `false`
- model retraining / score inversion / tuning: `false`
- mock market data in the formal Market-X view: `false`
- secrets or absolute local paths committed: `false`
- public Pydantic schema changed: `false`
- component Protocol changed: `false`
- v0.3 legacy configurations changed: `false`

## Gate decision

The implemented PR-H runtime infrastructure is suitable for review, but the
formal product gate cannot pass without the missing immutable inputs.

```text
PR-H = BLOCKED_MISSING_FROZEN_RUNTIME_INPUTS
NEXT = restore governed inputs, then execute the frozen 3–5 case matrix
```
