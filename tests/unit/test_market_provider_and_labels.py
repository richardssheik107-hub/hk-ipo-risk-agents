from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.exceptions import (
    DuplicateMarketBarError,
    MissingMarketMetadataError,
    UnsupportedStockError,
)
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.providers.market import InMemoryMarketDataProvider
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketExchange,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
)


def provenance(record: str) -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture",
        dataset_version="fixture-v1",
        source_record_id=record,
    )


def metadata(
    *,
    cohort_year: int = 2024,
    listing_date: date | None = date(2024, 1, 2),
    listing_price: Decimal | None = Decimal("10"),
) -> IPOMarketMetadata:
    return IPOMarketMetadata(
        case_id=f"ipo_{cohort_year}_00001",
        document_id=f"doc-{cohort_year}",
        stock_code="0001.HK",
        cohort_year=cohort_year,
        listing_date=listing_date,
        listing_price=listing_price,
        currency="HKD",
        exchange=MarketExchange.HKEX,
        source="fixture",
        provenance=provenance(f"ipo-{cohort_year}"),
    )


def observed_sessions(start: date, count: int, *, gap_after: int | None = None) -> list[date]:
    result: list[date] = []
    current = start
    while len(result) < count:
        if current.weekday() < 5:
            result.append(current)
            if gap_after is not None and len(result) == gap_after:
                current += timedelta(days=7)
        current += timedelta(days=1)
    return result


def bars_for(dates: list[date]) -> list[MarketDailyBar]:
    return [
        MarketDailyBar(
            stock_code="0001.HK",
            trading_date=trading_date,
            open=Decimal("10"),
            high=Decimal(index + 11),
            low=Decimal("9"),
            close=Decimal(index + 10),
            volume=Decimal("1000"),
            source="fixture",
            provenance=provenance(f"bar-{trading_date.isoformat()}"),
        )
        for index, trading_date in enumerate(dates, start=1)
    ]


def test_in_memory_provider_is_sorted_filtered_and_deterministic() -> None:
    info = metadata()
    values = bars_for([date(2024, 1, 4), date(2024, 1, 2), date(2024, 1, 3)])
    provider = InMemoryMarketDataProvider([info], values)

    first = provider.get_daily_bars("0001.HK", start_date=date(2024, 1, 3))
    second = provider.get_daily_bars("0001.HK", start_date=date(2024, 1, 3))
    assert [bar.trading_date for bar in first] == [date(2024, 1, 3), date(2024, 1, 4)]
    assert first == second
    assert provider.get_listing_metadata("0001.HK") == info


def test_in_memory_provider_distinguishes_unknown_stock_and_missing_metadata() -> None:
    orphan = bars_for([date(2024, 1, 2)])[0].model_copy(update={"stock_code": "0002.HK"})
    provider = InMemoryMarketDataProvider([metadata()], [orphan])
    with pytest.raises(UnsupportedStockError):
        provider.get_daily_bars("9999.HK")
    with pytest.raises(MissingMarketMetadataError):
        provider.get_listing_metadata("0002.HK")


def test_in_memory_provider_rejects_duplicate_bars() -> None:
    bar = bars_for([date(2024, 1, 2)])[0]
    with pytest.raises(DuplicateMarketBarError):
        InMemoryMarketDataProvider([metadata()], [bar, bar])


def test_label_horizons_count_observed_sessions_not_calendar_days() -> None:
    dates = observed_sessions(date(2024, 1, 2), 60, gap_after=5)
    labels = MarketLabelGenerator().generate(metadata(), bars_for(dates))
    by_horizon = {label.horizon: label for label in labels}

    assert by_horizon[MarketLabelHorizon.ONE_DAY].target_trading_date == dates[0]
    assert by_horizon[MarketLabelHorizon.FIVE_DAYS].target_trading_date == dates[4]
    assert by_horizon[MarketLabelHorizon.TWENTY_DAYS].target_trading_date == dates[19]
    assert by_horizon[MarketLabelHorizon.SIXTY_DAYS].target_trading_date == dates[59]
    assert by_horizon[MarketLabelHorizon.ONE_DAY].raw_return == Decimal("0.1")
    assert all(label.dataset_split is MarketDatasetSplit.VALIDATION for label in labels)
    assert all(label.benchmark_return is None and label.excess_return is None for label in labels)


def test_weekend_listing_and_suspension_gaps_use_first_observed_session() -> None:
    saturday = date(2024, 1, 6)
    dates = observed_sessions(date(2024, 1, 8), 5, gap_after=1)
    labels = MarketLabelGenerator().generate(
        metadata(listing_date=saturday), bars_for(dates)
    )
    assert labels[0].target_trading_date == date(2024, 1, 8)
    assert labels[1].target_trading_date == dates[4]


def test_insufficient_history_is_an_explicit_unavailable_label() -> None:
    labels = MarketLabelGenerator().generate(
        metadata(), bars_for(observed_sessions(date(2024, 1, 2), 5))
    )
    assert labels[0].availability is MarketLabelAvailability.AVAILABLE
    assert labels[1].availability is MarketLabelAvailability.AVAILABLE
    assert labels[2].missing_reason is MarketLabelMissingReason.INSUFFICIENT_FORWARD_HISTORY
    assert labels[3].raw_return is None


@pytest.mark.parametrize(
    "info,reason",
    [
        (metadata(listing_price=None), MarketLabelMissingReason.MISSING_BASE_PRICE),
        (metadata(listing_date=None), MarketLabelMissingReason.MISSING_LISTING_DATE),
    ],
)
def test_missing_base_or_listing_date_never_silently_falls_back(
    info: IPOMarketMetadata, reason: MarketLabelMissingReason
) -> None:
    labels = MarketLabelGenerator().generate(
        info, bars_for(observed_sessions(date(2024, 1, 2), 60))
    )
    assert all(label.availability is MarketLabelAvailability.UNAVAILABLE for label in labels)
    assert all(label.missing_reason is reason for label in labels)
    assert all(label.raw_return is None for label in labels)


def test_label_generation_rejects_missing_metadata_and_duplicate_dates() -> None:
    generator = MarketLabelGenerator()
    bar = bars_for([date(2024, 1, 2)])[0]
    with pytest.raises(MissingMarketMetadataError):
        generator.generate(None, [bar])
    with pytest.raises(DuplicateMarketBarError):
        generator.generate(metadata(), [bar, bar])


def test_label_generation_is_reproducible_and_versioned() -> None:
    values = bars_for(observed_sessions(date(2024, 1, 2), 60))
    generator = MarketLabelGenerator()
    first = [item.model_dump(mode="json") for item in generator.generate(metadata(), values)]
    second = [item.model_dump(mode="json") for item in generator.generate(metadata(), values)]
    assert first == second
    assert {item["label_policy_version"] for item in first} == {"v04_market_label_policy_v1"}
