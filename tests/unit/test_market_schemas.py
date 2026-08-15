from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketBasePriceSource,
    MarketDailyBar,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketExchange,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelPolicy,
    MarketOutcomeLabel,
)


def provenance(record: str = "row-1") -> MarketDataProvenance:
    return MarketDataProvenance(
        source="fixture",
        dataset_version="fixture-v1",
        source_record_id=record,
    )


def test_valid_daily_bar_preserves_optional_fields_and_decimal_values() -> None:
    bar = MarketDailyBar(
        stock_code="0001.HK",
        trading_date=date(2024, 1, 2),
        open=Decimal("10.0"),
        high=Decimal("11.0"),
        low=Decimal("9.5"),
        close=Decimal("10.5"),
        adjusted_close=None,
        volume=None,
        source="fixture",
        provenance=provenance(),
    )
    assert bar.close == Decimal("10.5")
    assert bar.adjusted_close is None
    assert bar.volume is None
    assert bar.model_dump(mode="json")["provenance"]["dataset_version"] == "fixture-v1"


@pytest.mark.parametrize("field,value", [("open", "0"), ("close", "-1"), ("high", "NaN"), ("low", "Infinity")])
def test_daily_bar_rejects_non_positive_or_non_finite_prices(field: str, value: str) -> None:
    payload = {
        "stock_code": "0001.HK",
        "trading_date": date(2024, 1, 2),
        "open": Decimal("10"),
        "high": Decimal("11"),
        "low": Decimal("9"),
        "close": Decimal("10"),
        "source": "fixture",
        "provenance": provenance(),
    }
    payload[field] = Decimal(value)
    with pytest.raises(ValidationError):
        MarketDailyBar(**payload)


def test_daily_bar_rejects_inconsistent_ohlc() -> None:
    with pytest.raises(ValidationError, match="high must be at least"):
        MarketDailyBar(
            stock_code="0001.HK",
            trading_date=date(2024, 1, 2),
            open=Decimal("10"),
            high=Decimal("9"),
            low=Decimal("8"),
            close=Decimal("10"),
            source="fixture",
            provenance=provenance(),
        )


def test_metadata_keeps_unavailable_listing_price_and_currency_missing() -> None:
    metadata = IPOMarketMetadata(
        case_id="ipo_2024_00001",
        stock_code="0001.HK",
        cohort_year=2024,
        listing_date=date(2024, 1, 2),
        listing_price=None,
        currency=None,
        exchange=MarketExchange.HKEX,
        source="catalog",
        provenance=provenance("ipo_2024_00001"),
    )
    assert metadata.listing_price is None
    assert metadata.currency is None


def test_metadata_rejects_invalid_currency_and_missing_provenance() -> None:
    common = {
        "case_id": "ipo_2024_00001",
        "stock_code": "0001.HK",
        "cohort_year": 2024,
        "exchange": MarketExchange.HKEX,
        "source": "catalog",
    }
    with pytest.raises(ValidationError, match="currency"):
        IPOMarketMetadata(**common, currency="hkd", provenance=provenance())
    with pytest.raises(ValidationError, match="provenance"):
        IPOMarketMetadata(**common)
    with pytest.raises(ValidationError, match="exchange"):
        IPOMarketMetadata(**{**common, "exchange": "NYSE"}, provenance=provenance())


def test_label_policy_requires_version_and_all_frozen_horizons() -> None:
    with pytest.raises(ValidationError, match="version"):
        MarketLabelPolicy(version="")
    with pytest.raises(ValidationError, match="exactly 1D, 5D, 20D, and 60D"):
        MarketLabelPolicy(horizons=(MarketLabelHorizon.ONE_DAY,))


def test_outcome_schema_refuses_2025_development_override() -> None:
    with pytest.raises(ValidationError, match="must use blind split"):
        MarketOutcomeLabel(
            case_id="ipo_2025_00001",
            stock_code="0001.HK",
            cohort_year=2025,
            dataset_split=MarketDatasetSplit.DEVELOPMENT,
            listing_date=None,
            horizon=MarketLabelHorizon.ONE_DAY,
            base_price=None,
            base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
            availability=MarketLabelAvailability.UNAVAILABLE,
            missing_reason="missing_listing_date",
            label_policy_version="v1",
            source="derived",
            provenance=provenance(),
        )
