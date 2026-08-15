"""Replaceable reference-market provider with deterministic in-memory tests."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ipo_risk.market.features import PreListingMarketFeatureError
from ipo_risk.schemas.market_features import MarketActivityObservation, MarketReferenceBar


class InMemoryMarketReferenceDataProvider:
    """Serve governed benchmark/industry/activity rows with an exclusive cutoff."""

    name = "in_memory_market_reference"

    def __init__(
        self,
        *,
        benchmark_bars: Iterable[MarketReferenceBar] = (),
        industry_bars: Iterable[MarketReferenceBar] = (),
        activity_observations: Iterable[MarketActivityObservation] = (),
    ) -> None:
        self._benchmark = self._index_bars(benchmark_bars, "benchmark")
        self._industry = self._index_bars(industry_bars, "industry")
        self._activity = sorted(activity_observations, key=lambda item: item.trading_date)
        activity_dates = [item.trading_date for item in self._activity]
        if len(activity_dates) != len(set(activity_dates)):
            raise PreListingMarketFeatureError("duplicate market activity date")

    @staticmethod
    def _index_bars(
        bars: Iterable[MarketReferenceBar], kind: str
    ) -> dict[str, tuple[MarketReferenceBar, ...]]:
        indexed: dict[str, list[MarketReferenceBar]] = {}
        seen: set[tuple[str, date]] = set()
        for bar in bars:
            key = (bar.reference_id, bar.trading_date)
            if key in seen:
                raise PreListingMarketFeatureError(
                    f"duplicate {kind} bar for {bar.reference_id} on {bar.trading_date}"
                )
            seen.add(key)
            indexed.setdefault(bar.reference_id, []).append(bar)
        return {
            reference_id: tuple(sorted(values, key=lambda item: item.trading_date))
            for reference_id, values in indexed.items()
        }

    def get_benchmark_bars(
        self, reference_id: str, *, end_date_exclusive: date
    ) -> list[MarketReferenceBar]:
        return [
            item
            for item in self._benchmark.get(reference_id, ())
            if item.trading_date < end_date_exclusive
        ]

    def get_industry_bars(
        self, reference_id: str, *, end_date_exclusive: date
    ) -> list[MarketReferenceBar]:
        return [
            item
            for item in self._industry.get(reference_id, ())
            if item.trading_date < end_date_exclusive
        ]

    def get_market_activity(
        self, *, end_date_exclusive: date
    ) -> list[MarketActivityObservation]:
        return [
            item for item in self._activity if item.trading_date < end_date_exclusive
        ]
