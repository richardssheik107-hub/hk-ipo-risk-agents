# Competition Submission Runbook — v1.0.0

> Release: `v1.0.0`  
> 状态日期：`2026-08-30`  
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`  
> Role-B runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Final product-surface freeze：`006c7f302be5c278680d136371f6ef0db45fecc0`

This Runbook covers only governed post-freeze competition-submission operations. Product/algorithm development is closed. Live release truth is `V1_RELEASE_ACCEPTANCE.md`; submission status is `FINAL_SUBMISSION_STATUS.md`.

## 1. Immutable rules

- Existing Gold immutable;
- `UNJUDGED != negative`;
- offline and real-provider metrics remain separate;
- Validation is one-shot after freeze;
- Validation results cannot drive Retriever / Prompt / Agent / Verifier / threshold / model / evaluator tuning;
- 2025 Blind outcomes are not used for optimization;
- fallback is not real-provider success;
- Market missing values are not zero-filled;
- `uncalibrated_model_score` is not a probability;
- no issuer/case/page/Gold hardcoding;
- no fabricated Evidence;
- licensed PDFs, raw EOD/CSMAR, secrets, raw provider journals and local absolute paths do not enter the public/submission package.

## 2. Final Development truth

```text
Best offline ALL79
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

G2 remains BLOCKED under the self-defined 80% / 85% threshold. `v1.0.0` is a formal competition product release, not a statement that G2 passed.

## 3. Frozen identities

Read:

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/submission_closeout_status.json
```

Core freeze facts:

```text
Role-B runtime freeze main = ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a
Final product-surface freeze = 006c7f302be5c278680d136371f6ef0db45fecc0
Role-B benchmark = dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b
Development tuning = STOP
Validation opened at freeze = false
Blind outcome accessed = false
```

## 4. Canonical product launch contract

All four launch commands now enter the same approved workspace:

```text
START_DEMO.bat       ─┐
start_demo.sh         ├─→ app/streamlit_app.py
START_JUDGE_DEMO.bat  ┤
start_judge_demo.sh  ─┘
```

Judge launch commands are compatibility aliases. Every launcher runs runtime/clone-ready preflight and fails closed instead of opening a stale or half-working checkout.

The final product-surface commit `006c7f3...` passed:

```text
tests
Role D runtime
Team demo runtime
```

## 5. Clean-environment preflight

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,retrieval-research]"

python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/run_market_runtime_audit.py --strict --no-write
python scripts/run_dynamic_model_runtime_audit.py --strict --no-write
python scripts/check_final_product_capabilities.py
```

A failure may justify a packaging/runtime-environment fix, but not a score-driven algorithm reopen.

## 6. One-shot Validation

Run exactly once on the frozen identity in the authorized environment:

```text
ALL19 2024 Existing-Gold Validation
ONE SHOT
```

Before running, record:

```text
release version
Role-B runtime freeze SHA
final product-surface SHA
Role-B benchmark SHA
config / prompt / schema / evaluator identities
Validation not previously used for tuning
Blind outcome untouched
```

After running, write:

```text
reports/final_status/one_shot_validation_receipt.json
```

Minimum fields:

```text
status
one_shot = true
post_hoc_tuning = false
blind_2025_y_accessed = false
freeze/runtime identity
case count
measured metrics
execution timestamp
```

Do not inspect Validation errors and then modify the model/retriever/prompt/rules for a second run.

## 7. Final G5/G6 exact-tree check

On the exact final submission tree:

```bash
python scripts/check_final_product_capabilities.py
```

Confirm:

```text
reports/final_status/product_acceptance.json = pass
reports/final_status/capability_manifest.json = pass
truthful_channel_states = true
8/8 capability proofs present
```

If the checker rewrites hashes, commit only those deterministic manifest updates. This is artifact/hash rebinding, not feature development.

## 8. Fresh clone verification

Create a second clean directory and clone only the remote final `main`/release tree. Do not copy `.env`, PDFs, market data, local reports, caches or credentials.

Then run:

```text
install
compileall
pytest / required validators
team clone-ready checker
canonical demo bundle verification
START_DEMO / start_demo smoke
START_JUDGE_DEMO / start_judge_demo smoke
```

The last two launcher groups are expected to enter the same canonical Streamlit application.

## 9. Security / licensing / provenance audit

Reject from the public/submission package:

```text
.env
API keys / bearer tokens / refresh tokens
private keys
licensed prospectus PDFs
raw licensed EOD
raw or normalized restricted CSMAR data
raw provider journals
local absolute paths
cache / temp / failed experiments
Validation private working files
Blind outcomes
```

Confirm all included model/data artifacts are allowed for distribution and have provenance/hash records where required.

## 10. Final artifact index

Create one index containing at least:

```text
logical_path
owner
gate
required_or_optional
exists
size_bytes
sha256
allowed_in_submission
rejection_reason
```

Human Review artifacts are optional and must not block submission.

## 11. Secure competition package

The final package may include, subject to the competition platform rules:

```text
source code
allowed configs
README / quickstart / Runbook / release notes
final metric summary
frozen model manifests/artifacts allowed for redistribution
Risk/Evidence benchmark summaries
Market/Model governed audit summaries
case reports / trace
Evidence screenshot manifests/images allowed for submission
canonical demo replay
capability proof
release/freeze/Validation receipts
artifact index
submission_manifest.json
SHA256SUMS.txt
```

Do not package the entire `reports/` tree blindly.

## 12. Final acceptance command

After the one-shot Validation receipt, exact-tree G5/G6 check, clean clone and audits are complete:

```bash
python scripts/run_final_acceptance.py \
  --ci-status pass \
  --ci-evidence-url <FINAL_MAIN_CI_URL> \
  --package-preflight
```

The command is fail-closed. If G2 remains blocked, its final acceptance report must continue to say so; do not edit the gate logic to make the report green.

## 13. Defense package

Prepare separately from the source ZIP:

- final PPT;
- speaking script;
- Q&A memo;
- 5–10 minute demo/recording if required;
- key Evidence screenshots;
- one-page system architecture / workflow;
- backup offline replay procedure.

Main defense narrative:

```text
有什么风险
→ 为什么值得关注
→ 证据在哪里
→ 系统如何保证不编造 / 不越界
→ Market / Model 如何补充但不替代文档证据
→ 已知边界是什么
```

## 14. Release completion

The v1.0.0 product is frozen. Remaining work is submission governance and packaging only. Any new algorithmic experiment belongs to a later version and must not rewrite the v1.0.0 benchmark truth.
