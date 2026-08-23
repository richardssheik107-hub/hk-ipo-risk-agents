# V04 PR-C — 5D Outcome Policy

> Status: **COMPLETE / FROZEN**
> Owner: **D — Quant / ML Research**  
> Review: **A — schema / provenance / reproducibility / Blind Gate**

Formal freeze evidence: [`../V04_PR_C_COMPLETION_REPORT.md`](../V04_PR_C_COMPLETION_REPORT.md) and [`../../reports/frozen/v04_pr_c_5d_outcome_manifest.json`](../../reports/frozen/v04_pr_c_5d_outcome_manifest.json).

## 1. Scope

PR-C freezes one reproducible post-listing target for the official 2020–2024
IPO universe. It does not build the PR-D dataset, train a model, inspect 2025
outcomes, or enable an ungoverned benchmark.

The versioned contracts are:

```text
outcome policy:  v04_5d_outcome_policy_v1
target schema:   v04_5d_outcome_target_v1
orchestration:   v04_pr_c_5d_outcome_v1
```

## 2. Raw 5D return

The existing governed `MarketLabelGenerator` remains the source of the raw 5D
label. PR-C does not change its market-session semantics.

```text
base price = authoritative official listing price
D1         = first valid observed bar on or after official listing date
D5         = fifth valid observed bar on or after official listing date
return_5d  = D5 close / official listing price - 1
```

Weekends, exchange holidays, suspensions and other dates without a valid
observed bar do not increment the session counter. Duplicate stock/date rows
fail closed. Missing listing date, listing price, eligible session or forward
history emits an explicit unavailable target; there is no close-price fallback
and no zero imputation.

## 3. Binary weak-performance target

```text
poor_performer_5d = raw_return_5d <= frozen Development threshold
```

The threshold method is frozen before Validation is applied:

```text
method     = development_nearest_rank_quantile
quantile   = 0.25
population = all available 5D raw labels in 2020–2023 Development
rank       = ceil(0.25 * N)
threshold  = sorted Development return at rank
```

Ties are resolved deterministically by `(raw_return_5d, case_id)`. The threshold
artifact records the exact Development case-ID hash and return hash. Unavailable
Development rows stay in coverage but do not enter the quantile population.

This is a target-definition rule, not a model-selection loop. No Validation
metric is allowed to change the quantile or numeric threshold after fitting.

## 4. Abnormal return

The first PR-C policy freezes:

```text
abnormal_return_5d = unavailable_without_governed_benchmark
```

The current repository does not have a governed HSI history or authoritative
industry benchmark mapping/history. PR-C therefore rejects a supplied
benchmark/excess return rather than accepting a proxy. A future policy may
enable abnormal return only with a new source contract and policy/schema review.

## 5. Time governance

```text
2020–2023  Development — fit the target threshold and build targets
2024       Validation  — apply the already-frozen threshold only
2025       Blind       — no target API, no CLI option, fail closed
```

`FiveDayOutcomeTarget` rejects `dataset_split=blind` and `cohort_year=2025`.
The CLI obtains its universe through `CompetitionCSVMarketDataProvider`, which
already limits outcome cohorts to 2020–2024, and performs an additional Blind
guard before reading bars.

## 6. Canonical implementation

```text
src/ipo_risk/schemas/outcomes.py
src/ipo_risk/market/outcomes.py
scripts/run_v04_pr_c.py
tests/unit/test_v04_outcome_policy.py
tests/unit/test_v04_pr_c_orchestration.py
```

Run the formal full materialization from a clean committed checkout containing
the governed raw EOD source:

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
```

The data root must contain `hkshareeodprices.csv`. Large target/runtime artifacts
remain outside normal Git. Only a small reviewed freeze manifest and completion
report should be committed after the real run.

After both full runs, validate the formal Gate and generate the small candidate
freeze manifest:

```bash
python scripts/validate_v04_pr_c_freeze.py \
  --input-dir reports/v04_pr_c \
  --output reports/frozen/v04_pr_c_5d_outcome_manifest.json
```

The validator fail-closes on cohort/coverage drift, unexpected unavailable case
IDs, source checksum drift, threshold-population drift, Validation/Blind use,
target tampering, abnormal-return policy drift, or incomplete determinism.

## 7. Artifacts

```text
reports/v04_pr_c/
  frozen_threshold_policy.json
  run_manifest.json
  coverage.json
  coverage.csv
  failure_report.csv
  reproducibility_report.json
  targets/<case_id>.json
```

Every target retains the raw label policy/hash, outcome policy/hash, frozen
threshold hash and deterministic content hash. Resume reuses only byte-equivalent
semantic JSON and rejects provenance/content conflicts.

## 8. PASS Gate

PR-C is not frozen merely because code/tests exist. The formal Gate required a
real governed full run and review confirming:

```text
[x] all 438 official cases appear in coverage
[x] expected available/unavailable counts reconcile to the governed EOD audit
[x] every unavailable case has an explicit reason
[x] failure count and failure stages are explicit; no silent drop
[x] threshold fit used Development only
[x] Validation did not change the threshold
[x] abnormal return remained unavailable without a governed benchmark
[x] 2025 Blind y was not accessed
[x] deterministic rebuild passed with zero mismatches
[x] targeted and full pytest passed
[x] small freeze manifest and completion report reviewed
```

This Gate was satisfied on 2026-08-23. PR-C is therefore COMPLETE / FROZEN and
formal PR-D canonical dataset materialization is unblocked, but PR-D is not yet
complete.
