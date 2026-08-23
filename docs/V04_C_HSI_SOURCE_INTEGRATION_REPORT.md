# V04-C HSI Authoritative Source Integration Report

> Audit date: 2026-08-23
> Source: licensed CSMAR export, only for Xi'an Jiaotong University use
> Scope: HSI authoritative source integration; other index series inventory only

## 1. Acceptance summary

```text
BRANCH                         feat/v04-c-hsi-source-integration
BASE_SHA                       a58a92ffd49f9b510d7633abe625310f12581c1c
RELEASE_COMMIT_SHA              recorded by Git/PR after this report is committed

CSMAR_ARCHIVES_AUDITED         10
HSI_ARCHIVE                    国际指数日行情文件140955620(仅供西安交通大学使用).zip
HSI_SOURCE_FILE                IDX_Gidxtrd.xls
HSI_SOURCE_SHA256              a974a93e091307006f8461ca7be65132a1b3c588c1f23a3336615b6766a7db39

HSI_ROW_COUNT                  943
HSI_COVERAGE_START             2020-01-02
HSI_COVERAGE_END               2026-08-21
HSI_DUPLICATES                 0
HSI_INVALID_ROWS               0

HSI_SOURCE_ACCEPTED            YES (official 438-case scope)
DECLARED_2019_COVERAGE_TARGET  NOT_MET; delivered source starts 2020-01-02
SERIES_TYPE_STATUS             SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION

HSCI_5D_STATUS                 AVAILABLE_FROM_GOVERNED_HSI
HSCI_20D_STATUS                AVAILABLE_FROM_GOVERNED_HSI
MARKET_VOLATILITY_20D_STATUS   AVAILABLE_FROM_GOVERNED_HSI

OFFICIAL_CASES                 438
HSI_5D_AVAILABLE               438
HSI_20D_AVAILABLE              438
HSI_VOLATILITY_AVAILABLE       438

INDUSTRY_REFERENCE_SERIES_FOUND HSC, HSF, HSP, HSU, HSCEI, HSCCI; SHHKSI inventoried separately
INDUSTRY_HISTORY_STATUS        NOT_RESOLVED
INDUSTRY_MAPPING_STATUS        BLOCKED / REQUIRES_AUTHORITATIVE_MAPPING
MARKET_TURNOVER_STATUS         STILL_MISSING

2025_BLIND_Y_ACCESSED          NO
TARGETED_TESTS                 75 passed
FULL_TESTS                     1437 passed, 2 pre-existing warnings
DETERMINISM                    PASS
GIT_DIFF_CHECK                 PASS

C_HSI_READY_FOR_REVIEW         YES
MERGE_READY                    YES, subject to required PR CI
```

The delivered HSI history does not meet the requested calendar floor of
2019-01-01. It is nevertheless accepted for the official 2020–2024 cohort
because the earliest official listing date is 2020-02-14 and 29 observed HSI
sessions exist strictly before that date. All 438 cases have the 21 closes
required by the frozen 20-session return/volatility contracts.

## 2. Read-only archive inventory

All ZIPs passed CRC validation. All text/CSV members are UTF-8 compatible; the
HSI workbook is binary BIFF8 (`.xls`). Every daily file has zero duplicate
keys, zero null/invalid closes and zero parse errors. The complete member-level
inventory, including every contained filename, member SHA-256, encoding,
columns and byte count, is stored in
`data/catalog/csmar_index_archive_inventory.json`.

| Archive | Archive SHA-256 | Actual tabular member | Rows / codes / coverage |
| --- | --- | --- | --- |
| 国内指数日行情文件140355961…zip | `85b585a9ee7c24e3ecb1525153e66c11b9c7e379cf40959fb03368cd87ad76b2` | `IDX_Idxtrd.csv` | 911; SHHKSI; 2023-01-03–2026-08-21 |
| 国内指数日行情文件140426734…zip | `dfcd1a3659f5604bf6838b8f8fa3e4169ab4f514f9ed6b31e1f7f67af86b8bfd` | `IDX_Idxtrd.csv` | 760; SHHKSI; 2020-01-02–2022-12-30 |
| 国际指数基本信息文件141600089…zip | `5440c28099e3d526598e6f58d33985be2431fefedd4d86ca97a8d0ff63ceea14` | `IDX_Gidxinfo.csv` | 50 index definitions; no trading dates |
| 国际指数日行情文件140955620…zip | `bd6b29416f087c525a515e5ce01265b4e124cf7de117684675b48b8f4b1602e6` | `IDX_Gidxtrd.xls` | 943; HSI; 2020-01-02–2026-08-21 |
| 国际指数日行情文件141356561…zip | `9fcbfa136fcb5052e270f28ad23347c19e2c2c9cb62b54daa6c52689bb09c637` | `IDX_Gidxtrd.csv` | 501; HSCCI; 2014-06-17–2016-07-11 |
| 国际指数日行情文件141430995…zip | `be0efbfc27903a3f88c06369024e7fcc6d72e98b8b91ba56b8418b470dcd4aa9` | `IDX_Gidxtrd.csv` | 513; HSCEI; 2014-06-16–2016-07-11 |
| 国际指数日行情文件141449555…zip | `640b656a76c92aaed2833e05640bfc047be5277e4c6a9f5f779a85aee55a6e29` | `IDX_Gidxtrd.csv` | 1767; HSC; 2014-06-17–2021-10-29 |
| 国际指数日行情文件141505558…zip | `b7313a2554c9236b2a3458beb4fc7ccec52d5b9ad0b04a400ac9693f397fe22a` | `IDX_Gidxtrd.csv` | 1767; HSF; 2014-06-17–2021-10-29 |
| 国际指数日行情文件141523479…zip | `621b84b1b0907302caaa28c5da525afcce6af532650b9bb5fe9ad2a9fe93887d` | `IDX_Gidxtrd.csv` | 1767; HSP; 2014-06-17–2021-10-29 |
| 国际指数日行情文件141535595…zip | `7dbf622420a92999a0acf2a26c8b7d72f9cde7f0aefb0c54388c06303587abfa` | `IDX_Gidxtrd.csv` | 1767; HSU; 2014-06-17–2021-10-29 |

The basic-information file confirms HSI = 恒生指数, HSC = 恒生工商业分类指数,
HSF = 恒生金融分类指数, HSP = 恒生地产分类指数, and HSU =
恒生公用事业分类指数. It does not provide a field that freezes the official
`series_type` terminology. The HSI close can therefore be governed as a daily
price-level series, while the manifest retains
`SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION` rather than inventing a label.

## 3. Governed normalized layer

The source ZIP and XLS remain untouched. `prepare_csmar_hsi.ps1` opens the
staged workbook hidden and read-only, validates the exact eight-column CSMAR
schema, filters `Indexcd == HSI`, and writes an ignored UTF-8 normalized cache.
It preserves the original open/high/low/close/constituent-volume/index-return
fields and adds governed identity/provenance fields:

```text
reference_id
trading_date
open
high
low
close
constituent_volume
index_return
source_record_id
source_id
source_version
project_generated_identity
```

CSMAR does not deliver a source record ID in this workbook. The normalized
layer therefore uses the stable project identity
`project:CSMAR:IDX_Gidxtrd.xls:HSI:<date>` and explicitly records
`project_generated_identity = true`; it is not represented as a CSMAR-issued
identifier.

Runtime hashes:

```text
source archive     bd6b29416f087c525a515e5ce01265b4e124cf7de117684675b48b8f4b1602e6
source workbook    a974a93e091307006f8461ca7be65132a1b3c588c1f23a3336615b6766a7db39
normalized CSV     785f4d7c7769abb68f7f7e2841795cf797b80088ab78b74207dfe9113c0af6d2
source version     csmar_hsi_daily_close_v1:bd6b29416f08:a974a93e0913
```

## 4. PIT and 438-case readiness

The existing `PreListingMarketFeatureEngine` remains unchanged. It continues
to use six closes for 5D return, 21 closes for 20D return, and the frozen
population standard deviation of 20 one-session log returns for volatility.
Every target receives only HSI rows satisfying `trading_date < listing_date`.

The real readiness run retained all 438 cases and produced:

```text
hsi_return_5d available          438 / 438
hsi_return_20d available         438 / 438
market_volatility_20d available  438 / 438
silent drops                     0
future-row poisoning             PASS
artifact hash                    9af7e2b086510833fbb4e1c0349facc327eb012be90539c546eafaa3649d1038
repeat-run hash                   identical
```

The orchestration reads only official identity/listing metadata for 2020–2024.
It has no outcome argument or 2025 cohort path, so 2025 Blind y was not
accessed.

## 5. Other series and unresolved boundaries

`AVAILABLE_REFERENCE_SERIES` is not equivalent to
`APPROVED_INDUSTRY_BENCHMARK`.

- HSC/HSF/HSP/HSU end on 2021-10-29 and are auxiliary historical series only.
  They are not forward-filled, spliced, or used to claim 2020–2024 industry
  coverage.
- HSCEI and HSCCI end in 2016 and are inventory-only.
- SHHKSI covers 2020-01-02–2026-08-21 across two domestic-index exports, but it
  is not HSI and is not used by the HSI provider.
- No delivered daily file contains HSCIE/HSCIM/HSCIIG/HSCICD/HSCICS/HSCIH/
  HSCIT/HSCIU/HSCIF/HSCIPC/HSCIIT/HSCIC. Basic-information code presence would
  not have been treated as daily-history availability in any case.
- No industry mapping is implemented. `IndustryCode`, `INDUSTRYNAME`,
  `IndustryCode2`, `IndustryName2`, and `SectorIndName` remain unmapped.
- CSMAR constituent volume is not HKEX total-market turnover. Turnover remains
  missing.

## 6. Tests and repository hygiene

Targeted tests cover UTF-8/BOM handling, source/filter identity, schema/hash
validation, duplicate dates, missing/invalid close, deterministic sort,
coverage validation, exclusive listing cutoff, future-row poisoning,
insufficient 5D/20D history through the frozen engine tests, real orchestration,
and 2025 exclusion.

```text
targeted market/source tests   75 passed
full pytest                    1437 passed, 2 unrelated sklearn warnings
git diff --check               PASS
```

Tracked content is limited to code, tests, metadata/hashes, compact inventory,
and documentation. The licensed ZIP/XLS, full normalized CSV and 438-case
runtime dump remain ignored and local. Commit and PR identities are recorded by
Git/GitHub rather than embedded as a self-referential hash in this report.
