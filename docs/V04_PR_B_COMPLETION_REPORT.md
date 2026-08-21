# V04 PR-B Completion Report

> Status: **COMPLETE / FROZEN**
> Freeze date: **2026-08-21**
> Source revision: **`dd67a17a5d6cfb246f0cb956c43e94aaddbc58a7`**
> Next milestone: **PR-C — 5D Outcome Policy Freeze / NOT STARTED**

## Scope

PR-B freezes the governed IPO EOD store and the first versioned Market-X Core. It does not freeze the 5D outcome threshold, create a model-ready dataset, or start PR-C.

The frozen Core contract is:

```text
schema                  v04_ipo_market_context_features_v1
policy                  ipo_market_context_policy_v1
raw features            15
adjacent missing flags  15
total positions         30
feature manifest hash   c2f4a1699e2bf9149f24cb35ea32dbc4851c017001ec509a0eaccd93720d729d
```

## Measured result

```text
Official 2020–2024 cases       438
Coverage rows                  438
Core materialized              438
Failed                         0
Silent drops                   0
PIT failures                   0
Development                    368
Validation                     70
Prior-history left boundary    2020-02-14
Coverage hash                  768b027676453d02d0cb5db8599acffbc2d58d7f5dc6e373bd9f4ddb305c974e
```

The 5-case engineering pilot also completed with 5 materialized, 0 failed and coverage hash `4f86f9d2488921bfb88f5349cf3866d236ae5648671cc17f4435a0f1cb9379db`. The pilot was not used to tune feature rules.

## Governed EOD provenance

```text
target cases                   438
row count                      433776
distinct target securities     432
provider OHLCV matched          432
provider OHLCV missing          6
filter schema                  v04_ipo_eod_filter_v2
raw EOD SHA256                 190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152
official bridge SHA256         751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198
```

The six securities without governed OHLCV remain explicit missing data. They were not removed from coverage and were not converted into zero or proxy observations. `S_DQ_AMOUNT` remains a per-security source column and is never treated as total-market turnover.

## PIT and missingness audit

- target IPO listing-day or post-listing values do not enter its own X;
- a prior IPO is eligible only when its listing date is strictly earlier than the target listing date;
- prior 1D/5D outcomes are eligible only when their target trading date is strictly earlier than the target listing date;
- the history start date comes from the complete official 438-case universe, including for limited pilots;
- incomplete 30D/60D/180D lookback is represented as `null` plus the adjacent `__missing=1` indicator;
- all 438 artifacts use the frozen feature order and manifest hash.

## Reproducibility

```text
resume requested               true
determinism checked            438
mismatch count                 0
coverage hash stable           true
manifest drift                 0
history-boundary drift         0
result                         PASS
```

## Validation

```text
targeted PR-B tests            68 passed / 0 failed / 0 skipped
full pytest                    1303 passed / 0 failed / 0 skipped
warnings                       2
compileall                     PASS
validate_project               PASS
validate_competition_data      PASS
git diff --check               PASS
2025 blind y accessed          NO
```

The two pytest warnings are existing scikit-learn feature-name warnings. Local persistent `IPO_RISK_*` LLM overrides were removed only inside the validation child process; no user environment or repository credential was changed.

## Extended source status

```text
HSI daily history                  MISSING
authoritative industry mapping     MISSING
industry-index history             MISSING
HK total-market turnover           MISSING
```

These are optional Extended-source limitations, not PR-B Core failures. No ungoverned proxy, fake benchmark row or neutral-zero imputation was used.

## Downstream contract boundary

PR-B freezes a 30-position Core contract. The repository also retains a separate historical 20-position Extended contract. PR-D must make an explicit versioned dataset-contract decision for Core and optional Extended inputs; this report does not silently modify the existing modeling dataset or public Schema.

## Gate verdict

```text
PR_A_STATUS               = COMPLETE / FROZEN
PR_B_STATUS               = COMPLETE / FROZEN
PR_B_GATE                 = PASS
PR_C_STATUS               = NEXT / NOT STARTED
MODEL_READY_DATA_GATE     = BLOCKED BY PR-C AND PR-D
2025_BLIND_Y_ACCESSED     = false
```

No complete runtime artifacts, raw market CSV, local absolute path, cache, secret or 2025 outcome are included in this freeze record.
