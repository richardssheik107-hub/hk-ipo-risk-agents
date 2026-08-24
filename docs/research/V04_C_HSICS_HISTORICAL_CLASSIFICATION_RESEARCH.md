# V04 C — PIT-valid Historical HSICS Classification Research

Research date: 2026-08-24
Branch: `research/v04-c-hsics-historical-classification`

## 1. Outcome

No publicly accessible or locally delivered source checked in this audit can prove the
HSICS classification of any of the 438 official IPO cases at its listing date. The
production gate therefore remains fail-closed:

```text
PIT_CLASSIFICATION_AVAILABLE = 0 / 438
PIT_CLASSIFICATION_MISSING   = 438 / 438
PIT_SAFE                     = NO
READY_FOR_GOVERNED_INGESTION = NO
INDUSTRY_MAPPING_PIT_BLOCKED = YES
```

This is not a finding that Hang Seng Indexes did not classify the IPOs before listing.
Its official HSICS page says that it does. The missing item is a security-level historical
record, snapshot, or effective interval that proves which classification was assigned to
each IPO at that time.

## 2. Acceptance rule and intended grain

The intended output grain is one governed classification interval per security and HSICS
classification state:

```text
security_id + industry_code + effective_from (+ effective_to)
```

A candidate is accepted only when all of the following hold:

1. the issuer/security identity is stable and not inferred from a reused stock code;
2. the industry is explicitly HSICS rather than another provider taxonomy;
3. the source is authoritative;
4. an official observation timestamp is no later than `listing_date`, or an effective
   interval contains `listing_date`;
5. the result is deterministic and retains record-level lineage.

Download date, current display date, database refresh date, index membership date, and a
generic announcement date are not treated as classification effective dates.

## 3. Search strategy

The audit covered:

- Hang Seng Indexes: HSICS methodology, Index Operation Guide, HSCI pages, INdex360,
  historical review announcements, 2024 HSICS consultation conclusions and implementation;
- HKEX: issuer profiles, the official HSICS adoption notice, Shareholder Value in Focus,
  historical/reference-data products and their public field descriptions;
- Internet Archive: CDX inventory and archived HKEX equity quote HTML for 2020–2024;
- local licensed material: the CSMAR-derived merged official workbook and the delivered
  international-index basic-information archive;
- commercial provider descriptions: CSMAR, LSEG/Refinitiv, Bloomberg and Wind discovery.

The search deliberately excluded additional HSCI price history because prices do not solve
the classification-time blocker.

## 4. Primary official findings

### 4.1 Hang Seng Indexes proves process timing, not the assigned historical value

The official [HSICS description](https://origin-www.hsi.com.hk/eng/our-services/hsics)
states that an IPO is classified before listing using its prospectus. It also says a company
normally remains in a sector unless its business mix changes. This supports the process, but
does not prove that the 2026 static value in the project is the value assigned before a
2020–2024 listing.

The official 2024 materials demonstrate why static backfill is unsafe. The
[consultation conclusions](https://www.hsi.com.hk/static/uploads/contents/en/news/pressRelease/20240322T120001.pdf)
set a September 2024 implementation point for taxonomy changes and resulting company
reclassifications, while the
[August 2024 review result](https://www.hsi.com.hk/static/uploads/contents/en/news/pressRelease/20240816T180003.pdf)
sets 9 September 2024 as the effective date. Neither document publishes a complete
security-level before/after classification table.

Decision: `REJECT` as a complete historical classification source. These documents remain
authoritative evidence for methodology and a limited change date.

### 4.2 Historical constituents are not listing-time classification

[INdex360](https://www.hsi.com.hk/index360/eng/indexes) exposes index historical data and,
where applicable, historical changes of constituents. HSCI review announcements and
constituent reports can identify a company's industry-index membership only after it becomes
an index constituent. A new IPO can be classified before listing but join HSCI later.

Therefore:

```text
first HSCI industry-index membership date != HSICS classification effective_from
```

Decision: `REJECT_AS_CLASSIFICATION_PROXY`. No constituent record was counted toward the
438-case PIT coverage.

### 4.3 HKEX current historical-looking views are explicitly non-PIT

HKEX adopted HSICS for all Hong Kong-listed companies and identifies Hang Seng Indexes as
the classification manager in its
[official adoption notice](https://www.hkex.com.hk/News/Regulatory-Announcements/2007/071211news?sc_lang=en).
However, HKEX's current analytical pages are not historical-classification sources. Its
[Shareholder Value in Focus notes](https://www.hkex.com.hk/Listing/Sustainability/Shareholder-Value-in-Focus/Price-to-Earnings-Ratio?sc_lang=en)
explicitly say that the latest classification is used for both the latest and prior financial
years even when the earlier classification differed.

Decision: `REJECT_FOR_PRODUCTION_PIT`. This is direct official evidence against treating a
historical chart or current issuer page as an as-of classification observation.

### 4.4 HKEX historical reference-data products need field confirmation

The HKEX Data Marketplace advertises
[Securities Attribute Daily Files](https://data.hkex.com.hk/catalog/dataset/b3ce155a763811ef953342323a43f021?lang=en)
from September 2013. The public description confirms daily next-trading-day reference files
for Main Board and GEM securities, but it does not confirm that the equity file contains
HSICS industry codes/names. The legacy monthly product was advertised at HKD 500/month with
an academic discount, and the legacy Securities Master File at HKD 1,000/month, but their
public descriptions likewise do not establish an HSICS field. These are not purchase
recommendations.

Decision: `MANUAL_REVIEW`. Obtain the current technical specification and one historical
equity sample before spending money. A file date would be PIT-usable only if the file actually
contains the HSICS classification applying on that date.

## 5. Internet Archive audit

The Wayback CDX query returned 10,814 distinct 2020–2024 captures for the HKEX equity quote
page URL family. Matching the official target stock codes produced:

```text
target codes with any archived quote-page capture       189 / 438
target codes with capture timestamp <= listing_date      36 / 438
accepted security-level HSICS observations                 0 / 438
```

The apparent 36 are not evidence. The archived HTML carries empty dynamic containers such as
the HSICS industry span, while the value was populated by a separate runtime quote request.
The archive inventory also produces pre-listing hits for stock codes later reused by a new
issuer. A page timestamp plus a stock code therefore fails both data-content and entity-
identity checks.

Decision: `REJECT`. Because no archived official file containing a classification value was
accepted, there is no raw archive file or SHA-256 to register.

## 6. CSMAR and local licensed data audit

### 6.1 Delivered international-index basic archive

`国际指数基本信息文件141600089(仅供西安交通大学使用).zip` contains only:

```text
IDX_Gidxinfo[DES][csv].txt
IDX_Gidxinfo.csv
版权声明.pdf
```

The CSV has only `Indexcd` and `Idxnme`. It contains index identities, not security-level
industry classifications or effective dates. Decision: `REJECT`.

### 6.2 Merged official workbook

The licensed CSMAR-derived workbook was audited at the actual 438-case cohort grain. Its
`Field_Dictionary` assigns `IndustryCode`, `INDUSTRYNAME`, `IndustryCode2`, and
`IndustryName2` to the Institution source. The merge contains 438 target SecurityIDs, but its
rows do not form a governed HSICS history table:

```text
target cases                                              438
targets with multiple merged rows                          28
IndustryCode2 + DeclareDate <= listing_date candidates     51
targets with multiple pre-listing codes                     1
pre-listing candidate differs from another merged row      18
```

Candidate count by listing year:

| Listing year | Cases | Timestamp candidates | Accepted PIT records |
|---|---:|---:|---:|
| 2020 | 125 | 14 | 0 |
| 2021 | 97 | 8 | 0 |
| 2022 | 78 | 6 | 0 |
| 2023 | 68 | 7 | 0 |
| 2024 | 70 | 16 | 0 |
| Total | 438 | 51 | 0 |

`DeclareDate` has not been documented as HSICS `effective_from` or an HSICS observation
timestamp. More importantly, multiple examples associate old institution/classification
records with a stock code subsequently used by the target issuer. Treating the earliest row
as the IPO's industry would silently misidentify the company. The 51 rows are rejected
candidates, not `AMBIGUOUS` production mappings.

Decision: `REJECT`. No local candidate mapping was generated.

### 6.3 CSMAR website access

The public CSMAR landing page exposes general database discovery but requires login for the
detailed table/field query needed here. The available browser session was not authenticated.
No official table dictionary was found that proves a Hong Kong HSICS history table with
start/end or change dates. This is not enough to upgrade the local Institution fields.

Decision: `MANUAL_REVIEW`, subordinate to the preferred HSIL request below.

## 7. Other commercial providers

- [LSEG Industry Classifications](https://www.lseg.com/en/data-analytics/financial-data/reference-data/classifications/business-and-industry-classifications)
  advertises long history but lists TRBC, NAICS, NACE, SIC, GICS and ICB—not HSICS.
- [Bloomberg Reference Data](https://professional.bloomberg.com/products/data/enterprise-catalog/reference/)
  advertises BICS/BCLASS and other integrated classifications, but its public description
  does not establish historical HSICS values or effective dates.
- No accessible authoritative Wind specification proving historical HSICS semantics was
  found in this environment.

Different taxonomies cannot be substituted without an official time-aware crosswalk.
LSEG is therefore `REJECT`; Bloomberg and Wind remain `MANUAL_REVIEW`, with no accepted
coverage.

## 8. 438-case coverage and static comparison

| Listing year | Cases | PIT available | Missing | Ambiguous |
|---|---:|---:|---:|---:|
| 2020 | 125 | 0 | 125 | 0 |
| 2021 | 97 | 0 | 97 | 0 |
| 2022 | 78 | 0 | 78 | 0 |
| 2023 | 68 | 0 | 68 | 0 |
| 2024 | 70 | 0 | 70 | 0 |
| **Total** | **438** | **0** | **438** | **0** |

Because no historical record passed acceptance, a valid static-versus-historical comparison
cannot be computed:

```text
STATIC_HISTORICAL_MATCH    = 0
STATIC_HISTORICAL_MISMATCH = 0
NO_HISTORICAL_EVIDENCE     = 438
```

This does not mean the 432 current static values match history. It means the comparison is
unknown for all 438 cases.

## 9. Manual action that could actually solve the blocker

The preferred path is a written request to the owner of HSICS, not another index-price
purchase. Hang Seng Indexes publishes its contact details on the
[index licensing page](https://www.hsi.com.hk/solutions/index-licensing/):
`info@hsi.com.hk`, `+852 2877 0704`.

Request a custom licensed **security-level historical HSICS classification extract** for the
438 IPO codes/listing dates, with:

```text
stable security identifier and stock code
company identifier
HSICS industry / sector / subsector code and name
effective_from and effective_to, or authoritative as-of timestamp
source record/version
pre-listing classifications covering 2020-2024 IPOs
```

Price: `NOT_PUBLISHED_QUOTE_REQUIRED`.

Before licensing, require (1) a written field dictionary and date-semantics statement and
(2) a sample showing that an IPO's listing date falls inside the supplied classification
interval. If HSIL says no such extract exists, ask HKEX Data Marketplace for the SSD equity
technical specification and historical sample, specifically whether it carries HSICS codes.

Do not buy the old HSCI price series for this purpose.

## 10. Governed conclusion

```text
HSICS_HISTORICAL_SEARCH_STATUS

TARGET_CASES = 438

PRIMARY_OFFICIAL_SOURCES_CHECKED = 10 source families
ARCHIVED_PRIMARY_SOURCES_CHECKED = 1 source family
DATABASE_SOURCES_CHECKED = 4 provider families

HISTORICAL_CLASSIFICATION_SOURCE_FOUND = NO

WHY_NOT = Public official sources prove the classification process and selected change dates,
          but expose no complete security-level historical HSICS value/effective interval.
          Archived HKEX pages lack captured dynamic values; local CSMAR DeclareDate is not an
          HSICS effective date and contains entity-history contamination.
BEST_AVAILABLE_SOURCE = Hang Seng Indexes custom licensed historical HSICS extract, subject
                        to written confirmation and sample validation
MANUAL_ACTION_REQUIRED = YES

SOURCE = Hang Seng Indexes Company Limited
URL = https://www.hsi.com.hk/solutions/index-licensing/
PRODUCT = Custom licensed security-level historical HSICS classification extract
REQUIRED_FIELDS = stable security/company IDs; HSICS codes/names; effective_from/effective_to
                  or authoritative as-of timestamp; source version; pre-listing coverage
PRICE = NOT_PUBLISHED_QUOTE_REQUIRED
USER_ACTION = Send the 438-code/listing-date scope to info@hsi.com.hk and require a field
              dictionary plus a historical sample before licensing

PIT_CLASSIFICATION_AVAILABLE = 0/438
PIT_CLASSIFICATION_MISSING = 438/438
AMBIGUOUS = 0/438

BY_YEAR:
2020 = cases 125; available 0; missing 125; ambiguous 0
2021 = cases 97; available 0; missing 97; ambiguous 0
2022 = cases 78; available 0; missing 78; ambiguous 0
2023 = cases 68; available 0; missing 68; ambiguous 0
2024 = cases 70; available 0; missing 70; ambiguous 0

STATIC_HISTORICAL_MATCH = 0
STATIC_HISTORICAL_MISMATCH = 0
NO_HISTORICAL_EVIDENCE = 438

PIT_SAFE = NO
READY_FOR_GOVERNED_INGESTION = NO

INDUSTRY_MAPPING_PIT_BLOCKED = YES
HSCI_HISTORY_PURCHASE_RECOMMENDED = NO
NEXT_RECOMMENDED_C_ACTION = Obtain HSIL written product/field/date-semantics confirmation and
                            a sample; rerun the 438-case identity and interval audit only if it
                            proves listing-time HSICS values
```
