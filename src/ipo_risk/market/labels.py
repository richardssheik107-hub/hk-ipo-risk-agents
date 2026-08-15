"""Deterministic 1/5/20/60-session IPO market outcome labels."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from ipo_risk.market.exceptions import (
    DuplicateMarketBarError,
    MissingMarketMetadataError,
    UnsupportedStockError,
)
from ipo_risk.market.governance import MarketDatasetSplitPolicy
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketLabelPolicy,
    MarketOutcomeLabel,
)


class MarketLabelGenerator:
    """Generate labels by counting observed eligible sessions, never calendar days.

    Session 1 is the first valid observed bar on or after ``listing_date``.
    Weekends, exchange holidays, suspensions, and other gaps have no synthetic
    rows and therefore do not increment the session counter. Duplicate dates are
    fatal. Missing listing price never falls back to listing-day close.
    """

    def __init__(
        self,
        policy: MarketLabelPolicy | None = None,
        split_policy: MarketDatasetSplitPolicy | None = None,
    ) -> None:
        self.policy = policy or MarketLabelPolicy()
        self.split_policy = split_policy or MarketDatasetSplitPolicy()

    def generate(
        self,
        metadata: IPOMarketMetadata | None,
        bars: Iterable[MarketDailyBar],
    ) -> list[MarketOutcomeLabel]:
        if metadata is None:
            raise MissingMarketMetadataError("IPO market metadata is required")

        materialized = list(bars)
        self._validate_bar_identity(metadata, materialized)
        dataset_split = self.split_policy.split_for_year(metadata.cohort_year)
        sorted_bars = sorted(materialized, key=lambda bar: bar.trading_date)

        if metadata.listing_date is None:
            return self._unavailable_all(
                metadata,
                dataset_split,
                MarketLabelMissingReason.MISSING_LISTING_DATE,
            )
        if metadata.listing_price is None:
            return self._unavailable_all(
                metadata,
                dataset_split,
                MarketLabelMissingReason.MISSING_BASE_PRICE,
            )

        eligible = [bar for bar in sorted_bars if bar.trading_date >= metadata.listing_date]
        if not eligible:
            return self._unavailable_all(
                metadata,
                dataset_split,
                MarketLabelMissingReason.NO_ELIGIBLE_SESSION,
            )

        labels: list[MarketOutcomeLabel] = []
        for horizon in self.policy.horizons:
            index = horizon.sessions - 1
            if index >= len(eligible):
                labels.append(
                    self._label(
                        metadata,
                        dataset_split,
                        horizon,
                        availability=MarketLabelAvailability.UNAVAILABLE,
                        missing_reason=MarketLabelMissingReason.INSUFFICIENT_FORWARD_HISTORY,
                    )
                )
                continue
            target = eligible[index]
            raw_return = target.close / metadata.listing_price - Decimal("1")
            labels.append(
                self._label(
                    metadata,
                    dataset_split,
                    horizon,
                    availability=MarketLabelAvailability.AVAILABLE,
                    target=target,
                    raw_return=raw_return,
                )
            )
        return labels

    @staticmethod
    def _validate_bar_identity(
        metadata: IPOMarketMetadata, bars: list[MarketDailyBar]
    ) -> None:
        seen_dates = set()
        for bar in bars:
            if bar.stock_code != metadata.stock_code:
                raise UnsupportedStockError(
                    f"bar {bar.stock_code} does not match metadata {metadata.stock_code}"
                )
            if bar.trading_date in seen_dates:
                raise DuplicateMarketBarError(
                    f"duplicate market bar for {bar.stock_code} on {bar.trading_date}"
                )
            seen_dates.add(bar.trading_date)

    def _unavailable_all(
        self,
        metadata: IPOMarketMetadata,
        dataset_split,
        reason: MarketLabelMissingReason,
    ) -> list[MarketOutcomeLabel]:
        return [
            self._label(
                metadata,
                dataset_split,
                horizon,
                availability=MarketLabelAvailability.UNAVAILABLE,
                missing_reason=reason,
            )
            for horizon in self.policy.horizons
        ]

    def _label(
        self,
        metadata: IPOMarketMetadata,
        dataset_split,
        horizon: MarketLabelHorizon,
        *,
        availability: MarketLabelAvailability,
        missing_reason: MarketLabelMissingReason | None = None,
        target: MarketDailyBar | None = None,
        raw_return: Decimal | None = None,
    ) -> MarketOutcomeLabel:
        target_record = target.provenance.source_record_id if target is not None else None
        provenance = MarketDataProvenance(
            source="market_label_generator",
            dataset_version=self.policy.version,
            source_record_id=f"{metadata.case_id}:{horizon.value}:{target_record or 'unavailable'}",
            metadata={
                "metadata_source": metadata.provenance.source,
                "market_bar_source": target.provenance.source if target is not None else None,
                "split_policy_version": self.split_policy.version,
            },
        )
        return MarketOutcomeLabel(
            case_id=metadata.case_id,
            stock_code=metadata.stock_code,
            cohort_year=metadata.cohort_year,
            dataset_split=dataset_split,
            listing_date=metadata.listing_date,
            horizon=horizon,
            base_price=metadata.listing_price,
            base_price_source=self.policy.base_price_source,
            target_trading_date=target.trading_date if target is not None else None,
            target_close=target.close if target is not None else None,
            raw_return=raw_return,
            benchmark_return=None,
            excess_return=None,
            availability=availability,
            missing_reason=missing_reason,
            label_policy_version=self.policy.version,
            source="derived_market_outcome",
            provenance=provenance,
        )
