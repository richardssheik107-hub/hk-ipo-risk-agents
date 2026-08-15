# V04-4A Data Readiness and Materialization

Status: **IN PROGRESS / BLOCKED ON REAL SOURCES**

This phase prepares reproducible 2020-2024 inputs for the merged V04-1,
V04-2 and V04-3 contracts. It does not train a model, choose a target threshold,
read a 2025 outcome, or treat synthetic data as a production source.

## 1. Reproduced baseline

The audit was rerun from main commit
`96cb081c58b6c61b0cdfaae07e2f6ad899c0d6df` against the configured local
competition data root. The official listing-year universe contains 438 matched
IPOs: 125 in 2020, 97 in 2021, 78 in 2022, 68 in 2023 and 70 in 2024.

The governed EOD scan matches 432 of 438 cases. There are still zero existing
authoritative `V03DocumentRiskSnapshot` artifacts; the older 398 JSON files are
mock/degraded `mvp_v1` outputs and remain prohibited for V04 modeling.

## 2. Official IPO metadata workbook

`HK_Official_Merged_565_First_with_IPO.xlsx` is the supplemental authoritative
source for IPO identity, listing date, issue price, board, listing method and
industry name. The committed bridge selects the 438 official 2020-2024 cases
from that wider workbook and retains its checksum.

The workbook does not close the normalized security-type gate. In particular,
`ShareType=H` appears on both conventional IPO rows and explicit SPAC rows, and
no authoritative codebook supplied with the data defines `ShareType2` as the
V04 security types. Neither field is therefore guessed into
`ordinary_equity`, `reit`, `spac` or `warrant`.

## 3. Security-master identifier audit

The available `hksharedescription.csv` was decoded as GB18030 and audited using:

- exact Wind code;
- normalized numeric code, leading zeros and `.HK` suffix;
- IPO `security_id` against source `OBJECT_ID`;
- IPO `institution_id` against source `S_INFO_COMPCODE`;
- listing-date coverage and historical identifier scope.

Result: 0/438 by every join route. The file contains 803 records, but its
non-null listing dates are 2009 or earlier; it is the already quarantined
`SECURITY_MASTER_TRUNCATED` source, not the 2020-2024 target universe.

`SECURITY_MASTER_SOURCE_REQUIRED`. Until a compatible source is provided,
every target IPO remains `security_type=unknown` and explicitly ineligible under
`v04_market_security_eligibility_v1`. The eligibility policy is not weakened.

## 4. Governed IPO OHLCV adapter

`CompetitionCSVMarketDataProvider` reads the official bridge and local
`hkshareeodprices.csv` using a configurable relative data root. It scans the EOD
file once, indexes byte offsets only for the 2020-2024 target securities, has no
network dependency, and records source name, version, record ID and checksum
without serializing an absolute local path.

The real adapter audit reports:

- target IPOs: 438;
- matched: 432;
- missing: 6;
- duplicate stock/date rows: 0;
- conventionally invalid OHLCV rows: 8,590;
- valid date coverage: 2020-01-02 through 2026-05-22;
- valid 1D/5D/20D/60D session coverage: 432 at every horizon.

The six missing cases are `ipo_2020_01248`, `ipo_2020_06688`,
`ipo_2020_06813`, `ipo_2021_01491`, `ipo_2022_06678` and
`ipo_2022_07841`. Invalid rows are excluded and counted; values are never
repaired or imputed. Duplicate stock/date keys fail closed. This phase does not
materialize labels.

## 5. Reference-market audit

No governed HSI daily-close series was found. A text hit for Hang Seng Bank is
not the Hang Seng Index. `HSI_SOURCE_REQUIRED`.

The IPO workbook supplies an industry name for 432 of the 438 target cases, but
an industry name is not an authoritative industry-to-index mapping. No governed
mapping or industry-index daily-close series was found.
`INDUSTRY_INDEX_MAPPING_REQUIRED` and `INDUSTRY_INDEX_SOURCE_REQUIRED`.

The EOD field `S_DQ_AMOUNT` is each security's transaction amount. It is not
total HKEX daily turnover and is not substituted, averaged or aggregated into
that feature. No governed total-market series was found.
`MARKET_TURNOVER_SOURCE_REQUIRED`.

These reference inputs were selected by the merged V04-3 market-feature
contract; they are not silently inferred from the competition workbook. V04-3
can represent their absence, but the complete real market-X gate remains
blocked while they are unavailable.

## 6. Authoritative document-result materialization

All 438 target cases have local prospectus files. The repository already has
`CatalogIPODataProvider`, `run_batch`, `IPOAnalysisService`, resume support and
the `enhanced_v2` workflow. `configs/v03_offline.yaml` uses the real PyMuPDF
parser, keyword Retriever and V03 Financial, Legal and Business agents with no
external LLM provider.

`V04DocumentSnapshotMaterializer` adds the governed final boundary:

```text
official case manifest
  -> enhanced_v2 IPOAnalysisResult
  -> authoritative-result validation
  -> DocumentRiskSnapshotBuilder
  -> versioned V03DocumentRiskSnapshot
```

It accepts only completed/partial `enhanced_v2` results carrying
`use_mock=false` and real parser, Retriever and professional-agent component
modes. It rejects `mvp_v1`, mock, unfinished and 2025 results. Pipeline version,
pipeline commit, workflow and schema provenance are retained. A persisted case
is reused only when its semantic snapshot is identical; different content or
provenance raises a conflict and is never overwritten. Batch reports are sorted
and include a failure CSV.

The offline configuration makes zero external LLM calls. Legal or Business
capabilities that require an unavailable LLM degrade explicitly in the final
result rather than being fabricated. A real-PDF smoke on development case
`ipo_2020_00368` completed with zero pipeline errors, produced a deterministic
snapshot, and reused it on the second materialization with the same hash. It
took about 16 seconds on the audit workstation. Naive sequential extrapolation
is roughly two hours for 438 cases, but one case is not a reliable performance
sample. The full run has not been started automatically and still requires
owner scheduling.

## 7. Versioned source manifest

`data/catalog/v04_source_manifest.json` uses
`v04_source_manifest_v1`. Entries are in stable logical-ID order and record
portable relative paths, source versions, SHA-256 checksums where a supplied
file exists, coverage, availability and provenance. Canonical JSON has a stable
content hash.

| Source | Required for | Status | Coverage | Blocker |
|---|---|---:|---:|---|
| Official IPO metadata | identity | AVAILABLE | 438/438 | none |
| Security type | eligibility | BLOCKED | 0/438 | `SECURITY_MASTER_SOURCE_REQUIRED` |
| IPO OHLCV | labels | AVAILABLE | 432/438 | six missing cases; eligibility still gated |
| HSI closes | market X | MISSING | 0/438 | `HSI_SOURCE_REQUIRED` |
| Industry mapping | market X | MISSING | 0/438 mapped | `INDUSTRY_INDEX_MAPPING_REQUIRED` |
| Industry-index closes | market X | MISSING | 0/438 | `INDUSTRY_INDEX_SOURCE_REQUIRED` |
| Total-market turnover | market X | MISSING | 0/438 | `MARKET_TURNOVER_SOURCE_REQUIRED` |
| V03 final snapshots | document X | AVAILABLE pipeline / not run | 0/438 existing | full batch not executed |

`MODEL_READY_DATA_GATE = BLOCKED`.

## 8. Exact owner inputs still required

1. Compatible security master: stable stock/security identifier, normalized
   security type, exchange, effective/listing dates, stable source record ID,
   source name and version. It cannot be replaced by stock-code rules or an
   undocumented `ShareType` interpretation.
2. HSI history: trading date, close, stable index identifier, source and
   version, covering the pre-listing windows required for 2020-2024 IPOs. A
   single stock or current index value is not a substitute.
3. Industry benchmark mapping: authoritative IPO industry identifier/name to
   governed benchmark index ID, with effective dates, source and version. An
   industry name alone is not a substitute.
4. Industry-index history: index ID, trading date, close, source and version
   for every governed mapping and required pre-listing window. HSI alone is not
   a substitute for industry-relative features.
5. HKEX total-market turnover: trading date, total-market turnover value, unit,
   market scope, source and version for the required pre-listing windows.
   Per-security amount or volume is not a substitute.
6. Owner scheduling approval for the 438-case offline real-PDF batch after the
   smoke runtime is reviewed. No paid API is required by the frozen offline
   configuration.

## 9. Target and scope governance

The target remains `five_day_significant_decline_risk`, but no threshold is
selected. `TARGET_POLICY_OWNER_DECISION_PENDING_DATA`. A future -5/-10/-15/-20
percent balance report may use eligible 2020-2023 development labels only.
Neither 2024 validation nor 2025 blind data may select the policy.

No Retriever, Parser, professional Agent, Verifier, Supervisor, Expert Golden,
V04-1 eligibility/label policy, V04-2 feature semantics or V04-3 formulas are
changed by this phase. Logistic, LightGBM, feature selection and training remain
out of scope.
