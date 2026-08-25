# 赛事数据概览

> Audit snapshot: **2026-08-25**  
> Purpose: 描述原始赛事数据宇宙、v0.4 official cohort 与 competition-stage 数据治理。  
> Measured readiness 以 [`research/V04_DATA_READINESS.md`](research/V04_DATA_READINESS.md) 为准。

## 1. Raw competition data universe

| 数据 | 规模 | 说明 |
| --- | ---: | --- |
| 招股书 | 565 份 | historical PDF corpus |
| 公司资料 | 4501 行 / 25 列 | supplemental company data |
| 证券资料 | 803 行 / 30 列 | isolated, not v0.4 eligibility authority |
| 日行情 | 4,117,539 行 / 22 列 | governed EOD source |
| 行情代码 | 3756 | `S_INFO_WINDCODE` |

Historical document `source_year` is not the modeling split authority.

## 2. Historical document corpus

```text
2020  138
2021   88
2022   87
2023   63
2024   73
2025  116
```

The frozen v0.3 2410.HK development exception remains a document-chain regression detail and does not redefine v0.4 market/model cohorts.

## 3. v0.4 official cohort

Authoritative split uses official listing date:

```text
2020–2023 official listing year → Development / Training
2024 official listing year      → Validation
2025 official listing year      → Blind Test
```

Official 2020–2024 universe: **438 cases**.

```text
2020  125
2021   97
2022   78
2023   68
2024   70
```

## 4. Official identity bridge

Controlled bridge:

```text
data/catalog/ipo_official_master_bridge.csv
```

It binds:

```text
case identity
stock code
listing date
issue/base price where authoritative
board / listing metadata
industry metadata
source provenance
```

`disclosure_date` is not listing date. Static supplemental fields do not automatically become PIT-safe features.

## 5. Document / Market / Outcome baseline coverage

```text
Production Document-X        438 / 438
Market-X Core                438 / 438
Governed EOD match            432 / 438 securities
5D Outcome                    424 / 438
Canonical model-ready         424 = 354 Dev + 70 Val
```

Outcome missing reasons:

```text
missing_base_price      12
no_eligible_session      2
```

EOD match coverage and Outcome coverage are distinct and must never be substituted for one another.

## 6. Market reference readiness

### Core

`Market-X Core` is frozen at 438/438 with strict PIT audit.

### Extended accepted inputs

```text
HSI return / volatility readiness       438 / 438
HKEX Main Board + GEM turnover 20D      438 / 438
HSCI official price series              12 accepted series
```

### Industry limitation

```text
production industry_return_5d             0 / 438
production industry_return_20d            0 / 438
```

Reason: the available company classification is a static Institution-source record without historical effective/listing-time semantics. HSCI index history cannot repair an unsafe company-to-industry temporal mapping.

Allowed behavior: explicit `INDUSTRY_MAPPING_PIT_BLOCKED` / `MISSING_INDUSTRY_CLASSIFICATION`.

Forbidden behavior:

```text
static current classification → pretend historical PIT mapping
single-security amount → pretend total-market turnover
fake benchmark
neutral zero fill
future IPO outcomes in target IPO features
```

## 7. Oracle research sidecar

```text
Oracle v2 materialized      98
strict usable               96
Development / Validation    77 / 19
feature count              142
evaluation_only            true
production_consumable      false
```

Oracle is not a production data source.

## 8. Competition-stage data extensions

After v0.4.3, new data work must be independently versioned.

### CH-1 Outcome sidecar

Planned:

```text
1D / 20D / 60D absolute returns
market-adjusted returns
20D / 60D maximum drawdown
20D / 60D volatility
severe-break flag
```

Frozen 5D PR-C artifacts are not rewritten.

### CH-3 Market Intelligence

Priority PIT-safe data families:

```text
recent IPO count
recent IPO break rate
recent IPO 1D / 5D performance
HSI trend / volatility
HKEX turnover / market activity
PIT-safe comparable IPO context
```

Any new feature must state `as_of`, source, cutoff semantics, availability/missing reason and version.

## 9. Source governance

- official membership controls eligibility;
- official listing year controls split;
- target IPO post-listing data cannot enter that IPO's X;
- prior IPO outcome may enter context only after that outcome was actually observable and before target listing cutoff;
- missing source remains missing;
- 2025 Blind y remains closed until formally authorized.

## 10. Source-of-truth order

1. code validators / Pydantic contracts;
2. frozen manifests;
3. completion reports;
4. `research/V04_DATA_READINESS.md`;
5. stable market/data research references;
6. this overview for corpus context.

Current Gate and schedule are defined in [`ROADMAP.md`](ROADMAP.md), not here.
