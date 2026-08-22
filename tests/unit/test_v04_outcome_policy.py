from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.outcomes import FiveDayOutcomeBuilder
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketOutcomeLabel,
)


def _label(
    case_id: str,
    raw_return: str | None,
    *,
    year: int = 2023,
    horizon: MarketLabelHorizon = MarketLabelHorizon.FIVE_DAYS,
    benchmark_return: str | None = None,
) -> MarketOutcomeLabel:
    listing = date(year, 1, 2)
    available = raw_return is not None
    return MarketOutcomeLabel(
        case_id=case_id,
        stock_code=f"{case_id[-4:]}.HK",
        cohort_year=year,
        dataset_split=(
            MarketDatasetSplit.DEVELOPMENT
            if year <= 2023
            else MarketDatasetSplit.VALIDATION
            if year == 2024
            else MarketDatasetSplit.BLIND
        ),
        listing_date=listing,
        horizon=horizon,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=listing + timedelta(days=7) if available else None,
        target_close=(
            Decimal("10") * (Decimal("1") + Decimal(raw_return))
            if available
            else None
        ),
        raw_return=Decimal(raw_return) if available else None,
        benchmark_return=(
            Decimal(benchmark_return) if benchmark_return is not None else None
        ),
        excess_return=(
            Decimal(raw_return) - Decimal(benchmark_return)
            if raw_return is not None and benchmark_return is not None
            else None
        ),
        availability=(
            MarketLabelAvailability.AVAILABLE
            if available
            else MarketLabelAvailability.UNAVAILABLE
        ),
        missing_reason=(
            None
            if available
            else MarketLabelMissingReason.NO_ELIGIBLE_SESSION
        ),
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture",
            dataset_version="fixture-v1",
            source_record_id=case_id,
        ),
    )


def test_threshold_is_development_only_nearest_rank_q25() -> None:
    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold(
        [
            _label("ipo_2023_0004", "0.20"),
            _label("ipo_2023_0001", "-0.30"),
            _label("ipo_2023_0003", "0.10"),
            _label("ipo_2023_0002", "-0.10"),
        ]
    )

    assert threshold.nearest_rank == 1
    assert threshold.threshold == Decimal("-0.30")
    assert threshold.development_sample_count == 4
    assert len(threshold.content_hash()) == 64


def test_unavailable_development_rows_are_not_silently_zeroed() -> None:
    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold(
        [_label("ipo_2023_0001", None), _label("ipo_2023_0002", "-0.10")]
    )
    target = builder.build_target(_label("ipo_2023_0001", None), threshold)

    assert threshold.development_sample_count == 1
    assert target.availability is MarketLabelAvailability.UNAVAILABLE
    assert target.raw_return_5d is None
    assert target.poor_performer_5d is None
    assert target.missing_reason is MarketLabelMissingReason.NO_ELIGIBLE_SESSION


def test_validation_can_apply_but_cannot_fit_threshold() -> None:
    builder = FiveDayOutcomeBuilder()
    development = [_label("ipo_2023_0001", "-0.10")]
    validation = _label("ipo_2024_0002", "-0.20", year=2024)
    threshold = builder.freeze_threshold(development)

    target = builder.build_target(validation, threshold)
    assert target.dataset_split is MarketDatasetSplit.VALIDATION
    assert target.poor_performer_5d is True

    with pytest.raises(ValueError, match="Development"):
        builder.freeze_threshold([validation])


def test_blind_outcome_is_rejected_for_fit_and_target() -> None:
    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold([_label("ipo_2023_0001", "-0.10")])
    blind = _label("ipo_2025_0002", "-0.20", year=2025)

    with pytest.raises(ValueError, match="Development"):
        builder.freeze_threshold([blind])
    with pytest.raises(ValueError, match="Blind"):
        builder.build_target(blind, threshold)


def test_threshold_and_targets_are_input_order_invariant() -> None:
    builder = FiveDayOutcomeBuilder()
    labels = [
        _label("ipo_2022_0002", "-0.20", year=2022),
        _label("ipo_2021_0001", "-0.20", year=2021),
        _label("ipo_2023_0003", "0.10", year=2023),
        _label("ipo_2020_0004", "0.20", year=2020),
    ]
    first = builder.freeze_threshold(labels)
    second = builder.freeze_threshold(reversed(labels))

    assert first == second
    assert first.threshold == Decimal("-0.20")
    target = builder.build_target(labels[0], first)
    assert target.poor_performer_5d is True
    assert target.canonical_json() == builder.build_target(labels[0], second).canonical_json()


def test_only_five_day_raw_labels_without_benchmark_are_accepted() -> None:
    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold([_label("ipo_2023_0001", "-0.10")])

    with pytest.raises(ValueError, match="only 5D"):
        builder.freeze_threshold(
            [
                _label(
                    "ipo_2023_0002",
                    "-0.20",
                    horizon=MarketLabelHorizon.ONE_DAY,
                )
            ]
        )
    with pytest.raises(ValueError, match="benchmark"):
        builder.build_target(
            _label("ipo_2023_0002", "-0.20", benchmark_return="0.01"),
            threshold,
        )
