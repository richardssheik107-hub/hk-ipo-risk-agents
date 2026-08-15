# V04-3 Pre-listing Market Features

Status: **IMPLEMENTED PENDING REVIEW**

## 1. Scope

V04-3 adds a deterministic, point-in-time market-control feature layer above the
merged V04-1 market foundation and V04-2 document feature contract. It does not
train a model or change document risk semantics.

All canonical V04-3 features are point-in-time features available strictly
before the target IPO listing date.

Post-listing `MarketOutcomeLabel` is never used to construct the target IPO's
pre-listing feature snapshot.

## 2. Architecture

```text
V03DocumentRiskSnapshot -> 100-position document vector
governed reference data -> PreListingMarketFeatureEngine -> 20-position market vector
document vector + market vector + non-blind MarketOutcomeLabel
    -> V04MarketAugmentedModelingDataset
```

`MarketReferenceDataProvider` is separate from the V04-1 per-security
`MarketDataProvider`. The replaceable reference provider supplies benchmark,
industry and total-market activity series with an exclusive end date. The pure
engine has no network, clock, random, LLM, Retriever or Agent dependency.

## 3. Observation cutoff and no-lookahead policy

Policy `v04_prelisting_market_features_v1` requires every market row date to be
strictly less than target `listing_date`. `observation_date` is the last valid
benchmark trading session before listing. Listing-day and later rows are removed
before series validation or computation, so adding or modifying T/T+N data cannot
change a legal historical snapshot.

Every series used by a feature also satisfies
`market_data_date <= observation_date < listing_date`. When no historical
benchmark row exists, `observation_date` and all observation-dependent feature
families remain explicitly unavailable.

## 4. Return and volatility formulas

HSI uses observed benchmark sessions ending at `observation_date`:

```text
hsi_return_5d  = close(t) / close(t-5)  - 1  # requires 6 closes
hsi_return_20d = close(t) / close(t-20) - 1  # requires 21 closes
```

Industry returns use the same 5/20 observed-session formulas. The industry
reference ID must come from authoritative metadata; the engine never infers an
industry from a company name, stock code or LLM. Missing mapping and missing
series are distinct states.

`market_volatility_20d` uses the last 21 benchmark closes, forms 20 one-session
log returns `ln(close_i / close_(i-1))`, then calculates the population standard
deviation (`ddof=0`). It is not annualized.

## 5. Turnover semantics

`market_turnover_20d_mean` is the arithmetic mean of actual total-market turnover
over the latest 20 valid sessions through `observation_date`. Single-stock volume
is not an accepted proxy. A missing governed turnover source remains
`unavailable / missing_turnover_source`.

## 6. Recent IPO universe and outcomes

The V1 universe contains at most the 20 most recent eligible ordinary-equity IPOs
whose listing date is within the 60 calendar days before the target listing and
no later than `observation_date`. The target case and target stock code are both
excluded. REIT, SPAC, warrant, unknown and other ineligible securities are
excluded using the merged V04-1 policy.

`recent_ipo_break_rate` is
`count(raw_return_1d < 0) / completed known 1D sample count`.
`recent_ipo_return_5d` is the mean completed known prior-IPO 5D raw return. A
prior label is known only when its `target_trading_date <= observation_date`.
Outcomes formed later are ignored before duplicate validation and aggregation.
Zero valid samples produce `None`, not a zero return/rate; the two sample-count
features remain zero.

## 7. Missing-data contract

Each raw feature carries value, availability, missing reason and provenance.
Missing reasons distinguish insufficient history, missing benchmark, missing
industry mapping, missing industry series, no recent IPO sample, missing turnover
source and a generally unavailable source. Missing is never converted to a safe
or market-neutral zero.

## 8. Feature manifest and provenance

Schema `v04_market_features_v1` freezes ten raw positions:

1. `hsi_return_5d`
2. `hsi_return_20d`
3. `industry_return_5d`
4. `industry_return_20d`
5. `recent_ipo_break_rate`
6. `recent_ipo_return_5d`
7. `recent_ipo_1d_sample_count`
8. `recent_ipo_5d_sample_count`
9. `market_turnover_20d_mean`
10. `market_volatility_20d`

Each raw position is immediately followed by an explicit `__missing` indicator,
for 20 ordered numeric positions total. Definitions include index, dtype, source
and missing semantics. Canonical JSON produces a deterministic SHA-256 manifest
hash. Snapshots retain source/dataset/record provenance and deterministic content
hashes. The legacy `MarketSnapshot.sentiment_score` is not part of this manifest.

## 9. Combined modeling contract

V04-3 does not mutate `v04_document_features_v1` or `V04ModelingRecord`. The new
`V04MarketAugmentedModelingRecord` records both manifest versions/hashes, market
policy, observation date, document pipeline version/commit, label policy, split
policy and dataset version. Combined order is explicitly:

```text
[100 document features] + [20 market features] = 120 positions
```

Development accepts 2020-2023 rows; validation accepts only 2024. The dedicated
2025 exporter accepts document X plus pre-listing market X and its schema forbids
outcome/target fields. It has no label argument.

## 10. Blind protection

No real 2025 outcome is read or used. A 2025 `MarketOutcomeLabel` cannot enter
the merged V04-2 dataset and therefore cannot reach the augmented builder. The
2025 feature-only record contains no post-listing outcome, label horizon or y.

## 11. Real-data availability

`REAL_MARKET_FEATURE_DATA_NOT_READY`: the committed catalog provides official
IPO identity, listing date, offer price, listing board/method and industry name,
plus EOD coverage metadata. It does not contain governed HSI closes, industry
index closes, total-market turnover or committed OHLCV history. Therefore V04-3
provides contracts, a pure engine and a deterministic in-memory reference
provider, but no production adapter or real development materialization. No
external market API or ungoverned download was introduced.

## 12. Current limitations and out of scope

- Authoritative industry names exist, but industry-to-index mapping and series do not.
- Real recent-IPO labels cannot be materialized until governed price history exists.
- There is no governed market sentiment policy; sentiment remains unavailable.
- Exchange-calendar semantics use observed sessions from supplied versioned series.
- Market Agent, Logistic Regression, LightGBM, SHAP, calibration, tuning and 2025
  outcome evaluation are out of scope.
- Parser, Retriever, professional Agents, Verifier, Supervisor, Expert Golden,
  V04-1 label policy and V04-2 document feature semantics are unchanged.
