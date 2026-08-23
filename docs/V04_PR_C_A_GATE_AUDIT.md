# v0.4 PR-C A-side Gate Audit

> Status: **SUPERSEDED BY FORMAL GATE PASS — PR-C COMPLETE / FROZEN**
> Owner: **A — Tech Lead / Pipeline**  
> Audit date: **2026-08-22**  
> Audited main revision: **`35d3fbcfe6f38b69842f3bb7c94d31a8d78a1d6c`**

> Resolution (2026-08-23): the required governed run and A final sign-off were
> completed on source revision `a1e32a97bc4ffa87aec3560598265e0536b4e07d`.
> Coverage is 438 / 424 / 14, the Development-only q25 threshold is `-0.1000`,
> determinism is 438 checked / 0 mismatches, and 2025 Blind y was not accessed.
> See [`V04_PR_C_COMPLETION_REPORT.md`](V04_PR_C_COMPLETION_REPORT.md). The
> remainder of this file is retained as the pre-materialization audit trail.

## 1. Historical pre-materialization decision

A-side review does **not** approve PR-C as COMPLETE / FROZEN yet.

The policy, schema, Development-only threshold rule, Validation isolation, Blind
boundary, abnormal-return behavior, provenance contract and deterministic
materialization machinery are acceptable for formal execution. However, the
formal freeze validator on `main` still encoded the old PR-B EOD coverage
assumption (`432 available / 6 unavailable`) instead of the measured PR-C 5D
outcome coverage (`424 available / 14 unavailable`). That mismatch must be
corrected before any formal full run can be accepted.

This audit therefore records:

```text
A_STATIC_AUDIT          PASS
PR_C_POLICY_GOVERNANCE  PASS
PR_C_FREEZE_EXPECTATION CORRECTION_REQUIRED
FORMAL_MATERIALIZATION  NOT_AVAILABLE_IN_REPOSITORY
PR_C_GATE               BLOCKED / NOT PASSED
```

No numeric threshold, freeze manifest, or completion claim is fabricated by
this audit.

## 2. Why 432 is not the PR-C label count

The frozen PR-B EOD store has session-ready EOD coverage for 432 of 438 official
cases. PR-C has an additional requirement: the raw 5D return is calculated
against the authoritative official listing price, and the generator does not
fall back to listing-day close when that price is missing.

The governed C-side readiness audit measured:

```text
Official cases retained          438
Development cases                368
Validation cases                  70
EOD/session-ready cases           432
Official base-price-ready cases   426
5D raw-return labels available    424
5D raw-return labels unavailable   14
```

Unavailable reason distribution:

```text
missing_base_price     12
no_eligible_session     2
```

All 14 unavailable cases are in Development, so the formal split-level target
coverage is:

```text
Development available  354 / 368
Validation available     70 / 70
Total available          424 / 438
```

## 3. Reviewed unavailable case set

The 14 PR-C outcome-unavailable cases, reconciled against the authoritative
bridge and the C-side label-readiness semantics, are:

| case_id | expected PR-C missing reason |
| --- | --- |
| `ipo_2020_01248` | `missing_base_price` |
| `ipo_2020_02115` | `missing_base_price` |
| `ipo_2020_02117` | `missing_base_price` |
| `ipo_2020_02148` | `missing_base_price` |
| `ipo_2020_02599` | `missing_base_price` |
| `ipo_2020_06688` | `no_eligible_session` |
| `ipo_2020_06813` | `missing_base_price` |
| `ipo_2020_09977` | `missing_base_price` |
| `ipo_2021_01491` | `missing_base_price` |
| `ipo_2021_02207` | `missing_base_price` |
| `ipo_2021_02217` | `missing_base_price` |
| `ipo_2022_03611` | `missing_base_price` |
| `ipo_2022_06678` | `missing_base_price` |
| `ipo_2022_07841` | `no_eligible_session` |

The six known no-EOD cases remain present. Four of those six also lack the
authoritative listing price, so the generator's existing missing-reason
precedence correctly reports `missing_base_price` for them. The two no-EOD
cases with a usable listing price are `ipo_2020_06688` and `ipo_2022_07841`,
which therefore report `no_eligible_session`.

## 4. A-side governance checks

| Gate item | Result | Evidence / rationale |
| --- | --- | --- |
| Official cohort is 438 | PASS | PR-C requires the authoritative 2020–2024 cohort |
| Development / Validation split is 368 / 70 | PASS | frozen time governance |
| Raw target definition | PASS | fifth observed eligible session close / official listing price - 1 |
| Threshold fit population | PASS | available Development labels only |
| Threshold method | PASS | Development nearest-rank q25 |
| Validation affects threshold | PASS | prohibited by policy/materializer |
| 2025 Blind y access | PASS | rejected by schema, builder and CLI boundary |
| Missing outcome behavior | PASS | explicit unavailable target; no zero/fallback imputation |
| Abnormal return | PASS | unavailable without governed benchmark |
| Source identity | PASS | raw EOD and official bridge SHA-256 are pinned |
| Readiness determinism | PASS | C-side readiness rerun produced identical coverage hash |
| Raw / filtered EOD parity | PASS | C-side audit reports full case/bar parity |
| Formal freeze expectations | **CORRECTED IN THIS A WORKSTREAM** | 424/14 replaces 432/6 |
| Formal target determinism | BLOCKED | requires governed full PR-C materialization |
| Numeric q25 threshold | BLOCKED | must be produced by governed Development run |
| Freeze manifest | BLOCKED | generated only after the formal validator passes |

## 5. Source identities retained by the Gate

```text
raw EOD SHA-256
190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152

official bridge SHA-256
751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198

filtered store SHA-256 (readiness audit)
73599d60818eeecfadc556453386d1dabc819138049c047cceb5ccc3a737cd1a

readiness coverage hash
df0a7d625c258f83c5beebdc6beec0bed23e38b5c07fd2454f5aed20c6f84608
```

The formal PR-C validator continues to bind the raw EOD and official bridge
hashes. The readiness-only filtered-store and coverage hashes are recorded here
for audit traceability and are not substituted for the formal run artifacts.

## 6. Required final steps before A can sign PASS

The next formal run must occur on the governed data machine from a clean
committed checkout after the corrected Gate lands:

```bash
python scripts/run_v04_pr_c.py \
  --catalog-dir data/catalog \
  --data-root <GOVERNED_COMPETITION_DATA_ROOT> \
  --output-dir reports/v04_pr_c \
  --verify-determinism

python scripts/run_v04_pr_c.py \
  --catalog-dir data/catalog \
  --data-root <GOVERNED_COMPETITION_DATA_ROOT> \
  --output-dir reports/v04_pr_c \
  --resume \
  --verify-determinism

python scripts/validate_v04_pr_c_freeze.py \
  --input-dir reports/v04_pr_c \
  --output reports/frozen/v04_pr_c_5d_outcome_manifest.json
```

A final sign-off requires all of the following to be observed rather than
assumed:

```text
438 coverage rows
424 available / 14 unavailable
354 Development available / 70 Validation available
12 missing_base_price / 2 no_eligible_session
zero build failures / zero silent drops
Development-only q25 threshold with exact provenance hashes
Validation did not refit or select threshold
2025 Blind y accessed = false
438 determinism checks / 0 mismatches
all 438 target content hashes valid
small freeze manifest generated by the validator
completion report reviewed
```

Only after those artifacts exist may A mark PR-C COMPLETE / FROZEN and release
formal PR-D materialization.

## 7. Current blocker

The public repository intentionally does not contain the governed raw
`hkshareeodprices.csv` or the formal `reports/v04_pr_c/` runtime output. A can
correct and review the Gate in Git, but cannot truthfully generate the numeric
q25 threshold or PR-C freeze manifest without the governed data execution.

This is an **external execution blocker**, not permission to weaken the Gate.
