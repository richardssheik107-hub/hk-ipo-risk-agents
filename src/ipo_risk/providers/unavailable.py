"""Honest providers for data that is unavailable in the current runtime."""

from datetime import date

from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.market import IPOMarketMetadata, MarketDailyBar


class UnavailableMarketDataProvider:
    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        """Return an explicit absence marker without fabricated market values."""

        return MarketSnapshot(
            source="unavailable",
            metadata={
                "available": False,
                "reason": "real_market_data_not_integrated_in_v0.2",
            },
        )

    def get_listing_metadata(self, stock_code: str) -> IPOMarketMetadata | None:
        """Return no metadata rather than guessing missing offering facts."""

        return None

    def get_daily_bars(
        self,
        stock_code: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MarketDailyBar]:
        """Return no bars rather than performing an implicit network request."""

        return []


class RequestIPODataProvider:
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile:
        """Preserve only IPO identity supplied by the analysis request."""

        return IPOProfile(
            company_name=company_name,
            stock_code=stock_code,
            metadata={"source": "request"},
        )
