# v0.4.5 Role D Final Closure

> Status date: 2026-08-28
>
> Gate: `D1_multi_horizon_evaluation`
>
> Current status: **CURRENT-MAIN STRICT REVALIDATION PASS — A MODEL DECISION PENDING**

Role D owns the governed post-listing outcome/evaluation lane. The implementation, strict acceptance checker, frozen bindings and governed 70-case materialization are complete. On 2026-08-28 the exact frozen PR-E/PR-F runtime and governed filtered EOD store were recovered and the current `main` base (`8211cc4a59e07529ad39faaa47ab3fcb35f565f5`) passed a fresh strict rerun. The licensed raw EOD archive and complete research runtimes remain intentionally outside Git; both historical and current-main runs are therefore recorded as hash-bound receipts.

## 1. Four evidence layers

### Layer A — committed implementation

The repository contains:

```text
scripts/build_v045_role_d_m5.py
scripts/check_v045_role_d_m5.py
src/ipo_risk/evaluation/role_d_m5.py
src/ipo_risk/evaluation/role_d_acceptance.py
```

The strict checker independently validates the exact four-file canonical directory, 70-case 2024 Validation set, 1D/5D/20D/60D trading-session returns, frozen PR-E/PR-F bindings, metric recomputation, provenance, Blind protection and deterministic semantics.

### Layer B — recorded governed materialization

The immutable repository receipt is:

```text
reports/frozen/v045_role_d_m5_materialization_receipt.json
```

Validate it without network or licensed data:

```bash
python scripts/validate_v045_role_d_receipt.py
```

The validator binds the receipt to:

```text
reports/frozen/v04_pr_f_lightgbm_manifest.json
reports/frozen/v04_pr_e_baseline_manifest.json
configs/v045_competition_metric_protocol.json
```

It also rejects artifact-set drift, hash drift, metric/horizon drift, unsafe governance flags, secrets and local absolute paths. This receipt is historical release evidence; it is not a substitute for the strict live checker when the external inputs are available.

### Layer C — live strict rerun

A live rerun requires all of:

```text
complete frozen reports/v04_pr_f runtime
complete frozen reports/v04_pr_e runtime
authorized hkshareeodprices.csv or its valid governed filtered store
current data/catalog bridge and source manifest
```

Build and validate:

```bash
python scripts/build_v045_role_d_m5.py \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output-dir reports/v045_role_d

python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output reports/v045_role_d_acceptance/acceptance.json
```

A successful shell exit from the builder is not sufficient; the strict checker must return `passed=true`.

### Layer D — current-main strict revalidation receipt

The 2026-08-28 rerun is recorded in:

```text
reports/frozen/v045_role_d_current_main_revalidation_receipt.json
```

Validate its frozen bindings, canonical artifact hashes, deterministic rebuild
evidence, final-three handoff and model-decision boundary without licensed data:

```bash
python scripts/validate_v045_role_d_revalidation_receipt.py
```

The strict checker returned `PASS` for all 12 checks. A same-directory
`--resume` and an independent fresh-directory rebuild produced byte-identical
four-file outputs.

## 2. Recorded D1 result

Source evidence:

```text
PR #141
merge commit = 2eb4bea6104e47c6472848d826e2572018909094
recorded at = 2026-08-27T12:15:03Z
evidence comment = pull/141#issuecomment-5438960640
```

Materialization scope:

```text
evaluation split = 2024 Validation
evaluated IPOs = 70
horizons = 1D / 5D / 20D / 60D
primary definition = return_5d <= -0.10
raw EOD SHA-256 = 190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
governed filtered store = 433,776 rows / 438 target IPOs
blind_2025_y_accessed = false
deterministic --resume = PASS
```

Canonical artifact hashes:

| Artifact | SHA-256 |
|---|---|
| `test_predictions.csv` | `8521dabe3f976e5c532f55fe1571294eb9555ae644a32d524233680af74fa93a` |
| `multi_horizon_results.csv` | `f2d3382f2618e3d328155e9a37e81cd01a156cfc0787c8bc42320237dbb56725` |
| `evaluation_summary.json` | `6d542b025e5a9c52285a80fcdde198282c389ebc55773b40b644ccf0b74f7a63` |
| `ai_vs_offline_report.json` | `3aab6fc39f75f1c350f92ab329df97c97ca48105235d906f5ef213731f180c94` |

Current-main revalidation hashes preserve the two CSV hashes exactly. The two
JSON hashes changed because the current contract is `v2` and adds complete
portable PR-E/PR-F source hashes; the strict checker independently accepted
them:

| Artifact | Current-main SHA-256 |
|---|---|
| `test_predictions.csv` | `8521dabe3f976e5c532f55fe1571294eb9555ae644a32d524233680af74fa93a` |
| `multi_horizon_results.csv` | `f2d3382f2618e3d328155e9a37e81cd01a156cfc0787c8bc42320237dbb56725` |
| `evaluation_summary.json` | `9eb0568a9253c410c30f2183e1fa58606313620954b88500f1d3f7104cc073c2` |
| `ai_vs_offline_report.json` | `e5fc17b93cc535fcd966bf78ef1aea4b74fa3c79da9577beb90ac76c7f25e197` |

Five-day descriptive metrics:

| Metric | Value |
|---|---:|
| Precision | 0.3333 |
| Recall | 0.0435 |
| F1 | 0.0769 |
| PR-AUC | 0.3364 |
| ROC-AUC | 0.4246 |
| Top-10% hit rate | 0.4286 |
| Top-20% hit rate | 0.2857 |
| Base prevalence | 0.3286 |

The competition protocol defines no absolute M5 score threshold. These values are reported as-is; they do not authorize score inversion, recalibration, model replacement or 2024 Validation retuning.

## 3. D-to-E final-three product handoff

The label-free handoff implementation is complete. The governed final case list is:

```text
configs/v045_demo_cases.json
```

When the complete frozen PR-F runtime is available, build the package with:

```bash
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --frozen-dir reports/frozen \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

The builder verifies the frozen `model_result_hash` and writes an exact four-file, checksum-bound package containing only case identity, the frozen uncalibrated score and frozen SHAP drivers. It excludes actual returns and target labels.

Current status after the current-main rerun:

```text
handoff implementation = COMPLETE
governed final-three manifest support = COMPLETE
final-three package strict validation = PASS
case IDs = ipo_2024_02410 / ipo_2024_02460 / ipo_2024_01318
label or realized-return fields = absent
package materialized in Git = true
runtime config enabled = true
Market-X Core final-three materialized in Git = true
fresh-checkout product preflight = 3/3 Market available + 3/3 Model available
```

The committed package is byte-identical to the four-file package already recorded
by the immutable current-main receipt.  It was recovered only after validating
the receipt and the exact `test_predictions.csv` byte hash; every output hash
matches the previously accepted handoff.  This is not a reconstructed model or
a hand-edited signal.

The ordinary build remains the preferred path when full frozen PR-F runtime
files are present.  Disaster recovery from the receipt-bound D export is:

```bash
python scripts/build_v04_pr_f_product_handoff_from_receipt.py \
  --predictions reports/v045_role_d/test_predictions.csv \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

Fresh-checkout product verification:

```bash
python scripts/check_v045_product_runtime.py
```

## 4. v2 high-recall candidate

This section records the historical pre-promotion closure state. It is superseded by the versioned V2 promotion manifest/receipt and `docs/ROLE_D_MODEL_DECISION.md`; the old PR-F artifacts described here remain preserved for audit and rollback.

```text
v2_candidate_promoted = false
frozen_pr_f_retrained = false
score_direction_inverted = false
validation_retuning_performed = false
```

Any promotion decision belongs to A-owned governance and requires a separate frozen decision record.

## 5. Closure boundary

The following are complete in the repository:

```text
M5 builder
strict D acceptance checker
four-file contract
frozen PR-E/PR-F binding
recorded 70-case materialization receipt
current-main strict revalidation receipt and validator
network-free receipt validator and tests
CI receipt validation
governed final-three demo-case manifest support
validated label-free final-three package evidence
committed receipt-bound final-three Market-X Core projections
committed byte-identical label-free final-three model handoff
3/3 Market and 3/3 Model product-runtime preflight
deterministic resume and fresh-directory rebuild evidence
D closure documentation
```

The following cannot be honestly completed from committed files alone:

```text
A-owned promote/retain decision for v2
v2 freeze and re-materialization if A selects promotion
committing the licensed EOD archive or full external frozen research runtime
```

The current-main D result files and the small label-free final-three product
projections now exist as validated, hash-bound Git artifacts. Licensed raw EOD
and full research runtime files remain outside Git. This does not settle A's
v2 promote/retain decision and does not authorize
retraining PR-F, changing frozen manifests, retuning on 2024 Validation, or
letting E consume v2 without a separate promotion record.
