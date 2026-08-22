# v0.4 C P0 Filtered EOD Consumer and Label Readiness

## Scope and baseline

This change is a consumer-only addition for `v04_ipo_eod_filter_v2`. It does
not modify the frozen EOD builder or artifact semantics, the frozen 30-position
PR-B Core contract, `MarketLabelGenerator`, any outcome threshold, or any HSI,
industry, or turnover source.

The branch was created from the then-current `origin/main` at
`6acc9cf16b5a23d5d96ecebf1301540383caa259`. This is newer than the SHA in the
task handoff because `origin/main` advanced during preflight.

## Governed consumer

`FilteredEODV2MarketDataProvider` reads the frozen filtered store without
opening `hkshareeodprices.csv`. It validates:

- frozen schema version, exact ordered columns, selection policy, cohort years,
  cohort count and cohort identity;
- raw EOD identity against `v04_source_manifest.json`, plus current official
  bridge SHA-256;
- manifest/store row count, security count, min/max date, and optional pinned
  store SHA-256;
- stock/date identity, duplicate dates, date parsing, `OBJECT_ID` provenance,
  OHLCV validity, and the frozen `S_DQ_AMOUNT` semantics.

Invalid OHLCV rows remain in the 433,776-row store and are excluded from label
sessions by the same existing validity rule used by the raw provider. The
consumer does not normalize, rewrite, or migrate the store.

## Real-data readiness result

The audit materialized every official 2020-2024 case with the unchanged
`MarketLabelGenerator`:

| Measure | Count |
| --- | ---: |
| Official cases retained | 438 |
| Development cases | 368 |
| Validation cases | 70 |
| EOD/session-ready cases | 432 |
| Official base-price-ready cases | 426 |
| 1D raw-return labels available | 424 |
| 5D raw-return labels available | 424 |

EOD coverage is not label coverage. The 432 figure describes session-ready
EOD coverage; a raw-return label also requires the official issue price.

The current generator's missing-reason precedence was preserved. For both 1D
and 5D the unavailable counts are:

- `missing_base_price`: 12
- `no_eligible_session`: 2

No case was dropped and no audit failure occurred. The six known no-EOD cases
remain present. Four of them also lack an issue price and therefore retain the
generator's existing `missing_base_price` precedence.

## Provenance and determinism

- raw EOD SHA-256: `190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152`
- official bridge SHA-256: `751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198`
- filtered store SHA-256: `73599d60818eeecfadc556453386d1dabc819138049c047cceb5ccc3a737cd1a`
- filtered manifest SHA-256: `90dea66584e23d1887bf1cda8116b24f7bceec873ddf3aeb17730c7ef076664d`
- coverage content hash: `df0a7d625c258f83c5beebdc6beec0bed23e38b5c07fd2454f5aed20c6f84608`
- deterministic rerun: PASS (identical coverage content hash)

The frozen builder manifest does not contain a self-checksum for the bulk
filtered CSV. The consumer therefore always reports the computed store hash
and supports `expected_store_sha256` for deployments that pin it externally.

## Raw/filtered parity

A real-data comparison covered all 438 official cases and all 425,186 valid
bars exposed by the existing raw provider. Official metadata, daily-bar
semantics, and complete label objects were identical. This includes normal
cases across listing years 2020-2024, a trading-session gap case
(`ipo_2020_00368`), a no-EOD case (`ipo_2020_06688`), and a missing-price case
(`ipo_2020_01248`).

`RAW_FILTERED_PARITY = PASS`

## Runtime artifacts

The real 433,776-row store and the full 438-case JSON/CSV coverage are ignored
runtime outputs under `data/cache/` and `reports/v04_pr_c_readiness/`. They are
not committed. The audit selects no abnormal-return benchmark, no performer
threshold, and reads no 2025 outcome.
