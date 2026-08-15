"""Deterministic, network-free provider used by V04-1 tests and research runs."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ipo_risk.market.exceptions import (
    DuplicateMarketBarError,
    MissingMarketMetadataError,
    UnsupportedStockError,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.market import IPOMarketMetadata, MarketDailyBar


class InMemoryMarketDataProvider:
    """Serve explicitly supplied metadata and bars without network or clock use."""

    name = "in_memory"

    def __init__(
        self,
        metadata: Iterable[IPOMarketMetadata] = (),
        bars: Iterable[MarketDailyBar] = (),
    ) -> None:
        self._metadata: dict[str, IPOMarketMetadata] = {}
        for item in metadata:
            if item.stock_code in self._metadata:
                raise MissingMarketMetadataError(
                    f"duplicate metadata for {item.stock_code}"
                )
            self._metadata[item.stock_code] = item

        self._bars: dict[str, list[MarketDailyBar]] = {}
        seen: set[tuple[str, date]] = set()
        for bar in bars:
            key = (bar.stock_code, bar.trading_date)
            if key in seen:
                raise DuplicateMarketBarError(
                    f"duplicate market bar for {bar.stock_code} on {bar.trading_date}"
                )
            seen.add(key)
            self._bars.setdefault(bar.stock_code, []).append(bar)
        for values in self._bars.values():
            values.sort(key=lambda bar: bar.trading_date)

    def get_listing_metadata(self, stock_code: str) -> IPOMarketMetadata:
        if stock_code in self._metadata:
            return self._metadata[stock_code]
        if stock_code in self._bars:
            raise MissingMarketMetadataError(
                f"market bars exist but IPO metadata is missing for {stock_code}"
            )
        raise UnsupportedStockError(f"unsupported stock code: {stock_code}")

    def get_daily_bars(
        self,
        stock_code: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MarketDailyBar]:
        if stock_code not in self._metadata and stock_code not in self._bars:
            raise UnsupportedStockError(f"unsupported stock code: {stock_code}")
        values = self._bars.get(stock_code, [])
        return [
            bar
            for bar in values
            if (start_date is None or bar.trading_date >= start_date)
            and (end_date is None or bar.trading_date <= end_date)
        ]

    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        """Preserve the legacy call without fabricating pre-listing features."""

        return MarketSnapshot(
            source="unavailable",
            metadata={
                "available": False,
                "reason": "pre_listing_snapshot_not_supplied_by_v04_in_memory_provider",
            },
        )
