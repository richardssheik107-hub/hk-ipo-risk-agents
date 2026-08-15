from __future__ import annotations

import inspect
import math
from datetime import date, timedelta
from decimal import Decimal
from statistics import pstdev

import pytest

from ipo_risk.market.features import (
    MARKET_FEATURE_MANIFEST_V1,
    PreListingMarketFeatureEngine,
    PreListingMarketFeatureError,
    vectorize_market_snapshot,
)
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.providers.market_reference import InMemoryMarketReferenceDataProvider
from ipo_risk.schemas.market import (
    MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION,
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityEligibilityReason,
    MarketSecurityType,
)
from ipo_risk.schemas.market_features import (
    MARKET_FEATURE_POLICY_VERSION,
    MARKET_FEATURE_SCHEMA_VERSION,
    MARKET_RAW_FEATURE_ORDER,
    MarketActivityObservation,
    MarketFeatureAvailability,
    MarketFeatureMissingReason,
    MarketReferenceBar,
    PreListingMarketFeatureContext,
    PriorIPOReference,
)


def provenance(record_id: str = "row") -> MarketDataProvenance:
    return MarketDataProvenance(
        source="governed-fixture",
        dataset_version="fixture-v1",
        source_record_id=record_id,
    )


def context(year: int = 2023, listing: date | None = None) -> PreListingMarketFeatureContext:
    listing = listing or date(year, 3, 1)
    split = (
        MarketDatasetSplit.DEVELOPMENT
        if year <= 2023
        else MarketDatasetSplit.VALIDATION
        if year == 2024
        else MarketDatasetSplit.BLIND
    )
    return PreListingMarketFeatureContext(
        case_id=f"ipo_{year}_0001",
        stock_code="0001.HK",
        cohort_year=year,
        listing_date=listing,
        dataset_split=split,
        benchmark_reference_id="HSI",
        industry_reference_id="HKEX-TECH",
        source="catalog-fixture",
        provenance=provenance("target"),
    )


def bars(
    reference_id: str,
    *,
    start: date = date(2023, 1, 1),
    count: int = 40,
    base: int = 100,
) -> list[MarketReferenceBar]:
    return [
        MarketReferenceBar(
            reference_id=reference_id,
            trading_date=start + timedelta(days=index),
            close=Decimal(base + index),
            provenance=provenance(f"{reference_id}-{index}"),
        )
        for index in range(count)
    ]


def activity(count: int = 30) -> list[MarketActivityObservation]:
    return [
        MarketActivityObservation(
            trading_date=date(2023, 1, 1) + timedelta(days=index),
            turnover=Decimal(1000 + index),
            provenance=provenance(f"turnover-{index}"),
        )
        for index in range(count)
    ]


def prior(
    case_id: str,
    code: str,
    listing: date,
    *,
    security_type: MarketSecurityType = MarketSecurityType.ORDINARY_EQUITY,
    official_member: bool = True,
) -> PriorIPOReference:
    eligible = official_member
    reason = (
        MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER
        if eligible
        else MarketSecurityEligibilityReason.NOT_OFFICIAL_IPO_UNIVERSE_MEMBER
    )
    return PriorIPOReference(
        case_id=case_id,
        stock_code=code,
        cohort_year=listing.year,
        listing_date=listing,
        dataset_split=MarketDatasetSplit.DEVELOPMENT,
        official_ipo_universe_member=official_member,
        security_type=security_type,
        modeling_eligibility=(
            MarketSecurityEligibility.ELIGIBLE
            if eligible
            else MarketSecurityEligibility.INELIGIBLE
        ),
        eligibility_reason=reason,
        provenance=provenance(case_id),
    )


def outcome(
    item: PriorIPOReference,
    horizon: MarketLabelHorizon,
    raw_return: str,
    target_date: date,
) -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id=item.case_id,
        stock_code=item.stock_code,
        cohort_year=item.cohort_year,
        dataset_split=item.dataset_split,
        listing_date=item.listing_date,
        horizon=horizon,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=target_date,
        target_close=Decimal("10") * (Decimal("1") + Decimal(raw_return)),
        raw_return=Decimal(raw_return),
        availability=MarketLabelAvailability.AVAILABLE,
        label_policy_version="v04_market_label_policy_v1",
        source="label-fixture",
        provenance=provenance(f"{item.case_id}-{horizon.value}"),
    )


def values(snapshot):
    return {item.name: item for item in snapshot.features}


def complete_snapshot(**overrides):
    inputs = {
        "benchmark_bars": bars("HSI"),
        "industry_bars": bars("HKEX-TECH", base=200),
        "activity_observations": activity(),
        "prior_ipos": (),
        "prior_outcomes": (),
    }
    inputs.update(overrides)
    return PreListingMarketFeatureEngine().build(context(), **inputs)


def test_observation_date_is_strictly_prelisting_and_listing_day_is_never_used() -> None:
    target = context()
    historical = bars("HSI")
    listing_bar = MarketReferenceBar(
        reference_id="HSI",
        trading_date=target.listing_date,
        close=Decimal("999999"),
        provenance=provenance("listing-day"),
    )
    first = complete_snapshot(benchmark_bars=historical)
    second = complete_snapshot(benchmark_bars=[*historical, listing_bar])
    assert first.observation_date == historical[-1].trading_date < target.listing_date
    assert first == second


def test_future_rows_cannot_change_historical_features() -> None:
    target = context()
    historical_hsi = bars("HSI")
    historical_industry = bars("HKEX-TECH", base=200)
    future_hsi = MarketReferenceBar(
        reference_id="WRONG-FUTURE-ID",
        trading_date=target.listing_date + timedelta(days=20),
        close=Decimal("1"),
        provenance=provenance("future-hsi"),
    )
    future_industry = MarketReferenceBar(
        reference_id="WRONG-FUTURE-INDUSTRY",
        trading_date=target.listing_date + timedelta(days=1),
        close=Decimal("999"),
        provenance=provenance("future-industry"),
    )
    future_activity = MarketActivityObservation(
        trading_date=target.listing_date,
        turnover=Decimal("999999999"),
        provenance=provenance("future-turnover"),
    )
    first = complete_snapshot(
        benchmark_bars=historical_hsi,
        industry_bars=historical_industry,
    )
    second = complete_snapshot(
        benchmark_bars=[*historical_hsi, future_hsi],
        industry_bars=[*historical_industry, future_industry],
        activity_observations=[*activity(), future_activity],
    )
    assert first == second


def test_hsi_and_industry_trailing_session_formulas_are_exact() -> None:
    snapshot = complete_snapshot()
    observed = values(snapshot)
    hsi = bars("HSI")
    industry = bars("HKEX-TECH", base=200)
    assert observed["hsi_return_5d"].value == hsi[-1].close / hsi[-6].close - 1
    assert observed["hsi_return_20d"].value == hsi[-1].close / hsi[-21].close - 1
    assert observed["industry_return_5d"].value == industry[-1].close / industry[-6].close - 1
    assert observed["industry_return_20d"].value == industry[-1].close / industry[-21].close - 1


def test_missing_and_insufficient_benchmark_history_are_explicit() -> None:
    missing = complete_snapshot(benchmark_bars=[])
    short = complete_snapshot(benchmark_bars=bars("HSI", count=5))
    assert values(missing)["hsi_return_5d"].missing_reason is MarketFeatureMissingReason.MISSING_BENCHMARK
    assert values(short)["hsi_return_5d"].missing_reason is MarketFeatureMissingReason.INSUFFICIENT_HISTORY
    assert values(short)["hsi_return_5d"].value is None


def test_missing_industry_mapping_and_series_are_not_zero() -> None:
    no_mapping = PreListingMarketFeatureEngine().build(
        context().model_copy(update={"industry_reference_id": None}),
        benchmark_bars=bars("HSI"),
        prior_ipos=(),
    )
    no_series = complete_snapshot(industry_bars=[])
    short_series = complete_snapshot(industry_bars=bars("HKEX-TECH", count=5))
    assert values(no_mapping)["industry_return_5d"].missing_reason is MarketFeatureMissingReason.MISSING_INDUSTRY_MAPPING
    assert values(no_series)["industry_return_20d"].missing_reason is MarketFeatureMissingReason.MISSING_INDUSTRY_SERIES
    assert values(no_series)["industry_return_20d"].value is None
    assert values(short_series)["industry_return_5d"].missing_reason is MarketFeatureMissingReason.INSUFFICIENT_HISTORY


def test_volatility_is_exact_population_std_of_20_log_returns() -> None:
    hsi = bars("HSI")
    snapshot = complete_snapshot(benchmark_bars=hsi)
    selected = hsi[-21:]
    expected = pstdev(
        math.log(float(selected[index].close / selected[index - 1].close))
        for index in range(1, 21)
    )
    actual = values(snapshot)["market_volatility_20d"].value
    assert float(actual) == pytest.approx(expected)
    assert "not annualized" in values(snapshot)["market_volatility_20d"].provenance.derivation


def test_volatility_insufficient_history_is_unavailable() -> None:
    snapshot = complete_snapshot(benchmark_bars=bars("HSI", count=20))
    item = values(snapshot)["market_volatility_20d"]
    assert item.availability is MarketFeatureAvailability.UNAVAILABLE
    assert item.missing_reason is MarketFeatureMissingReason.INSUFFICIENT_HISTORY


def test_turnover_uses_actual_total_market_turnover_and_missing_source_is_explicit() -> None:
    observations = activity()
    snapshot = complete_snapshot(activity_observations=observations)
    expected = sum((row.turnover for row in observations[-20:]), Decimal("0")) / 20
    item = values(snapshot)["market_turnover_20d_mean"]
    assert item.value == expected
    assert "actual total-market turnover" in item.provenance.derivation
    missing = complete_snapshot(activity_observations=None)
    assert values(missing)["market_turnover_20d_mean"].missing_reason is MarketFeatureMissingReason.MISSING_TURNOVER_SOURCE


def test_recent_ipo_universe_and_known_outcome_cutoff() -> None:
    target = context()
    ordinary = prior("prior-good", "0002.HK", date(2023, 2, 1))
    reit = prior("prior-reit", "0003.HK", date(2023, 2, 2), security_type=MarketSecurityType.REIT)
    outside = prior("outside", "0005.HK", date(2023, 2, 4), official_member=False)
    self_row = prior(target.case_id, target.stock_code, date(2023, 2, 3))
    after_target = prior("after", "0004.HK", date(2023, 3, 2))
    known_1d = outcome(ordinary, MarketLabelHorizon.ONE_DAY, "-0.10", date(2023, 2, 2))
    known_5d = outcome(ordinary, MarketLabelHorizon.FIVE_DAYS, "0.20", date(2023, 2, 8))
    future_1d = outcome(ordinary, MarketLabelHorizon.ONE_DAY, "0.99", date(2023, 3, 2))
    # Future label is excluded before duplicate detection and cannot replace known history.
    snapshot = complete_snapshot(
        prior_ipos=[ordinary, reit, outside, self_row, after_target],
        prior_outcomes=[known_1d, known_5d, future_1d],
    )
    observed = values(snapshot)
    assert observed["recent_ipo_break_rate"].value == Decimal("1")
    assert observed["recent_ipo_return_5d"].value == Decimal("0.20")
    assert observed["recent_ipo_1d_sample_count"].value == 1
    assert observed["recent_ipo_5d_sample_count"].value == 1
    assert set(observed["recent_ipo_1d_sample_count"].provenance.source_record_ids) == {
        ordinary.case_id,
        reit.case_id,
    }


def test_zero_recent_ipo_samples_are_none_not_zero_rate() -> None:
    snapshot = complete_snapshot(prior_ipos=(), prior_outcomes=())
    observed = values(snapshot)
    assert observed["recent_ipo_break_rate"].value is None
    assert observed["recent_ipo_return_5d"].value is None
    assert observed["recent_ipo_1d_sample_count"].value == 0
    assert observed["recent_ipo_5d_sample_count"].value == 0
    assert observed["recent_ipo_break_rate"].missing_reason is MarketFeatureMissingReason.NO_RECENT_IPO_SAMPLE


def test_duplicate_historical_reference_rows_fail_closed() -> None:
    historical = bars("HSI")
    with pytest.raises(PreListingMarketFeatureError, match="duplicate historical"):
        complete_snapshot(benchmark_bars=[*historical, historical[-1]])


def test_snapshot_vector_manifest_and_hash_are_deterministic() -> None:
    first = complete_snapshot()
    second = complete_snapshot()
    vector = vectorize_market_snapshot(first)
    assert first == second
    assert first.content_hash() == second.content_hash()
    assert first.feature_policy_version == MARKET_FEATURE_POLICY_VERSION
    assert first.market_feature_schema_version == MARKET_FEATURE_SCHEMA_VERSION
    assert tuple(item.name for item in first.features) == MARKET_RAW_FEATURE_ORDER
    assert len(MARKET_FEATURE_MANIFEST_V1.features) == 20
    assert vector.feature_names == tuple(item.name for item in MARKET_FEATURE_MANIFEST_V1.features)
    assert MARKET_FEATURE_MANIFEST_V1.content_hash() == "9b777ef56168ef40c4beb924e73a99ed1613f8032ce4483630ffa8bed395ad3e"


def test_in_memory_reference_provider_enforces_exclusive_cutoff() -> None:
    target = context()
    all_bars = [
        *bars("HSI"),
        MarketReferenceBar(
            reference_id="HSI",
            trading_date=target.listing_date,
            close=Decimal("500"),
            provenance=provenance("listing"),
        ),
    ]
    provider = InMemoryMarketReferenceDataProvider(benchmark_bars=all_bars)
    result = provider.get_benchmark_bars(
        "HSI", end_date_exclusive=target.listing_date
    )
    assert result[-1].trading_date < target.listing_date


def test_v04_1_and_v04_2_frozen_contracts_remain_unchanged() -> None:
    assert MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION == "v04_market_security_eligibility_v2"
    assert DOCUMENT_FEATURE_MANIFEST_V1.version == "v04_document_features_v1"
    assert len(DOCUMENT_FEATURE_MANIFEST_V1.features) == 100
    assert DOCUMENT_FEATURE_MANIFEST_V1.content_hash() == "241d34ab0311c6d24b1685e01385a4bd69c404a759dbe37e9f2825ce7b404be4"


def test_engine_has_no_network_llm_retriever_or_agent_dependency() -> None:
    source = inspect.getsource(inspect.getmodule(PreListingMarketFeatureEngine))
    for forbidden in ("requests", "httpx", "openai", "retriever", "agent"):
        assert f"import {forbidden}" not in source.lower()
        assert f"from ipo_risk.{forbidden}" not in source.lower()
