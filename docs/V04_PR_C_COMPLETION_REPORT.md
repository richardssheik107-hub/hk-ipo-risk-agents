# v0.4 PR-C Completion Report

> Status: **COMPLETE / FROZEN**
> Freeze date: **2026-08-23**
> Source revision: **`a1e32a97bc4ffa87aec3560598265e0536b4e07d`**
> Gate owner: **A — Tech Lead / Pipeline**

## 1. Decision

PR-C — 5D Outcome Policy Freeze has completed its governed 2020–2024 full
materialization, conflict-safe resume, deterministic rebuild audit and formal
freeze validation. The measured artifacts satisfy the frozen Gate without
changing the outcome policy, expected cohort or source identities.

```text
PR-C                         COMPLETE / FROZEN
PR-D formal materialization READY / UNBLOCKED / NOT STARTED
2025 Blind y accessed       NO
```

PR-D is released to its own formal materialization Gate; this report does not
claim that PR-D is complete, frozen or passed.

## 2. Governed input identity

```text
raw EOD SHA-256
190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152

official bridge SHA-256
751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198
```

Both checksums were recomputed from the governed local sources and matched the
values pinned by the formal validator. No local absolute path is published in
the freeze manifest.

## 3. Measured coverage

```text
official cases                 438
coverage rows                  438
5D target available            424
5D target unavailable           14

Development available          354
Validation available             70

missing_base_price              12
no_eligible_session              2

generation/runtime failures      0
silent drops                     0
```

The 14 unavailable rows remain explicit and are not imputed to zero. Their
case IDs and reason mapping match `V04_PR_C_A_GATE_AUDIT.md` exactly.

## 4. Frozen threshold

```text
policy version          v04_5d_outcome_policy_v1
target schema           v04_5d_outcome_target_v1
method                  development_nearest_rank_quantile
quantile                0.25
Development samples     354
nearest rank             89
poor_performer_5d       raw_return_5d <= -0.1000
```

The threshold was fitted only on available 2020–2023 Development returns.
Validation did not fit or select the threshold. Blind was not accessed.
Benchmark/abnormal return remains unavailable because no governed benchmark
source is present.

## 5. Determinism and execution

```text
first governed run              60.429 seconds
resume + determinism run        64.115 seconds
determinism checked             438
determinism mismatches            0
resume provenance conflicts       0
freeze validator                PASS
```

All 438 target artifacts were independently revalidated against their declared
content hashes, policy hash, threshold hash and coverage identities. Available
targets contain raw return and binary target values; unavailable targets keep
both values null and retain an explicit missing reason.

## 6. Freeze identities

```text
coverage hash
2bf3282752db60ab971db43ac22f29db04c429a8250b7d2d7e29750ab049adc3

policy hash
5f793de0df22679430bb0a7565ed2d9eabfe63f0153725babc7ebd121d369c67

threshold hash
5aac9625209e65ccd7337d713e714ae1e9bd7e2d8f24db510e46131608a6ec05

target-set hash
5e0dedc8d207c8e73ca6439efb72f463c6b6f276c1c6c48e3ad7a989ad1533f4

freeze-manifest hash
722110d4eba51f5a8fe1071e268b6b46df4eb03eea63a353ec468bc462df1730
```

## 7. Artifact policy

Published in Git:

- `reports/frozen/v04_pr_c_5d_outcome_manifest.json` — small machine-readable
  freeze record;
- this completion report and active project-status updates.

Kept outside normal Git:

- `reports/v04_pr_c/targets/` with 438 per-case target files;
- bulk coverage JSON/CSV, runtime manifests, failure report and reproducibility
  output;
- governed raw competition CSV data and local execution paths.

The published freeze manifest is repository-safe and contains no credentials,
raw rows, local absolute paths or 2025 Blind outcomes.

## 8. A final sign-off

Independent A-side checks passed for source identity, cohort completeness,
missing-reason distribution, threshold population and nearest-rank semantics,
target nullability, abnormal-return governance, target/content hashes,
determinism and Blind isolation.

```text
PR-C COMPLETE / FROZEN
PR-D FORMAL MATERIALIZATION UNBLOCKED
```
