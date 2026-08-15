# V04-1 Market Foundation

Status: **MERGED**

## 1. Scope

V04-1 provides versioned contracts and deterministic infrastructure for IPO
market metadata, daily bars, post-listing outcome labels, chronological dataset
splits, blind-test protection, and integrity validation. It is a downstream
market layer and does not call the document Retriever or any professional Agent.

## 2. Architecture

```text
Official IPO metadata + versioned daily bars
                    -> MarketLabelGenerator
                    -> MarketOutcomeLabel (1D/5D/20D/60D)
                    -> MarketDatasetGuard / MarketDataValidator
```

The future modeling input will combine these outcome labels with a stable
document-risk snapshot. Retriever improvements will regenerate document
features, not change the market-data or label contracts.

## 3. MarketDataProvider contract

`MarketDataProvider` exposes `get_listing_metadata(stock_code)` and
`get_daily_bars(stock_code, start_date, end_date)`. The existing `get_snapshot`
call remains for v0.3 runtime compatibility. `InMemoryMarketDataProvider` is a
deterministic, network-free implementation for tests and controlled research.
It is deliberately not registered as a default production provider.

## 4. MarketDailyBar semantics

Each bar identifies a stock and observed trading date and carries positive,
finite `open`, `high`, `low`, and `close` values. `adjusted_close` and `volume`
are optional because a source may not supply them. OHLC ordering is validated.
Every record has a named source and versioned provenance.

## 5. IPO market metadata

`IPOMarketMetadata` records case/document identity, stock code, governance
cohort year, listing date, official listing price when available, currency,
exchange, authoritative-universe membership, descriptive security type,
modeling eligibility, eligibility reason/policy, source, and provenance. Missing
listing price or date remains missing; the foundation
never guesses it. The current committed catalog contains listing facts and EOD
coverage metadata, but no committed OHLCV history.

### 5.1 Cohort-year consistency

When `listing_date` exists, its year must equal `cohort_year`; inconsistent
metadata and labels fail schema validation. The catalog audit found 51 rows where
the prospectus `source_year` differs from `official_listed_date.year`. Therefore
`source_year` is not a safe modeling cohort proxy: a production market metadata
adapter must derive cohort year from the authoritative official listing date,
and must not silently inherit the document-source split.

### 5.2 Security universe and eligibility

Owner policy `v04_market_security_eligibility_v2` defines eligibility by
authoritative IPO-case membership:

```text
authoritative official IPO case -> eligible
non-member / arbitrary case     -> ineligible
security type                   -> descriptive only
```

For the current research cohort, membership is frozen by the official catalog:
all 438 official 2020-2024 IPO cases are eligible by construction. An unknown
security type is therefore eligible when the case is an authoritative member;
it is not converted to ordinary equity. A known REIT, SPAC or warrant annotation
also remains descriptive and does not exclude an official case.

Every `IPOMarketMetadata` row carries `official_ipo_universe_member`,
`security_type`, `modeling_eligibility`, `eligibility_reason`, and
`eligibility_policy_version`. Membership defaults to false, so a mock, arbitrary
ticker or ungoverned 2025 case cannot become eligible merely from its code or
declared security type. Security Master and Security Description may enrich
type metadata later, but they are not eligibility gates.

## 6. Canonical return formula

For horizon `h`:

```text
raw_return_h = target_session_close / official_listing_price - 1
```

The canonical base price is the official listing price. Listing-day close is
not a fallback.

## 7. 1D definition

`1D` is the close of observed eligible session 1 divided by official listing
price, minus one.

## 8. 5D definition

`5D` uses the close of observed eligible session 5.

## 9. 20D definition

`20D` uses the close of observed eligible session 20.

## 10. 60D definition

`60D` uses the close of observed eligible session 60.

## 11. Trading-session semantics

Session 1 is the first valid observed daily bar on or after `listing_date`.
Horizons count actual eligible bars, never `listing_date + N calendar days`.
Weekends and exchange holidays therefore add no session.

## 12. Suspension behavior

The v1 policy uses observed-session semantics. A suspension or another missing
date has no bar and does not increment the session counter. This is explicit in
policy version `v04_market_label_policy_v1`; no synthetic close is inserted.

## 13. Missing listing-price behavior

If official listing price is unavailable, all requested labels are emitted as
`unavailable / missing_base_price`. The generator does not silently substitute
listing-day close or another market price.

## 14. Insufficient-history behavior

If fewer than `h` eligible bars exist, horizon `h` is
`unavailable / insufficient_forward_history`. This is an allowed unavailable
label and is reported as a validation warning, not hidden as a valid return.

## 15. Benchmark semantics

`benchmark_return` and `excess_return` are optional. The repository has no
committed, versioned benchmark series, so V04-1 leaves both unavailable. No
Hang Seng or other index values are fabricated.

## 16. Split governance

The split is deterministic and has no random fallback or legacy exception:

```text
2020-2023 -> development
2024      -> validation
2025      -> blind
```

The cohort is carried as explicit metadata and the expected split is derived in
code. A known listing date must agree with that cohort, so a 2025 listing cannot
be labeled as a 2024 validation row. The v0.2-only `development_exception` is not
inherited by V04 modeling.

## 17. 2025 blind protection

`MarketOutcomeLabel` rejects an inconsistent year/split pair at validation.
`MarketDatasetGuard.require_development` rejects both validation and blind rows,
with a dedicated `BlindDataLeakageError` for 2025. `MarketDataValidator` also
reports `blind_leakage` when blind labels are presented for development use.
There is no parameter that reclassifies a 2025 row as development.

## 18. Provenance

Metadata, bars, and labels use `MarketDataProvenance`, which requires a source
and dataset version and can retain an upstream record identifier. Derived labels
record their label-policy and split-policy versions plus upstream source names.
No current timestamp, random value, LLM, or network call affects label output.

## 19. Current limitations

- The governed local competition OHLCV adapter covers 432 of the 438 eligible
  official 2020-2024 cases; six remain eligible with unavailable outcomes.
- Authoritative normalized security type remains unavailable and optional for
  descriptive/subgroup analysis.
- No reliable benchmark series is integrated.
- Missing official listing price produces unavailable labels.
- Observed-session counting cannot distinguish an exchange holiday from another
  absent bar without a future versioned exchange calendar.
- The in-memory provider is for deterministic tests/research, not live trading.

## 20. V04-1 out of scope

V04-1 does NOT yet provide a production market prediction model. It does not
provide a MarketAgent, Logistic Regression, LightGBM, feature selection,
hyperparameter tuning, a final document feature set, or 2025 blind evaluation.
It does not modify Parser, Retriever, Financial, Legal, Business, Verifier, or
Supervisor scoring behavior.
